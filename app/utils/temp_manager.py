import os
import shutil
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class TempManager:
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
        self.video_dir = self.temp_dir / "videos"
        self.audio_dir = self.temp_dir / "audio"
        self.chunks_dir = self.temp_dir / "chunks"
        
        # Create directories if they don't exist
        for directory in [self.video_dir, self.audio_dir, self.chunks_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def generate_session_id(self) -> str:
        """Generate unique session ID for file processing"""
        return str(uuid.uuid4())
    
    async def save_uploaded_file(self, file: UploadFile, session_id: str) -> str:
        """Save uploaded file to temp directory"""
        file_extension = Path(file.filename).suffix
        temp_filename = f"{session_id}_video{file_extension}"
        temp_path = self.video_dir / temp_filename
        
        try:
            async with aiofiles.open(temp_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            logger.info(f"Saved uploaded file: {temp_path}")
            return str(temp_path)
        
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise
    
    async def download_file(self, url: str, session_id: str) -> str:
        """Download file from URL to temp directory"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Get file extension from URL or default to .mp4
                file_extension = Path(url).suffix or ".mp4"
                temp_filename = f"{session_id}_video{file_extension}"
                temp_path = self.video_dir / temp_filename
                
                async with aiofiles.open(temp_path, 'wb') as f:
                    await f.write(response.content)
                
                logger.info(f"Downloaded file from URL: {temp_path}")
                return str(temp_path)
        
        except Exception as e:
            logger.error(f"Failed to download file from {url}: {e}")
            raise
    
    def get_audio_path(self, session_id: str) -> str:
        """Get audio file path for session"""
        return str(self.audio_dir / f"{session_id}_audio.wav")
    
    def get_chunk_path(self, session_id: str, chunk_id: int) -> str:
        """Get chunk file path"""
        return str(self.chunks_dir / f"{session_id}_chunk_{chunk_id}.wav")
    
    def cleanup_session(self, session_id: str):
        """Clean up all temp files for a session"""
        try:
            # Clean video files
            for file_path in self.video_dir.glob(f"{session_id}_*"):
                file_path.unlink(missing_ok=True)
            
            # Clean audio files
            for file_path in self.audio_dir.glob(f"{session_id}_*"):
                file_path.unlink(missing_ok=True)
            
            # Clean chunk files
            for file_path in self.chunks_dir.glob(f"{session_id}_*"):
                file_path.unlink(missing_ok=True)
            
            logger.info(f"Cleaned up session: {session_id}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
    
    def cleanup_all(self, max_age_hours: int = 24):
        """Clean up old temp files"""
        import time
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        for directory in [self.video_dir, self.audio_dir, self.chunks_dir]:
            try:
                for file_path in directory.iterdir():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink(missing_ok=True)
                        logger.info(f"Cleaned old file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning directory {directory}: {e}")
