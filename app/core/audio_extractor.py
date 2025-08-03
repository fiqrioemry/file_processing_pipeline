# app/core/audio_extractor.py
import ffmpeg
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

class AudioExtractor:
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_DIR)
    
    async def extract_audio(self, video_path: str, output_path: str) -> str:
        try:
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    acodec='pcm_s16le', 
                    ac=1,            
                    ar=16000,    
                    loglevel='error'   
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return output_path
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode('utf-8') if e.stderr else str(e)
            raise Exception(f"Audio extraction failed: {error_message}")
        except Exception as e:
            raise Exception(f"Audio extraction failed: {str(e)}")
    
    def get_audio_duration(self, audio_path: str) -> float:
        try:
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['streams'][0]['duration'])
            logger.info(f"Audio duration: {duration} seconds")
            return duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
