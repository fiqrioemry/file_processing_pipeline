import ffmpeg
import math
from typing import List, Dict
from pathlib import Path
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class AudioChunker:
    def __init__(self):
        self.chunk_duration = settings.CHUNK_DURATION
        self.chunk_overlap = settings.CHUNK_OVERLAP
    
    async def create_chunks(self, audio_path: str, session_id: str) -> List[Dict]:
        """Split audio into overlapping chunks"""
        try:
            # Get audio duration
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['streams'][0]['duration'])
            
            logger.info(f"Creating chunks for audio duration: {duration} seconds")
            
            chunks = []
            chunk_id = 0
            start_time = 0.0
            
            while start_time < duration:
                end_time = min(start_time + self.chunk_duration, duration)
                
                # Create chunk file path
                chunk_path = Path(settings.TEMP_DIR) / "chunks" / f"{session_id}_chunk_{chunk_id}.wav"
                
                # Extract chunk using ffmpeg
                await self._extract_chunk(audio_path, str(chunk_path), start_time, end_time - start_time)
                
                chunks.append({
                    'chunk_id': chunk_id,
                    'path': str(chunk_path),
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time
                })
                
                chunk_id += 1
                
                # Move start time forward (with overlap)
                start_time += self.chunk_duration - self.chunk_overlap
                
                # Break if we've processed the entire audio
                if end_time >= duration:
                    break
            
            logger.info(f"Created {len(chunks)} audio chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to create audio chunks: {e}")
            raise Exception(f"Audio chunking failed: {str(e)}")
    
    async def _extract_chunk(self, input_path: str, output_path: str, start_time: float, duration: float):
        """Extract a single chunk from audio file"""
        try:
            (
                ffmpeg
                .input(input_path, ss=start_time, t=duration)
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
            
            logger.debug(f"Created chunk: {output_path}")
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode('utf-8') if e.stderr else str(e)
            logger.error(f"FFmpeg chunk extraction failed: {error_message}")
            raise Exception(f"Chunk extraction failed: {error_message}")
