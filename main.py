import json
import os
import re

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()
STATIC_DIR = Path(__file__).parent / "static"

# SUPER_MIND_API_KEY for local dev; AI_BUILDER_TOKEN injected during deployment
API_KEY = os.getenv("SUPER_MIND_API_KEY") or os.getenv("AI_BUILDER_TOKEN")
BASE_URL = "https://space.ai-builders.com/backend/v1"
SEARCH_URL = "https://space.ai-builders.com/backend/v1/search/"


def web_search(query: str) -> dict:
    """Call the internal search API with the given query."""
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"keywords": [query], "max_results": 3}
    response = requests.post(SEARCH_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def read_page(url: str) -> dict:
    """Fetch a URL and extract main text from HTML (strip tags, scripts, styles)."""
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (compatible; FastAPI-Bot/1.0)"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # Remove script, style, and other non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse multiple newlines and whitespace
    text = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text))
    return {"url": url, "text": text[:50000]}  # Limit to 50k chars


# Tool schemas for the LLM (OpenAI function calling format)
WEB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information. Use this when you need to look up facts, recent events, or information that may have changed.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string (e.g., 'Super Bowl 2025 winner')",
                }
            },
            "required": ["query"],
        },
    },
}

READ_PAGE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_page",
        "description": "Fetch a web page by URL and extract its main text content. Use this to read specific pages (e.g., documentation, changelogs, articles) after you have found their URLs via web_search.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the page to read (e.g., 'https://docs.python.org/3/whatsnew/3.13.html')",
                }
            },
            "required": ["url"],
        },
    },
}

TOOLS = [WEB_SEARCH_TOOL_SCHEMA, READ_PAGE_TOOL_SCHEMA]


MODELS = [
    {"id": "gpt-5", "name": "GPT-5"},
    {"id": "deepseek", "name": "DeepSeek"},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
    {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash"},
    {"id": "grok-4-fast", "name": "Grok 4 Fast"},
    {"id": "kimi-k2.5", "name": "Kimi K2.5"},
    {"id": "supermind-agent-v1", "name": "SuperMind Agent"},
]


class ChatRequest(BaseModel):
    user_message: str
    model: str = "gpt-5"


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/hello")
def hello(name: str = "World"):
    return {"message": f"Hello, World {name}"}


@app.get("/models")
def list_models():
    return {"models": MODELS}


@app.post("/chat")
def chat(request: ChatRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="SUPER_MIND_API_KEY or AI_BUILDER_TOKEN not configured")
    model = request.model or "gpt-5"
    if model not in [m["id"] for m in MODELS]:
        model = "gpt-5"
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    messages = [{"role": "user", "content": request.user_message}]
    max_turns = 3
    turn = 0

    while turn < max_turns:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            # Final answer
            content = message.content or ""
            print(f"[Agent] Final Answer: '{content}'")
            return {"content": content}

        # Execute tool calls and feed results back
        turn += 1
        messages.append(message)  # Assistant message with tool_calls

        for tc in message.tool_calls:
            tool_name = tc.function.name
            print(f"[Agent] Decided to call tool: '{tool_name}'")

            try:
                args = json.loads(tc.function.arguments)
                if tool_name == "web_search":
                    result = web_search(args.get("query", ""))
                elif tool_name == "read_page":
                    result = read_page(args.get("url", ""))
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                result_str = json.dumps(result, default=str)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})

            print(f"[System] Tool Output: '{result_str[:500]}{'...' if len(result_str) > 500 else ''}'")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

    # Max turns reached with pending tool results - force final answer (no more tools)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="none",
    )
    content = response.choices[0].message.content or "Max turns reached."
    print(f"[Agent] Final Answer: '{content}'")
    return {"content": content}
