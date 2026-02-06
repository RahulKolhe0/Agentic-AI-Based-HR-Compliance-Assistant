from fastapi import FastAPI, UploadFile, File
from api.schemas import QueryRequest, QueryResponse

from router.graph import router_app
import os
from memory.long_term import init_db
from rag_pipeline.config import DATA_DIR
from rag_pipeline.ingest import ingest

# Initialize DB at startup
init_db()

app = FastAPI(
    title="HR Compliance Assistant API",
    version="1.0"
)


@app.get("/")
def home():
    return {"message": "HR Compliance Assistant API Running"}


from logger import get_logger

logger = get_logger("API")

@app.post("/ask")
def ask_question(req: QueryRequest):
    """
    Main API endpoint used by Streamlit UI.
    Always returns valid JSON response.
    """
    logger.info(f"📥 Received Question: '{req.question}' | User: {req.user}")

    try:
        result = router_app.invoke({
            "question": req.question,
            "user": req.user
        })

        final_answer = result.get("final", "⚠️ No answer generated.")
        logger.info("✅ Response generated successfully")
        
        return {
            "answer": final_answer,
            "intents": list(result.get("intents", []))
        }

    except Exception as e:
        logger.error(f"❌ API Error: {str(e)}", exc_info=True)
        # ✅ Prevent FastAPI from returning HTML crash page
        return {
            "answer": f"❌ Internal Server Error: {str(e)}",
            "intents": []
        }

# -------------------------------
# ✅ Upload Endpoint (Admin Only)
# -------------------------------
@app.post("/upload")
def upload_document(file: UploadFile = File(...)):

    try:
        # ✅ Always save inside project data folder
        os.makedirs(DATA_DIR, exist_ok=True)

        # ✅ Clean filename
        safe_name = file.filename.replace(" ", "_")

        save_path = os.path.join(DATA_DIR, safe_name)

        # ✅ Save uploaded file into /data
        with open(save_path, "wb") as f:
            f.write(file.file.read())

        print("✅ File uploaded to:", save_path)

        # ✅ Run ingestion automatically in background
        import threading
        threading.Thread(target=ingest).start()

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file": safe_name
        }

    except Exception as e:
        print("❌ Upload Failed:", e)

        return {
            "status": "failed",
            "error": str(e)
        }