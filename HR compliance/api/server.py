from fastapi import FastAPI
from api.schemas import QueryRequest, QueryResponse

from router.graph import router_app
from memory.long_term import init_db

# Initialize DB at startup
init_db()

app = FastAPI(
    title="HR Compliance Assistant API",
    version="1.0"
)


@app.get("/")
def home():
    return {"message": "HR Compliance Assistant API Running"}


@app.post("/ask")
def ask_question(req: QueryRequest):
    try:
        result = router_app.invoke({
            "question": req.question,
            "user": req.user
        })
        return {
            "answer": result["final"],
            "intents": list(result["intents"])
        }
    except Exception as e:
        return {
            "answer": f"❌ Internal error: {str(e)}",
            "intents": []
        }
