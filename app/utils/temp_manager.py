# =====================================================================================
# FILE: app/utils/temp_manager.py (Updated)
# =====================================================================================
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.services.audio_service import AudioService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class TempManager:
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
        self.audio_dir = self.temp_dir / "audio"
        self.chunks_dir = self.temp_dir / "chunks"
        self.audio_service = AudioService()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create all required directories"""
        for directory in [self.audio_dir, self.chunks_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())
    
    async def save_uploaded_file(self, file: UploadFile, session_id: str) -> str:
        """Save uploaded audio file to temporary directory"""
        file_extension = Path(file.filename).suffix
        temp_filename = f"{session_id}_audio{file_extension}"
        temp_path = self.audio_dir / temp_filename
            
        try:
            async with aiofiles.open(temp_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
                
            logger.info(f"Saved uploaded audio file: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise
    
    async def download_audio_from_url(self, url: str, session_id: str) -> str:
        """Download audio directly from URL using audio service"""
        try:
            return await self.audio_service.download_audio_from_url(url, session_id)
        except Exception as e:
            logger.error(f"Failed to download audio from {url}: {e}")
            raise
    
    def get_chunk_path(self, session_id: str, chunk_id: int) -> str:
        """Get chunk file path for session and chunk ID"""
        return str(self.chunks_dir / f"{session_id}_chunk_{chunk_id}.wav")
    
    def cleanup_session(self, session_id: str):
        """Clean up all files for a specific session"""
        try:
            for directory in [self.audio_dir, self.chunks_dir]:
                for file_path in directory.glob(f"{session_id}_*"):
                    file_path.unlink(missing_ok=True)
                    
            logger.debug(f"Cleaned up session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")