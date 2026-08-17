"""Ollama Local Inference Client — shared by Strategy and Learning agents."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def generate(
    model: str,
    prompt: str,
    system: str,
    num_ctx: int = 2048,
    num_predict: int = 512,
    timeout: int = 30,
) -> dict:
    """
    Call Ollama /api/generate synchronously.
    Returns the full response dict (including 'response', 'eval_count', etc.).
    Raises requests.Timeout if the call exceeds `timeout` seconds.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()
