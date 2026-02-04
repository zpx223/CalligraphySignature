from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
import json
from bs4 import BeautifulSoup

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

class ChatRequest(BaseModel):
    user_message: str
    model: str = "gpt-5"

AI_BUILDERS_URL = "https://space.ai-builders.com/backend/v1"

# Model IDs that use the images API (from ai-builders /models)
IMAGE_MODEL_IDS = {"gpt-image-1.5", "gemini-2.5-flash-image"}

def fetch_ai_builders_models() -> list[dict]:
    """Fetch available models from ai-builders API."""
    api_key = os.getenv("SUPER_MIND_API_KEY")
    if not api_key:
        return []
    try:
        headers = {"accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = requests.get(f"{AI_BUILDERS_URL}/models", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception:
        return []

def get_client_and_model(model_key: str) -> tuple[OpenAI, str]:
    """Get OpenAI client and model id. All models use ai-builders."""
    api_key = os.getenv("SUPER_MIND_API_KEY")
    if not api_key:
        raise ValueError("Missing SUPER_MIND_API_KEY")
    client = OpenAI(api_key=api_key, base_url=AI_BUILDERS_URL)
    return client, model_key or "gpt-5"

client = OpenAI(
    api_key=os.getenv("SUPER_MIND_API_KEY"),
    base_url=AI_BUILDERS_URL
)

def web_search(query: str):
    url = f"{AI_BUILDERS_URL}/search/"
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

@app.get("/models")
def list_models():
    """Return available models from ai-builders API for the frontend dropdown."""
    raw = fetch_ai_builders_models()
    available = [
        {"id": m["id"], "name": m.get("description", m["id"])}
        for m in raw
    ]
    if not available:
        available = [{"id": "gpt-5", "name": "GPT-5 (fallback)"}]
    return {"models": available}


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
    chat_client, model_id = get_client_and_model(request.model)
    prompt = request.user_message

    # Image models: use images API
    if model_id in IMAGE_MODEL_IDS:
        try:
            img_resp = chat_client.images.generate(prompt=prompt, model=model_id, n=1)
            urls = []
            for d in getattr(img_resp, "data", []) or []:
                url = getattr(d, "url", None) or (d.get("url") if isinstance(d, dict) else None)
                if url:
                    urls.append(url)
                b64 = getattr(d, "b64_json", None) or (d.get("b64_json") if isinstance(d, dict) else None)
                if b64:
                    urls.append(f"data:image/png;base64,{b64}")
            return {"response": None, "images": urls}
        except Exception as e:
            return {"response": f"Image generation failed: {e}", "images": None}

    # Text models: chat completions with tools
    messages = [{"role": "user", "content": prompt}]
    max_turns = 3
    message = None
    for turn in range(max_turns):
        response = chat_client.chat.completions.create(
            model=model_id,
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
                print(f"[System] Tool Output: {result[:500]}...")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

    text = getattr(message, "content", None) if message else None
    return {"response": text, "images": None}

