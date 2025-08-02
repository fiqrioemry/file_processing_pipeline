# app/core/transcriber.py
import asyncio
import logging
import openai
import ffmpeg
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor
from app.services.openai_service import OpenAIService
from app.utils.response_models import ChunkInfo

logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.max_workers = 3  
    
    async def transcribe_chunks(self, chunks: List[Dict]) -> Tuple[List[ChunkInfo], Dict]:
        try:
            logger.info(f"Starting transcription of {len(chunks)} chunks")
            
            # Use thread pool for concurrent transcription
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                tasks = []
                for chunk in chunks:
                    task = asyncio.get_event_loop().run_in_executor(
                        executor,
                        self._transcribe_single_chunk,
                        chunk
                    )
                    tasks.append(task)
                
                transcription_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and aggregate ACTUAL costs
            successful_transcriptions = []
            failed_count = 0
            total_whisper_cost = 0.0
            total_audio_minutes = 0.0
            total_transcription_tokens = 0
            
            for i, result in enumerate(transcription_results):
                if isinstance(result, Exception):
                    logger.error(f"Chunk {i} transcription failed: {result}")
                    failed_count += 1
                    chunk = chunks[i]
                    failed_chunk_info = ChunkInfo(
                        chunk_id=chunk['chunk_id'],
                        start_time=chunk['start_time'],
                        end_time=chunk['end_time'],
                        duration=chunk['duration'],
                        transcript="[Transcription failed]",
                        confidence=0.0
                    )
                    successful_transcriptions.append(failed_chunk_info)
                else:
                    chunk_info, usage_info = result
                    successful_transcriptions.append(chunk_info)
                    
                    # Aggregate ACTUAL costs from each chunk
                    total_whisper_cost += usage_info.get("cost_estimate", 0.0)
                    total_audio_minutes += usage_info.get("audio_duration_minutes", 0.0)
                    total_transcription_tokens += usage_info.get("output_tokens", 0)
            
            if failed_count > 0:
                logger.warning(f"{failed_count} chunks failed transcription")
            
            # ACCURATE usage summary with real costs
            usage_summary = {
                "transcription_tokens": total_transcription_tokens,
                "whisper_cost": round(total_whisper_cost, 6),
                "total_audio_minutes": round(total_audio_minutes, 2),
                "chunks_processed": len(chunks),
                "failed_chunks": failed_count,
                "successful_chunks": len(chunks) - failed_count,
                "pricing_verification": f"${total_whisper_cost:.6f} = {total_audio_minutes:.2f} min × $0.006/min"
            }
            
            logger.info(f"Total Whisper cost: ${total_whisper_cost:.6f} for {total_audio_minutes:.2f} minutes")
            logger.info(f"Transcription completed: {len(chunks) - failed_count}/{len(chunks)} successful")
            
            return successful_transcriptions, usage_summary
            
        except Exception as e:
            logger.error(f"Batch transcription failed: {e}")
            raise Exception(f"Transcription process failed: {str(e)}")
    
    def _transcribe_single_chunk(self, chunk: Dict) -> Tuple[ChunkInfo, Dict]:
        try:        
            client = openai.OpenAI(api_key=self.openai_service.client.api_key)
            
            # Get ACTUAL audio duration for this chunk
            probe = ffmpeg.probe(chunk['path'])
            actual_duration_seconds = float(probe['streams'][0]['duration'])
            actual_duration_minutes = actual_duration_seconds / 60.0
            
            with open(chunk['path'], "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )

            transcript_text = transcript if isinstance(transcript, str) else str(transcript)
            
            # ACCURATE cost calculation for this chunk
            actual_whisper_cost = actual_duration_minutes * 0.006
            estimated_tokens = max(1, len(transcript_text) // 4)
            
            usage_info = {
                "output_tokens": estimated_tokens,
                "audio_duration_seconds": actual_duration_seconds,
                "audio_duration_minutes": actual_duration_minutes,
                "cost_estimate": actual_whisper_cost,
                "chunk_id": chunk['chunk_id']
            }
            
            chunk_info = ChunkInfo(
                chunk_id=chunk['chunk_id'],
                start_time=chunk['start_time'],
                end_time=chunk['end_time'],
                duration=chunk['duration'],
                transcript=transcript_text.strip(),
                confidence=1.0
            )
        
            logger.debug(f"Chunk {chunk['chunk_id']}: {actual_duration_minutes:.2f} min = ${actual_whisper_cost:.6f}")
            return chunk_info, usage_info
            
        except Exception as e:
            logger.error(f"Single chunk transcription failed for chunk {chunk['chunk_id']}: {e}")
            raise e

    # ===== MISSING METHOD: combine_transcripts =====
    def combine_transcripts(self, transcriptions: List[ChunkInfo]) -> str:
        """Combine all chunk transcripts into a single text"""
        try:
            logger.info(f"Combining {len(transcriptions)} transcripts")
            
            # Validate input
            if not transcriptions:
                logger.warning("No transcriptions to combine")
                return ""
            

            if hasattr(transcriptions[0], 'chunk_id'):
                logger.debug(f"First transcription chunk_id: {transcriptions[0].chunk_id}")
            
            # Sort by chunk_id to ensure correct order
            try:
                sorted_transcriptions = sorted(transcriptions, key=lambda x: x.chunk_id)
            except AttributeError as e:
                logger.error(f"Transcription objects missing chunk_id attribute: {e}")
                raise Exception(f"Invalid transcription object structure: {str(e)}")
            
            # Combine transcripts with timestamps
            combined_parts = []
            for trans in sorted_transcriptions:
                try:
                    if trans.transcript and trans.transcript != "[Transcription failed]":
                        # Format timestamp (MM:SS)
                        start_minutes = int(trans.start_time // 60)
                        start_seconds = int(trans.start_time % 60)
                        
                        timestamp = f"[{start_minutes:02d}:{start_seconds:02d}]"
                        combined_parts.append(f"{timestamp} {trans.transcript}")
                except AttributeError as e:
                    continue
            
            if not combined_parts:
                return "[No valid transcriptions available]"
            
            combined_transcript = "\n\n".join(combined_parts)

            return combined_transcript
            
        except Exception as e:
            logger.error(f"Failed to combine transcripts: {e}")
            logger.error(f"Transcriptions input type: {type(transcriptions)}")
            if transcriptions:
                logger.error(f"First item type: {type(transcriptions[0])}")
                logger.error(f"First item content: {transcriptions[0]}")
            raise Exception(f"Transcript combination failed: {str(e)}")

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        return {"message": "Stats available"}
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        pass