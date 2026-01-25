from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
import json
from bs4 import BeautifulSoup

load_dotenv()

app = FastAPI()

class ChatRequest(BaseModel):
    user_message: str

client = OpenAI(
    api_key=os.getenv("SUPER_MIND_API_KEY"),
    base_url="https://space.ai-builders.com/backend/v1"
)

def web_search(query: str):
    url = "https://space.ai-builders.com/backend/v1/search/"
    headers = {
        "Authorization": f"Bearer {os.getenv('SUPER_MIND_API_KEY')}"
    }
    data = {
        "keywords": [query],
        "max_results": 3
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

def read_page(url: str):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return f"Error: HTTP {response.status_code}"
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove scripts, styles, and other unwanted tags
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception as e:
        return f"Error fetching or parsing page: {str(e)}"

web_search_schema = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for information using keywords",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string"
                }
            },
            "required": ["query"]
        }
    }
}

read_page_schema = {
    "type": "function",
    "function": {
        "name": "read_page",
        "description": "Read the main text content from a web page URL",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the web page to read"
                }
            },
            "required": ["url"]
        }
    }
}

tools = [web_search_schema, read_page_schema]

@app.get("/hello")
def hello(name: str):
    """
    A simple hello endpoint that takes a name and returns a greeting.
    
    Args:
        name: A string representing the name
    
    Returns:
        A greeting message: "hello, {name}"
    """
    return f"hello, {name}"

@app.post("/chat")
def chat(request: ChatRequest):
    messages = [{"role": "user", "content": request.user_message}]
    max_turns = 3
    
    for turn in range(max_turns):
        response = client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            tools=tools
        )
        message = response.choices[0].message
        messages.append(message)
        
        if not message.tool_calls:
            print(f"[Agent] Final Answer: {message.content}")
            break
        
        for tool_call in message.tool_calls:
            print(f"[Agent] Decided to call tool: {tool_call.function.name}")
            if tool_call.function.name == "web_search":
                args = json.loads(tool_call.function.arguments)
                result = web_search(args["query"])
                print(f"[System] Tool Output: {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
            elif tool_call.function.name == "read_page":
                args = json.loads(tool_call.function.arguments)
                result = read_page(args["url"])
                print(f"[System] Tool Output: {result[:500]}...")  # Truncate for logging
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
    
    return {"response": message.content}

