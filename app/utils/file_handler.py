# app/utils/file_handler.py
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FileHandler:
    SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.webm'}
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    
    @staticmethod
    def validate_audio_file(filename: str) -> bool:
        """Check if file has supported audio format"""
        if not filename:
            return False
        file_extension = Path(filename).suffix.lower()
        return file_extension in FileHandler.SUPPORTED_AUDIO_FORMATS
    
    @staticmethod
    def validate_video_file(filename: str) -> bool:
        """Check if file has supported video format"""
        if not filename:
            return False
        file_extension = Path(filename).suffix.lower()
        return file_extension in FileHandler.SUPPORTED_VIDEO_FORMATS
    
    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """Get file size in megabytes"""
        try:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except Exception as e:
            logger.error(f"Failed to get file size for {file_path}: {e}")
            return 0.0
    
    @staticmethod
    def validate_file_size(file_path: str, max_size_mb: int) -> bool:
        """Validate file size against maximum limit"""
        file_size = FileHandler.get_file_size_mb(file_path)
        return file_size <= max_size_mb
