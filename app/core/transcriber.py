from typing import List, Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from app.services.openai_service import OpenAIService
from app.utils.response_models import ChunkInfo

logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.max_workers = 3  # Limit concurrent transcriptions
    
    async def transcribe_chunks(self, chunks: List[Dict]) -> List[ChunkInfo]:
        """Transcribe all audio chunks"""
        try:
            logger.info(f"Starting transcription of {len(chunks)} chunks")
            
            # Use thread pool for concurrent transcription
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Create tasks for all chunks
                tasks = []
                for chunk in chunks:
                    task = asyncio.get_event_loop().run_in_executor(
                        executor,
                        self._transcribe_single_chunk,
                        chunk
                    )
                    tasks.append(task)
                
                # Wait for all transcriptions to complete
                transcription_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle any failures
            successful_transcriptions = []
            failed_count = 0
            
            for i, result in enumerate(transcription_results):
                if isinstance(result, Exception):
                    logger.error(f"Chunk {i} transcription failed: {result}")
                    failed_count += 1
                    # Create empty transcript for failed chunk
                    chunk = chunks[i]
                    successful_transcriptions.append(ChunkInfo(
                        chunk_id=chunk['chunk_id'],
                        start_time=chunk['start_time'],
                        end_time=chunk['end_time'],
                        duration=chunk['duration'],
                        transcript="[Transcription failed]",
                        confidence=0.0
                    ))
                else:
                    successful_transcriptions.append(result)
            
            if failed_count > 0:
                logger.warning(f"{failed_count} chunks failed transcription")
            
            logger.info(f"Completed transcription. Success: {len(chunks) - failed_count}, Failed: {failed_count}")
            return successful_transcriptions
            
        except Exception as e:
            logger.error(f"Batch transcription failed: {e}")
            raise Exception(f"Transcription process failed: {str(e)}")
    
    def _transcribe_single_chunk(self, chunk: Dict) -> ChunkInfo:
        """Transcribe a single audio chunk (synchronous)"""
        try:
            # Use synchronous method in thread
            import openai
            client = openai.OpenAI(api_key=self.openai_service.client.api_key)
            
            with open(chunk['path'], "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            return ChunkInfo(
                chunk_id=chunk['chunk_id'],
                start_time=chunk['start_time'],
                end_time=chunk['end_time'],
                duration=chunk['duration'],
                transcript=transcript.strip(),
                confidence=1.0  # Whisper doesn't provide confidence scores
            )
            
        except Exception as e:
            logger.error(f"Single chunk transcription failed for chunk {chunk['chunk_id']}: {e}")
            raise e
    
    def combine_transcripts(self, transcriptions: List[ChunkInfo]) -> str:
        """Combine all chunk transcripts into a single text"""
        try:
            # Sort by chunk_id to ensure correct order
            sorted_transcriptions = sorted(transcriptions, key=lambda x: x.chunk_id)
            
            # Combine transcripts with timestamps
            combined_parts = []
            for trans in sorted_transcriptions:
                if trans.transcript and trans.transcript != "[Transcription failed]":
                    # Format timestamp (MM:SS)
                    start_minutes = int(trans.start_time // 60)
                    start_seconds = int(trans.start_time % 60)
                    
                    timestamp = f"[{start_minutes:02d}:{start_seconds:02d}]"
                    combined_parts.append(f"{timestamp} {trans.transcript}")
            
            combined_transcript = "\n\n".join(combined_parts)
            logger.info(f"Combined {len(combined_parts)} transcripts into full text")
            
            return combined_transcript
            
        except Exception as e:
            logger.error(f"Failed to combine transcripts: {e}")
            raise Exception(f"Transcript combination failed: {str(e)}")

