def detect_dependency(question: str) -> str:
    """
    Decide pipeline execution order based on semantic intent.

    Semantic categories:
    1. policy_lookup       → RAG only
    2. policy_application  → RAG → SQL (MANDATORY)
    3. data_lookup         → SQL only
    4. data_explanation    → SQL → RAG

    Returns:
        "sql_depends_on_rag"
        "rag_depends_on_sql"
        "independent"
    """

    q = question.lower().strip()

    # =================================================
    # 1️⃣ POLICY LOOKUP (RAG ONLY)
    # =================================================
    # Asking what the rule / limit is — NO data action
    policy_lookup_triggers = [
        "what is the policy",
        "according to the policy",
        "policy says",
        "what is the maximum",
        "what is the allowed",
        "maximum allowed sick leaves",
        "allowed sick leaves",
        "allowed limit",
        "policy limit"
    ]

    data_action_words = [
        "how many",
        "count",
        "number of",
        "employees",
        "who",
        "list",
        "exceeded"
    ]

    if any(p in q for p in policy_lookup_triggers) and not any(
        d in q for d in data_action_words
    ):
        # Router intents will ensure RAG-only execution
        return "independent"


    # =================================================
    # 2️⃣ POLICY APPLICATION (RAG → SQL)
    # =================================================
    # Policy threshold MUST be fetched before analytics
    policy_application_triggers = [
        "as per policy",
        "according to policy",
        "based on policy",
        "maximum allowed",
        "allowed limit",
        "policy limit",
        "exceeded allowed",
        "exceeded maximum",
        "more than allowed",
        "above allowed"
    ]

    analytics_triggers = [
        "how many",
        "count",
        "number of employees",
        "employees exceeded",
        "who exceeded",
        "list employees"
    ]

    # NEW: Remaining/Left calculation patterns (requires policy limit)
    # Examples: "how many sick leaves left", "remaining casual leaves"
    remaining_calculation_triggers = [
        "left", "remaining", "available", "balance"
    ]
    
    resource_types = [
        "sick leave", "casual leave", "privilege leave",
        "leave", "leaves", "days off"
    ]

    # Check for remaining/left calculations
    # Pattern: "how many [resource] left/remaining for [employee]"
    has_remaining = any(r in q for r in remaining_calculation_triggers)
    has_resource = any(res in q for res in resource_types)
    
    if has_remaining and has_resource:
        # This needs policy limit first, then SQL calculation
        return "sql_depends_on_rag"

    if any(p in q for p in policy_application_triggers) and any(
        a in q for a in analytics_triggers
    ):
        return "sql_depends_on_rag"


    # =================================================
    # 3️⃣ DATA → POLICY EXPLANATION (SQL → RAG)
    # =================================================
    explanation_triggers = [
        "based on employee data",
        "according to dataset",
        "explain this",
        "what does this mean",
        "policy implication",
        "interpret this",
        "is this allowed"
    ]

    if any(e in q for e in explanation_triggers):
        return "rag_depends_on_sql"


    # =================================================
    # 4️⃣ PURE DATA LOOKUP (SQL ONLY)
    # =================================================
    data_only_triggers = [
        "how many employees",
        "count",
        "list",
        "show",
        "who has",
        "highest",
        "lowest",
        "average",
        "maximum",
        "minimum",
        "joining date",
        "manager code",
        "years at company",
        "years in current role"
    ]

    if any(d in q for d in data_only_triggers):
        return "independent"


    # =================================================
    # 5️⃣ DEFAULT (SAFE)
    # =================================================
    return "independent"
