from pydantic import BaseModel
from typing import Optional, List, Set


class QueryRequest(BaseModel):
    question: str
    user: dict


class QueryResponse(BaseModel):
    question: str
    answer: str
    intents: Optional[Set[str]] = None
