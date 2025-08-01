import ffmpeg
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

class AudioExtractor:
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
    
    async def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio from video file using ffmpeg"""
        try:
            logger.info(f"Extracting audio from: {video_path}")
            
            # Extract audio with optimized settings
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    acodec='pcm_s16le',  # 16-bit PCM for compatibility
                    ac=1,                # Mono audio
                    ar=16000,            # 16kHz sample rate (optimal for Whisper)
                    loglevel='error'     # Reduce ffmpeg verbosity
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f"Successfully extracted audio to: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode('utf-8') if e.stderr else str(e)
            logger.error(f"FFmpeg audio extraction failed: {error_message}")
            raise Exception(f"Audio extraction failed: {error_message}")
        
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            raise Exception(f"Audio extraction failed: {str(e)}")
    
    def get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds"""
        try:
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['streams'][0]['duration'])
            logger.info(f"Audio duration: {duration} seconds")
            return duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
