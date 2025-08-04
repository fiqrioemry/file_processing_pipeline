# app/core/chunker.py
import ffmpeg
import logging
import asyncio

from pathlib import Path
from typing import List, Dict
from app.config import settings

logger = logging.getLogger(__name__)

class AudioChunker:
    def __init__(self):
        self.chunk_duration = settings.CHUNK_DURATION
        self.chunk_overlap = settings.CHUNK_OVERLAP
    
    async def create_chunks(self, audio_path: str, session_id: str) -> List[Dict]:
        """Split audio into overlapping chunks for transcription with optimized processing"""
        try:
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['streams'][0]['duration'])
            
            # Skip chunking for short files
            if duration <= self.chunk_duration:
                logger.info(f"Audio duration {duration}s <= chunk size, skipping chunking")
                return [{
                    'chunk_id': 0,
                    'path': audio_path,
                    'start_time': 0.0,
                    'end_time': duration,
                    'duration': duration
                }]
            
            chunks_dir = Path(settings.TEMP_DIR) / "chunks"
            chunks_dir.mkdir(parents=True, exist_ok=True)
            
            # Calculate all chunks first
            chunk_specs = []
            chunk_id = 0
            start_time = 0.0
            
            while start_time < duration:
                end_time = min(start_time + self.chunk_duration, duration)
                chunk_path = chunks_dir / f"{session_id}_chunk_{chunk_id}.wav"
                
                chunk_specs.append({
                    'chunk_id': chunk_id,
                    'path': str(chunk_path),
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'input_path': audio_path
                })
                
                chunk_id += 1
                start_time += self.chunk_duration - self.chunk_overlap
                
                if end_time >= duration:
                    break
            
            # Process chunks in batches to reduce I/O overhead
            batch_size = 4  # Process 4 chunks at a time
            chunks = []
            
            for i in range(0, len(chunk_specs), batch_size):
                batch = chunk_specs[i:i + batch_size]
                batch_tasks = [self._extract_chunk_optimized(spec) for spec in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for spec, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to process chunk {spec['chunk_id']}: {result}")
                        continue
                    chunks.append({
                        'chunk_id': spec['chunk_id'],
                        'path': spec['path'],
                        'start_time': spec['start_time'],
                        'end_time': spec['end_time'],
                        'duration': spec['duration']
                    })
            
            logger.info(f"Successfully created {len(chunks)} chunks from {duration}s audio")
            return chunks
            
        except Exception as e:
            raise Exception(f"Audio chunking failed: {str(e)}")
    
    async def _extract_chunk_optimized(self, chunk_spec: Dict):
        """Extract a single audio chunk with optimized parameters"""
        try:
            (
                ffmpeg
                .input(
                    chunk_spec['input_path'], 
                    ss=chunk_spec['start_time'], 
                    t=chunk_spec['duration']
                )
                .output(
                    chunk_spec['path'],
                    acodec='pcm_s16le',
                    ac=1,
                    ar=16000,
                    loglevel='error'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode('utf-8') if e.stderr else str(e)
            raise Exception(f"Chunk extraction failed: {error_message}")
    
    async def _extract_chunk(self, input_path: str, output_path: str, start_time: float, duration: float):
        """Legacy method - kept for backward compatibility"""
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
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode('utf-8') if e.stderr else str(e)
            raise Exception(f"Chunk extraction failed: {error_message}")