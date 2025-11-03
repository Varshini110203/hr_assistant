from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    response: str
    source_document: Optional[str] = None
    confidence: Optional[float] = None

class ChatMessage(BaseModel):
    query: str
    response: str
    timestamp: datetime