import requests

def llm_intent_classifier(question: str):

    prompt = f"""
You are an HR compliance intent classifier.

Classify the user question into one or more intents:

Intents:
- greet → greetings like hi/hello
- rag → HR policy/compliance/company rules questions
- sql → employee dataset/analytics/count/salary questions
- both → if both rag and sql are needed

Return ONLY one of these labels:
greet
rag
sql
both

Question: {question}
Label:
"""

    r = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2:7b",
            "prompt": prompt,
            "stream": False
        }
    )

    label = r.json()["response"].strip().lower()

    if label == "both":
        return {"rag", "sql"}
    return {label}
