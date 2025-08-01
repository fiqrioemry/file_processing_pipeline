import time
from typing import Optional
import logging
from fastapi import UploadFile
from app.core.audio_extractor import AudioExtractor
from app.core.chunker import AudioChunker
from app.core.transcriber import Transcriber
from app.services.summarizer import SummarizerService
from app.utils.temp_manager import TempManager
from app.utils.file_handler import FileHandler
from app.utils.response_models import ProcessingResponse, ChunkInfo
from app.config import settings

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.audio_extractor = AudioExtractor()
        self.chunker = AudioChunker()
        self.transcriber = Transcriber()
        self.summarizer = SummarizerService()
        self.temp_manager = TempManager()
        self.file_handler = FileHandler()
    
    async def process_video_file(self, video_file: UploadFile, summarizer_service: str = None) -> ProcessingResponse:
        """Process uploaded video file"""
        session_id = self.temp_manager.generate_session_id()
        start_time = time.time()
        
        try:
            logger.info(f"Starting video processing for session: {session_id}")
            
            # Validate file format
            if not self.file_handler.validate_video_file(video_file.filename):
                return ProcessingResponse(
                    success=False,
                    message="Unsupported video format",
                    error_details=f"File: {video_file.filename}"
                )
            
            # Save uploaded file
            video_path = await self.temp_manager.save_uploaded_file(video_file, session_id)
            
            # Validate file size
            if not self.file_handler.validate_file_size(video_path, settings.MAX_FILE_SIZE):
                return ProcessingResponse(
                    success=False,
                    message=f"File too large. Maximum size: {settings.MAX_FILE_SIZE}MB",
                    error_details=f"File size: {self.file_handler.get_file_size_mb(video_path):.1f}MB"
                )
            
            # Process the video
            result = await self._process_video_pipeline(video_path, session_id, summarizer_service)
            
            # Add processing stats
            processing_time = time.time() - start_time
            result.processing_stats = {
                "total_time_seconds": round(processing_time, 2),
                "file_size_mb": round(self.file_handler.get_file_size_mb(video_path), 2),
                "session_id": session_id
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Video processing failed for session {session_id}: {e}")
            return ProcessingResponse(
                success=False,
                message="Video processing failed",
                error_details=str(e)
            )
        
        finally:
            # Cleanup temporary files
            self.temp_manager.cleanup_session(session_id)
    
    async def process_video_url(self, video_url: str, summarizer_service: str = None) -> ProcessingResponse:
        """Process video from URL"""
        session_id = self.temp_manager.generate_session_id()
        start_time = time.time()
        
        try:
            logger.info(f"Starting video URL processing for session: {session_id}")
            
            # Download video file
            video_path = await self.temp_manager.download_file(video_url, session_id)
            
            # Validate file size
            if not self.file_handler.validate_file_size(video_path, settings.MAX_FILE_SIZE):
                return ProcessingResponse(
                    success=False,
                    message=f"File too large. Maximum size: {settings.MAX_FILE_SIZE}MB",
                    error_details=f"File size: {self.file_handler.get_file_size_mb(video_path):.1f}MB"
                )
            
            # Process the video
            result = await self._process_video_pipeline(video_path, session_id, summarizer_service)
            
            # Add processing stats
            processing_time = time.time() - start_time
            result.processing_stats = {
                "total_time_seconds": round(processing_time, 2),
                "file_size_mb": round(self.file_handler.get_file_size_mb(video_path), 2),
                "source_url": video_url,
                "session_id": session_id
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Video URL processing failed for session {session_id}: {e}")
            return ProcessingResponse(
                success=False,
                message="Video URL processing failed",
                error_details=str(e)
            )
        
        finally:
            # Cleanup temporary files
            self.temp_manager.cleanup_session(session_id)
    
    async def