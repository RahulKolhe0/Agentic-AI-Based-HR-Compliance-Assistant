from typing import TypedDict, Set, Optional, Dict
from langgraph.graph import StateGraph, END

from router.rules import rule_based_intent
from router.classifier import llm_intent_classifier

from memory.retrieval import get_memory_context, store_memory

from router.dependency import detect_dependency
from router.hybrid_executor import (
    sql_depends_on_rag,
    rag_depends_on_sql,
    independent_run
)


# -----------------------------
# Router State (Updated)
# -----------------------------
class RouterState(TypedDict):
    question: str
    intents: Set[str]
    user: Optional[Dict]     # ✅ Needed for RBAC
    final: str


# -----------------------------
# Intent Detection Node
# -----------------------------
def detect_intent_node(state):
    question = state["question"]

    # Step 1: Rule-based intent detection
    intents = rule_based_intent(question)

    if intents != {"unknown"}:
        print(f"\n🟢 Intent decided by RULES → {intents}")

    # Step 2: Fallback to LLM classifier
    if intents == {"unknown"}:
        intents = llm_intent_classifier(question)
        print(f"\n🔵 Intent decided by LLM → {intents}")

    return {
        **state,
        "intents": intents,
        "final": ""
    }


# -----------------------------
# Routing Node (Memory + Dependency)
# -----------------------------
def route_node(state):

    question = state["question"]
    intents = state["intents"]
    user = state.get("user", None)

    # -----------------------------
    # Greeting Shortcut
    # -----------------------------
    if "greet" in intents:
        return {**state, "final": "Hello! How can I help you today?"}

    # -----------------------------
    # ✅ Step 1: Memory Retrieval ONLY for RAG
    # -----------------------------
    enriched_question = question

    if "rag" in intents:
        memory_context = get_memory_context(question)

        if memory_context:
            print("🧠 Memory Match Found! Injecting context...")

            enriched_question = f"""
Previous Conversation Memory:
{memory_context}

Now answer the new question:
{question}
"""

    # -----------------------------
    # ✅ Step 2: Dependency Detection
    # -----------------------------
    dependency = detect_dependency(question)
    print(f"⚡ Dependency detected → {dependency}")

    # -----------------------------
    # ✅ Step 3: Execute Pipelines
    # -----------------------------
    if dependency == "sql_depends_on_rag":
        final = sql_depends_on_rag(enriched_question, user)

    elif dependency == "rag_depends_on_sql":
        final = rag_depends_on_sql(enriched_question, user)

    else:
        final = independent_run(enriched_question, intents, user)

    # -----------------------------
    # ✅ Step 4: Store Memory Only if Useful
    # -----------------------------
    if final and "❌" not in final and "Hello" not in final:
        store_memory(question, final)

    return {**state, "final": final}


# -----------------------------
# Finalize Node
# -----------------------------
def finalize_node(state: RouterState) -> RouterState:
    return state


# -----------------------------
# Build LangGraph Router
# -----------------------------
graph = StateGraph(RouterState)

graph.add_node("detect", detect_intent_node)
graph.add_node("route", route_node)
graph.add_node("finalize", finalize_node)

graph.set_entry_point("detect")

graph.add_edge("detect", "route")
graph.add_edge("route", "finalize")
graph.add_edge("finalize", END)

router_app = graph.compile()
