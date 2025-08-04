# app/utils/response_models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List
    
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


class TranscriptionSegment(BaseModel):
    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")  
    text: str = Field(..., description="Transcribed text")
    confidence: Optional[float] = Field(None, description="Confidence score")

class TranscriptionResponse(BaseModel):
    transcript: str = Field(..., description="Full transcribed text")
    language: str = Field(..., description="Detected language")
    language_confidence: float = Field(..., description="Language detection confidence")
    segments: Optional[List[TranscriptionSegment]] = Field(None, description="Text segments with timestamps")
    processing_stats: Dict[str, Any] = Field(..., description="Processing statistics")