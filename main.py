from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class ChatRequest(BaseModel):
    user_message: str

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://space.ai-builders.com/backend/v1"
)

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
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "user", "content": request.user_message}
        ]
    )
    return {"response": response.choices[0].message.content}

