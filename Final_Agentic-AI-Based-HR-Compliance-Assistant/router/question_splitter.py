import re
from typing import List


# --------------------------------------------------
# Attribute vocabulary (planner-level, NOT SQL)
# --------------------------------------------------
ATTRIBUTE_KEYWORDS = {
    "name",
    "id",
    "employee id",
    "employeeid",
    "joining date",
    "date of joining",
    "salary",
    "monthly salary",
    "manager",
    "manager code",
    "years at company",
    "years in current role",
    "sick leaves",
    "leave balance"
}


def split_multi_part_question(question: str) -> List[str]:
    """
    FIX 22 — Intelligent Question Splitting

    Rules:
    1. ONE entity + multiple attributes → ONE question
    2. "also give me X also Y" → split into separate questions
    3. Multiple different metrics (highest X, highest Y, highest Z) → split
    4. NEVER split 'name and id' style queries

    Returns:
        List[str] — planned logical questions
    """

    q = question.strip().rstrip("?")
    lowered = q.lower()

    # --------------------------------------------------
    # 1️⃣ Detect attribute-style conjunctions (same entity)
    # --------------------------------------------------
    attribute_hits = [
        attr for attr in ATTRIBUTE_KEYWORDS
        if attr in lowered
    ]

    # If multiple attributes but SAME entity → DO NOT SPLIT
    if len(attribute_hits) >= 2 and "also" not in lowered:
        return [question]

    # --------------------------------------------------
    # FIX 22: Detect multiple DIFFERENT metrics/intents
    # --------------------------------------------------
    different_metrics = [
        "highest years at company",
        "highest years in current role",
        "highest years in role",
        "highest sick leaves",
        "most sick leaves",
        "maximum salary",
        "highest salary"
    ]
    
    metric_hits = [m for m in different_metrics if m in lowered]
    
    # If multiple different metrics → MUST split
    if len(metric_hits) >= 2:
        # Try to split intelligently on "also"
        parts = re.split(r"\balso give me\b|\balso what is\b|\band also\b", q, flags=re.IGNORECASE)
        if len(parts) > 1:
            planned = []
            for part in parts:
                part = part.strip()
                if len(part.split()) < 3:
                    continue
                if not part.lower().startswith(("what", "how", "give", "show", "who")):
                    part = "Give me " + part
                planned.append(part + "?")
            return planned if planned else [question]

    # --------------------------------------------------
    # 2️⃣ Split ONLY on true question boundaries
    # --------------------------------------------------
    separators = [
        r"\?\s+",
        r"\.\s+",
        r"\band then\b",
        r"\balso tell me\b"
    ]

    parts = [q]
    for sep in separators:
        temp = []
        for p in parts:
            temp.extend(re.split(sep, p, flags=re.IGNORECASE))
        parts = temp

    planned: List[str] = []

    for part in parts:
        part = part.strip()
        if len(part.split()) < 3:
            continue

        if not part.lower().startswith(("what", "how", "give", "show", "list", "who")):
            part = "Give me " + part

        planned.append(part + "?")

    return planned if planned else [question]
