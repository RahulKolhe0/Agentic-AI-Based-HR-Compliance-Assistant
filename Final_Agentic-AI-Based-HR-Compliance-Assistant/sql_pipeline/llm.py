import requests

def qwen(prompt):
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "qwen2:7b",
        "prompt": prompt,
        "stream": False
    })
    return r.json()["response"]
