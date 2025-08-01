from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChunkInfo(BaseModel):
    chunk_id: int
    start_time: float
    end_time: float
    duration: float
    transcript: str
    confidence: Optional[float] = None

class ProcessingResponse(BaseModel):
    success: bool
    message: str
    transcript: Optional[str] = None
    summary: Optional[str] = None
    chunks: Optional[List[ChunkInfo]] = None
    processing_stats: Optional[dict] = None
    timestamp: datetime = datetime.now()
    error_details: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime = datetime.now()

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = datetime.now()
