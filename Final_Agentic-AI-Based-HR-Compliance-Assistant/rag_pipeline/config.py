import os

DATA_DIR = "./data"
VECTOR_DIR = "./vector_store"
RF_MODEL_PATH = "./models/hallucination_RF_model.pkl"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
TOP_K = 20
FINAL_TOP_K = 5
SIMILARITY_THRESHOLD = 2.5
HALLUCINATION_THRESHOLD = 0.65
MAX_RETRIES = 2
MIN_TOKEN_OVERLAP = 0.15

# Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"
RAG_MODEL = "llama3:latest"
