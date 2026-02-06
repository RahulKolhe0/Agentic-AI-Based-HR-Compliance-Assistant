import re
from typing import Dict, Optional, Tuple

from memory.retrieval import set_active_entity, get_active_entity


# --------------------------------------------------
# Regex patterns (STRICT, DETERMINISTIC)
# --------------------------------------------------

EMP_ID_PATTERN = re.compile(
    r"\b(?:employee\s*id|emp\s*id|id)\s*(?:is|=)?\s*(\d{2,10})\b",
    re.IGNORECASE
)

EMP_NAME_PATTERN = re.compile(
    r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b"
)

PRONOUN_PATTERN = re.compile(
    r"\b(her|him|his|this|that|it|this employee|that employee)\b",
    re.IGNORECASE
)

# Attribute-only questions (FIX 14)
EMPTY_ENTITY_PATTERN = re.compile(
    r"^\s*(what\s+is|give\s+me|show)\s+(the\s+)?"
    r"(name|id|employee\s*id|joining\s+date|salary)\s*\??\s*$",
    re.IGNORECASE
)

# FIX 20: Company name blacklist (NOT employee names)
COMPANY_SUFFIXES = {
    "pharma", "ltd", "limited", "inc", "corp", "corporation",
    "bank", "company", "co", "pvt", "llc", "group", "ppl"
}

# FIX 31: Column/metric name blacklist (NOT employee names)
COLUMN_NAME_BLACKLIST = {
    "overtime hours", "work hours", "sick leaves", "sick leave",
    "leave balance", "years at company", "years in role",
    "monthly salary", "annual salary", "date of joining",
    "joining date", "manager code", "compliance risk",
    "performance rating", "hours last month", "per week",
    "last month", "work hours per week", "overtime hours last month"
}


# --------------------------------------------------
# FIX 20 + FIX 31: Employee Name Validation
# --------------------------------------------------
def _is_valid_employee_name(name: str) -> bool:
    """
    Validate extracted name is actually an employee.
    
    FIX 20: Rejects company names
    FIX 31: Rejects column/metric names
    
    Rules:
    - Must have 2+ words (first + last name)
    - Each word must be 3+ characters
    - NOT all caps (likely acronym)
    - NOT containing company suffixes
    - NOT column/metric names
    """
    parts = name.split()
    name_lower = name.lower()
    
    # Single word → likely company/acronym
    if len(parts) < 2:
        return False
    
    # All caps → likely acronym (PPL, IBM, etc.)
    if name.isupper():
        return False
    
    # Check each part
    for part in parts:
        # Too short
        if len(part) < 3:
            return False
        
        # FIX 20: Company suffix detected
        if part.lower() in COMPANY_SUFFIXES:
            return False
    
    # FIX 31: Reject column/metric names
    if any(col in name_lower for col in COLUMN_NAME_BLACKLIST):
        return False
    
    return True


# --------------------------------------------------
# Main Resolver
# --------------------------------------------------
def resolve_entity(question: str) -> Tuple[Dict[str, Optional[str]], str]:
    """
    FIX 9 + FIX 10 + FIX 14

    Responsibilities:
    - Extract employeeid / employeename
    - Update Active Entity Context
    - Resolve pronouns deterministically
    - BLOCK underspecified questions early
    """

    resolved: Dict[str, Optional[str]] = {
        "employeeid": None,
        "employeename": None
    }

    sanitized_question = question.strip()

    # --------------------------------------------------
    # 🛑 FIX 14 — Underspecified question guard
    # --------------------------------------------------
    if EMPTY_ENTITY_PATTERN.match(sanitized_question):
        active_entity = get_active_entity()
        if not active_entity or (
            not active_entity.get("employeeid")
            and not active_entity.get("employeename")
        ):
            raise ValueError(
                "❌ This question is incomplete. Please specify which employee "
                "you are asking about."
            )

    # --------------------------------------------------
    # 1️⃣ Extract employee ID
    # --------------------------------------------------
    id_match = EMP_ID_PATTERN.search(sanitized_question)
    if id_match:
        resolved["employeeid"] = id_match.group(1)

    # --------------------------------------------------
    # 2️⃣ Extract employee NAME (FIX 20: with validation)
    # --------------------------------------------------
    name_match = EMP_NAME_PATTERN.search(sanitized_question)
    if name_match:
        candidate_name = f"{name_match.group(1)} {name_match.group(2)}"
        
        # FIX 20: Validate before accepting
        if _is_valid_employee_name(candidate_name):
            resolved["employeename"] = candidate_name
        else:
            # Reject company names silently
            pass


    # --------------------------------------------------
    # 3️⃣ Update Active Entity Context
    # --------------------------------------------------
    if resolved["employeeid"] or resolved["employeename"]:
        set_active_entity(
            employeeid=resolved["employeeid"],
            employeename=resolved["employeename"]
        )

    # --------------------------------------------------
    # 4️⃣ Pronoun resolution (FIX 10)
    # --------------------------------------------------
    pronoun_match = PRONOUN_PATTERN.search(sanitized_question)
    if pronoun_match:
        active_entity = get_active_entity()

        if not active_entity or (
            not active_entity.get("employeeid")
            and not active_entity.get("employeename")
        ):
            raise ValueError(
                "❌ Pronoun used but no active employee context exists. "
                "Please specify the employee explicitly."
            )

        if active_entity.get("employeeid"):
            replacement = f"employee id {active_entity['employeeid']}"
        else:
            replacement = active_entity["employeename"]

        sanitized_question = PRONOUN_PATTERN.sub(
            replacement,
            sanitized_question,
            count=1
        )

    return resolved, sanitized_question
