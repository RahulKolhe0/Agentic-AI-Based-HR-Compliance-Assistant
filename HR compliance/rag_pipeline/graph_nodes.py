from typing import TypedDict, List, Set, Dict
from rag_pipeline.intent import detect_intent
from rag_pipeline.retrieval import retrieve_chunks
from rag_pipeline.rerank import rerank_chunks
from rag_pipeline.hallucination import detect_hallucination
from rag_pipeline.prompts import answer_prompt
from rag_pipeline.llm import gemma_llm
from rag_pipeline.config import MAX_RETRIES

class GraphState(TypedDict):
    question: str
    intent: str
    retrieved: List[Dict]
    reranked: List[Dict]
    categories: Dict
    context: str
    answer: str
    final: str
    sources: Set[str]
    hallucination_check: Dict
    retry_count: int


def intent_node(state):
    intent = detect_intent(state["question"])
    return {**state, "intent": intent}


def retrieve_node(state):
    chunks = retrieve_chunks(state["question"])
    return {**state, "retrieved": chunks}


def rerank_node(state):
    reranked = rerank_chunks(state["question"], state["retrieved"])
    return {**state, "reranked": reranked}


def categorize_chunks(chunks):
    categories = {
        "mandatory": [],
        "restriction": [],
        "penalty": [],
        "procedure": [],
        "general": []
    }

    for chunk in chunks:
        text_lower = chunk["text"].lower()

        if any(w in text_lower for w in ["must", "shall", "required", "mandatory"]):
            categories["mandatory"].append(chunk)
        if any(w in text_lower for w in ["not allowed", "prohibited", "restricted", "cannot"]):
            categories["restriction"].append(chunk)
        if any(w in text_lower for w in ["disciplinary", "termination", "warning", "penalty"]):
            categories["penalty"].append(chunk)
        if any(w in text_lower for w in ["procedure", "process", "step"]):
            categories["procedure"].append(chunk)

        categories["general"].append(chunk)

    return categories


def build_context(question, chunks, categories, intent):
    if intent == "penalty":
        selected = categories["penalty"][:3] + categories["mandatory"][:2]
    elif intent == "permission":
        selected = categories["restriction"][:3] + categories["mandatory"][:2]
    elif intent == "procedure":
        selected = categories["procedure"][:4]
    elif intent == "definition":
        selected = chunks[:3]
    else:
        selected = chunks[:5]

    context_parts = []
    sources = set()

    for chunk in selected:
        source = chunk["metadata"].get("source", "Unknown")
        page = chunk["metadata"].get("page", "?")
        context_parts.append(f"[{source}, Page {page}]\n{chunk['text']}\n")
        sources.add(f"{source} (Page {page})")

    return "\n".join(context_parts), sources


def context_node(state):
    context, sources = build_context(
        state["question"],
        state["reranked"],
        state["categories"],
        state["intent"]
    )
    return {**state, "context": context, "sources": sources}


def generate_node(state):
    if not state["context"].strip():
        answer = "Information not found in the provided documents."
    else:
        prompt = answer_prompt.format(question=state["question"], context=state["context"])
        answer = gemma_llm(prompt).strip()
    return {**state, "answer": answer}


def validate_node(state):
    check = detect_hallucination(
        state["question"],
        state["context"],
        state["answer"]
    )

    retry_count = state.get("retry_count", 0)

    if check.get("is_hallucination"):
        retry_count += 1

    return {
        **state,
        "hallucination_check": check,
        "retry_count": retry_count
    }



def should_retry(state):
    if state["hallucination_check"]["is_hallucination"] and state["retry_count"] < MAX_RETRIES:
        return "retry"
    return "end"

def finalize_node(state):
    return {
        **state,
        "final": state["answer"]
    }



