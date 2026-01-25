from fastapi import FastAPI

app = FastAPI()

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

