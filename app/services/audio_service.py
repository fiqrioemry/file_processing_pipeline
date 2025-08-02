# =====================================================================================
# FILE: app/services/audio_service.py
# =====================================================================================
import yt_dlp
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any 
from app.config import settings
from app.utils.response_helpers import raise_unprocessable_entity_error, raise_payload_too_large_error

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
        self.audio_dir = self.temp_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_audio_from_url(self, url: str, session_id: str) -> str:
        """Download audio directly from video URL using yt-dlp"""
        filename = f"{session_id}_audio"
        output_template = str(self.audio_dir / f"{filename}.%(ext)s")
        
        try:
            logger.info(f"Downloading audio directly from: {url}")
            
            result = subprocess.run([
                "yt-dlp",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",  # Best audio quality
                "-x",  # Extract audio
                "--audio-format", "wav",  # Convert to WAV
                "--audio-quality", "0",  # Best quality
                "--output", output_template,
                "--no-playlist",
                "--no-warnings",
                "--postprocessor-args", "-ar 16000 -ac 1",  # 16kHz mono for Whisper
                url
            ], check=True, capture_output=True, text=True, timeout=300)
            
            # Find downloaded audio file
            audio_path = self._find_downloaded_file(filename)
            
            if not audio_path.exists():
                raise_unprocessable_entity_error("Audio download failed", "Downloaded file not found")
                
            logger.info(f"Successfully downloaded audio to: {audio_path}")
            return str(audio_path)
            
        except subprocess.TimeoutExpired:
            raise_unprocessable_entity_error("Audio download timeout", "Download took too long")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or "Unknown yt-dlp error"
            raise_unprocessable_entity_error("Audio download failed", f"yt-dlp error: {error_msg}")
    
    async def validate_video_url(self, video_url: str) -> Dict[str, Any]:
        """Validate video URL and get metadata using yt-dlp"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'format': 'bestaudio'  # Only check audio availability
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Validate duration first
                duration = info.get('duration')
                if duration and duration > settings.MAX_VIDEO_DURATION:
                    raise_payload_too_large_error(
                        f"Video too long. Max duration: {settings.MAX_VIDEO_DURATION} seconds",
                        f"Duration: {duration} seconds ({duration//60}:{duration%60:02d})"
                    )
                
                # Check estimated file size
                filesize = info.get('filesize')
                if filesize:
                    filesize_mb = filesize / (1024 * 1024)
                    if filesize_mb > settings.MAX_FILE_SIZE:
                        raise_payload_too_large_error(
                            f"File too large. Max size: {settings.MAX_FILE_SIZE}MB",
                            f"Estimated size: {filesize_mb:.1f}MB"
                        )
                
                return {
                    "is_valid": True,
                    "title": info.get('title', 'Unknown'),
                    "duration": duration,
                    "filesize": filesize,
                    "uploader": info.get('uploader'),
                    "view_count": info.get('view_count')
                }
                
        except Exception as e:
            logger.error(f"Video URL validation failed: {e}")
            raise_unprocessable_entity_error("Video URL validation failed", str(e))
    
    def _find_downloaded_file(self, filename: str) -> Path:
        """Find downloaded audio file with various extensions"""
        for ext in ['.wav', '.m4a', '.mp3', '.webm']:
            audio_path = self.audio_dir / f"{filename}{ext}"
            if audio_path.exists():
                return audio_path
        
        # Fallback: search for any file with the filename
        for file_path in self.audio_dir.glob(f"{filename}.*"):
            return file_path
            
        return self.audio_dir / f"{filename}.wav"  # fallback
