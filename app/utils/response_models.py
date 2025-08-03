# app/utils/response_models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
    
class ChunkInfo(BaseModel):
    chunk_id: int
    start_time: float
    end_time: float
    duration: float
    transcript: str
    confidence: Optional[float] = None


class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
