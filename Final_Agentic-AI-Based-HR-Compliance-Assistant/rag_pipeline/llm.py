import requests
from rag_pipeline.config import OLLAMA_URL, RAG_MODEL

def llm(prompt: str) -> str:
    r = requests.post(OLLAMA_URL, json={
        "model": RAG_MODEL,
        "prompt": prompt,
        "stream": False
    })
    return r.json()["response"]
