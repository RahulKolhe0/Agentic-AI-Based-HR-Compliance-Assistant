from typing import TypedDict, Set, Optional, Dict, List, Any
from langgraph.graph import StateGraph, END

from router.rules import rule_based_intent
from router.classifier import llm_intent_classifier
from router.dependency import detect_dependency
from router.question_splitter import split_multi_part_question
from router.entity_resolver import resolve_entity

from memory.retrieval import (
    get_memory_context,
    store_memory,
    get_active_entity
)

from router.hybrid_executor import (
    sql_depends_on_rag,
    rag_depends_on_sql,
    independent_run
)

from logger import get_logger
logger = get_logger("ROUTER")


# -----------------------------
# Router State
# -----------------------------
class RouterState(TypedDict):
    question: str
    intents: Set[str]
    user: Optional[Dict]
    final: str


# -----------------------------
# Detect Node (INTENT DETECTION & PLANNING)
# -----------------------------
def detect_intent_node(state):
    question = state["question"]

    # Step 1: Rule-based intent detection
    intents = rule_based_intent(question)

    if intents != {"unknown"}:
        print(f"\n🟢 Intent decided by RULES → {intents}")

    # Step 2: If unclear, fallback to LLM classifier
    if intents == {"unknown"}:
        intents = llm_intent_classifier(question)
        print(f"\n🔵 Intent decided by LLM → {intents}")
    
    logger.info(f"Detecting intent for: {question}")
    logger.info(f"Intent decided: {intents}")
    
    return {
        **state,
        "intents": intents,
        "final": ""
    }


# -----------------------------
# Routing Node (FIX 15 ACTIVE)
# -----------------------------
def route_node(state):

    user = state.get("user")

    # --------------------------------------------------
    # 🧠 Entity resolution FIRST
    # --------------------------------------------------
    try:
        resolved_entity, sanitized_question = resolve_entity(state["question"])
    except ValueError as e:
        return {**state, "final": str(e)}

    active_entity = get_active_entity()
    if resolved_entity["employeeid"] or resolved_entity["employeename"]:
        print(f"🧠 Active Entity → {active_entity}")

    # 👋 Greeting shortcut (safe, entity-agnostic)
    rule_intents = rule_based_intent(sanitized_question)
    if "greet" in rule_intents:
        return {**state, "final": "Hello! How can I help you today?"}

    # --------------------------------------------------
    # 1️⃣ Semantic planning
    # --------------------------------------------------
    planned_questions: List[str] = split_multi_part_question(sanitized_question)

    outputs: List[str] = []

    for idx, sub_q in enumerate(planned_questions, start=1):

        print(f"\n🔹 Processing planned question {idx}: {sub_q}")

        # --------------------------------------------------
        # 🧠 FIX 19 + FIX 25 — Global Query Detection (CRITICAL)
        # --------------------------------------------------
        def _is_global_query(q: str) -> bool:
            """
            Detect if question requires GLOBAL dataset (no entity scoping).
            
            FIX 19: Aggregates (how many, count, total)
            FIX 25: Rankings (highest, lowest, most, top)
            FIX 32: Policy questions (policy, posh, dress code)
            NEW FIX: "Remaining/Left" calculations for specific employees are NOT global
            
            These should NEVER inherit entity context.
            """
            q_lower = q.lower()
            
            # NEW: Detect "remaining/left" calculation queries (NOT global)
            # These ask "how many X left for [employee]" - specific, not global
            remaining_patterns = [
                "left for", "remaining for", "available for",
                "how many" and ("left" in q_lower or "remaining" in q_lower)
            ]
            
            # Check if this is a remaining/left calculation for a specific employee
            has_remaining_pattern = any(pattern in q_lower for pattern in ["left", "remaining", "available"])
            has_specific_entity = any(pattern in q_lower for pattern in ["for", "whose", "with id"])
            
            # If asking about remaining/left for a specific employee → NOT global
            if has_remaining_pattern and has_specific_entity:
                return False
            
            # FIX 19: Aggregate keywords
            aggregate_keywords = [
                "how many", "total number", "count", "all employees",
                "total employees", "number of employees", "sum of",
                "average", "total", "exceeded", "who all"
            ]
            
            # FIX 25: Ranking keywords
            ranking_keywords = [
                "highest", "lowest", "most", "least", "top", "bottom",
                "maximum", "minimum", "max", "min", "best", "worst",
                "largest", "smallest", "greatest"
            ]
            
            # FIX 32: Policy keywords
            policy_keywords = [
                "policy", "posh", "dress code", "procedure", "rules",
                "regulations", "guidelines", "harassment", "code of conduct"
            ]
            
            is_aggregate = any(kw in q_lower for kw in aggregate_keywords)
            is_ranking = any(kw in q_lower for kw in ranking_keywords)
            is_policy = any(kw in q_lower for kw in policy_keywords)
            
            return is_aggregate or is_ranking or is_policy

        # --------------------------------------------------
        # 🧠 FIX 13 — Entity inheritance (with FIX 19 + FIX 25 guards)
        # --------------------------------------------------
        sub_entity, _ = resolve_entity(sub_q)
        active_entity = get_active_entity()

        # FIX 19 + FIX 25: NEVER inherit entity for global queries
        is_global = _is_global_query(sub_q)
        
        if (
            not is_global
            and not sub_entity["employeeid"]
            and not sub_entity["employeename"]
            and active_entity
        ):
            if active_entity.get("employeeid"):
                sub_q = f"{sub_q} for employee id {active_entity['employeeid']}"
            elif active_entity.get("employeename"):
                sub_q = f"{sub_q} for employee {active_entity['employeename']}"

            print(f"🔁 Entity inherited → {active_entity}")
        elif is_global:
            print(f"🌍 Global query detected → NO entity inheritance")

        # --------------------------------------------------
        # 🧠 Intent from detect_intent_node
        # --------------------------------------------------
        intents = state["intents"]
        print(f"🎯 Intent (from global detection) → {intents}")

        # --------------------------------------------------
        # RAG memory ONLY if intent is truly rag
        # --------------------------------------------------
        enriched_q = sub_q
        if intents == {"rag"}:
            memory_context = get_memory_context(sub_q)
            if memory_context:
                enriched_q = f"""
Previous Conversation Memory:
{memory_context}

Now answer:
{sub_q}
"""

        # --------------------------------------------------
        # Dependency detection
        # --------------------------------------------------
        dependency = detect_dependency(sub_q)
        print(f"⚡ Dependency detected → {dependency}")

        # --------------------------------------------------
        # Execute pipeline
        # --------------------------------------------------
        if dependency == "sql_depends_on_rag":
            answer = sql_depends_on_rag(enriched_q, user)
        elif dependency == "rag_depends_on_sql":
            answer = rag_depends_on_sql(enriched_q, user)
        else:
            answer = independent_run(enriched_q, intents, user)

        outputs.append(answer)

    final_answer = "\n\n".join(outputs)

    # Store memory only if meaningful
    if final_answer and "❌" not in final_answer and "Hello" not in final_answer:
        store_memory(state["question"], final_answer)

    return {**state, "final": final_answer}


# -----------------------------
# Finalize Node
# -----------------------------
def finalize_node(state: RouterState) -> RouterState:
    return state


# -----------------------------
# Build Graph
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
