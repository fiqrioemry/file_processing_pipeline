# =====================================================================================
# FILE: app/core/audio_processor.py (UPDATED with subtitle logic)
# =====================================================================================
import time
import logging
from typing import Dict, Any
from fastapi import UploadFile

from app.core.chunker import AudioChunker
from app.core.transcriber import Transcriber
from app.services.summarizer import SummarizerService
from app.services.audio_service import AudioService
from app.services.subtitle_service import SubtitleService
from app.utils.temp_manager import TempManager
from app.utils.file_handler import FileHandler
from app.utils.response_models import StandardResponse
from app.utils.response_helpers import (
    raise_validation_error, 
    raise_payload_too_large_error,
    raise_internal_server_error
)
from app.config import settings

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.chunker = AudioChunker()
        self.transcriber = Transcriber()
        self.summarizer = SummarizerService()
        self.audio_service = AudioService()
        self.subtitle_service = SubtitleService()  # NEW
        self.temp_manager = TempManager()
        self.file_handler = FileHandler()

    async def process_audio_file(self, audio_file: UploadFile, summarizer_service: str = None) -> StandardResponse:
        """Process uploaded audio file"""
        session_id = self.temp_manager.generate_session_id()
        start_time = time.time()
        
        try:
            logger.info(f"Starting audio file processing for session: {session_id}")
            
            # Validate audio file
            if not self.file_handler.validate_audio_file(audio_file.filename):
                raise_validation_error(
                    "Unsupported audio format",
                    f"Supported formats: {', '.join(self.file_handler.SUPPORTED_AUDIO_FORMATS)}"
                )
            
            # Save uploaded file
            audio_path = await self.temp_manager.save_uploaded_file(audio_file, session_id)
            
            # Validate file size
            if not self.file_handler.validate_file_size(audio_path, settings.MAX_FILE_SIZE):
                actual_size = self.file_handler.get_file_size_mb(audio_path)
                raise_payload_too_large_error(
                    f"File too large. Max size: {settings.MAX_FILE_SIZE}MB",
                    f"Actual: {actual_size:.1f}MB"
                )
            
            # Process audio pipeline
            result_data, token_usage = await self._process_audio_pipeline(audio_path, session_id, summarizer_service)
            
            # Create processing stats
            processing_stats = {
                "total_time_seconds": round(time.time() - start_time, 2),
                "file_size_mb": round(self.file_handler.get_file_size_mb(audio_path), 2),
                "session_id": session_id
            }
            
            logger.info(f"Successfully processed audio file: {audio_file.filename}")
            
            return StandardResponse(
                success=True,
                message="Audio processing completed successfully",
                data=result_data,
                meta={
                    "token_usage": token_usage,
                    "processing_stats": processing_stats
                }
            )

        except Exception as e:
            logger.error(f"Audio processing failed for session {session_id}: {e}")
            if hasattr(e, 'status_code'):  # HTTPException
                raise
            raise_internal_server_error("Audio processing failed", str(e))

        finally:
            self.temp_manager.cleanup_session(session_id)

    async def process_audio_from_url(self, video_url: str, summarizer_service: str = None) -> StandardResponse:
        """Process audio extracted directly from video URL with subtitle optimization"""
        session_id = self.temp_manager.generate_session_id()
        start_time = time.time()
        
        try:
            logger.info(f"Starting URL processing for session: {session_id}")
            
            # Validate URL format
            if not video_url.startswith(('http://', 'https://')):
                raise_validation_error(
                    "Invalid video URL",
                    "URL must start with http:// or https://"
                )
            
            # ====================================================================
            # STEP 1: CHECK FOR SUBTITLES FIRST (NEW OPTIMIZATION)
            # ====================================================================
            logger.info("Checking for existing subtitles...")
            subtitle_result = await self.subtitle_service.check_and_extract_subtitles(video_url)
            
            if subtitle_result.get("has_subtitles"):
                logger.info("🎯 FOUND SUBTITLES! Using subtitle-only processing (cost-optimized)")
                return await self._process_subtitle_only(
                    subtitle_result, video_url, session_id, start_time, summarizer_service
                )
            
            # ====================================================================
            # STEP 2: FALLBACK TO AUDIO PROCESSING (if no subtitles)
            # ====================================================================
            logger.info("⚠️ No subtitles found. Falling back to audio transcription...")
            
            # Validate video URL and constraints
            video_info = await self.audio_service.validate_video_url(video_url)
            
            # Download audio directly from URL
            audio_path = await self.temp_manager.download_audio_from_url(video_url, session_id)
            
            # Final file size check after download
            if not self.file_handler.validate_file_size(audio_path, settings.MAX_FILE_SIZE):
                actual_size = self.file_handler.get_file_size_mb(audio_path)
                raise_payload_too_large_error(
                    f"Downloaded audio file too large. Max size: {settings.MAX_FILE_SIZE}MB",
                    f"Actual: {actual_size:.1f}MB"
                )
            
            # Process audio pipeline
            result_data, token_usage = await self._process_audio_pipeline(audio_path, session_id, summarizer_service)
            
            # Create processing stats with video info
            processing_stats = {
                "total_time_seconds": round(time.time() - start_time, 2),
                "file_size_mb": round(self.file_handler.get_file_size_mb(audio_path), 2),
                "video_duration": video_info.get('duration'),
                "video_title": video_info.get('title', 'Unknown'),
                "source_url": video_url,
                "session_id": session_id,
                "processing_method": "audio_transcription"
            }
            
            logger.info(f"Successfully processed audio from URL: {video_url}")
            
            return StandardResponse(
                success=True,
                message="Video audio processing completed successfully",
                data=result_data,
                meta={
                    "token_usage": token_usage,
                    "processing_stats": processing_stats,
                    "video_info": {
                        "title": video_info.get('title'),
                        "uploader": video_info.get('uploader'),
                        "duration": video_info.get('duration')
                    }
                }
            )

        except Exception as e:
            logger.error(f"URL processing failed for session {session_id}: {e}")
            if hasattr(e, 'status_code'):  # HTTPException
                raise
            raise_internal_server_error("Video processing failed", str(e))

        finally:
            self.temp_manager.cleanup_session(session_id)

    async def _process_subtitle_only(self, subtitle_result: Dict, video_url: str, session_id: str, start_time: float, summarizer_service: str = None) -> StandardResponse:
        """Process video using only subtitles (cost-optimized path)"""
        try:
            subtitle_text = subtitle_result["subtitle_text"]
            video_info = subtitle_result["video_info"]
            subtitle_source = subtitle_result["subtitle_source"]
            
            logger.info(f"Processing {len(subtitle_text)} characters of subtitle text")
            
            # Validate subtitle content length
            if len(subtitle_text.strip()) < 50:
                logger.warning("Subtitle content too short, falling back to audio processing")
                raise Exception("Subtitle content insufficient")
            
            # Generate summary directly from subtitle text
            summary, summary_usage = await self.summarizer.summarize_with_usage(subtitle_text, summarizer_service)
            
            # No whisper cost since we're using subtitles
            whisper_cost = 0.0
            summary_cost = summary_usage.get("cost_estimate", 0.0)
            total_cost = summary_cost
            
            # Create result data
            result_data = {
                "transcript": subtitle_text,
                "summary": summary,
                "chunks": []  # No chunks since we used subtitles
            }
            
            # Token usage (only from summarizer)
            token_usage = {
                "input_tokens": summary_usage.get("input_tokens", 0),
                "output_tokens": summary_usage.get("output_tokens", 0),
                "total_tokens": summary_usage.get("total_tokens", 0),
                "cost_estimate": round(total_cost, 6),
                "cost_breakdown": {
                    "whisper_cost": 0.0,  # Saved!
                    "summary_cost": summary_cost
                },
                "cost_savings": "Used existing subtitles - no transcription cost!"
            }
            
            # Processing stats
            processing_stats = {
                "total_time_seconds": round(time.time() - start_time, 2),
                "file_size_mb": 0.0,  # No file downloaded
                "video_duration": video_info.get('duration'),
                "video_title": video_info.get('title', 'Unknown'),
                "source_url": video_url,
                "session_id": session_id,
                "processing_method": "subtitle_extraction",
                "subtitle_source": subtitle_source
            }
            
            logger.info(f"💰 COST SAVINGS: Using subtitles saved Whisper transcription cost!")
            logger.info(f"Total cost: ${total_cost:.6f} (Summary only)")
            
            return StandardResponse(
                success=True,
                message="Video processing completed using existing subtitles (cost-optimized)",
                data=result_data,
                meta={
                    "token_usage": token_usage,
                    "processing_stats": processing_stats,
                    "video_info": {
                        "title": video_info.get('title'),
                        "uploader": video_info.get('uploader'),
                        "duration": video_info.get('duration')
                    },
                    "optimization_info": {
                        "method_used": "subtitle_extraction",
                        "subtitle_source": subtitle_source,
                        "cost_saved": "Whisper transcription cost avoided"
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Subtitle-only processing failed: {e}")
            # Don't raise error - let it fall back to audio processing
            raise Exception("Subtitle processing failed, falling back to audio")


    async def _process_audio_pipeline(self, audio_path: str, session_id: str, summarizer_service: str = None) -> tuple:
        """Core audio processing pipeline"""
        try:
            # Create audio chunks
            chunks = await self.chunker.create_chunks(audio_path, session_id)
            if not chunks:
                raise_internal_server_error("No audio chunks created")

            # Transcribe chunks
            transcriptions, transcription_usage = await self.transcriber.transcribe_chunks(chunks)
            full_transcript = self.transcriber.combine_transcripts(transcriptions)
            if not full_transcript.strip():
                raise_internal_server_error("No transcript generated")

            # Generate summary
            summary, summary_usage = await self.summarizer.summarize_with_usage(full_transcript, summarizer_service)

            # Calculate total costs
            whisper_cost = transcription_usage.get("whisper_cost", 0.0)
            summary_cost = summary_usage.get("cost_estimate", 0.0)
            total_cost = whisper_cost + summary_cost

            # Prepare chunks data for response
            chunks_data = [
                {
                    "chunk_id": t.chunk_id,
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "duration": t.duration,
                    "transcript": t.transcript,
                    "confidence": t.confidence
                } for t in transcriptions
            ]

            # Return data and usage info
            result_data = {
                "transcript": full_transcript,
                "summary": summary,
                "chunks": chunks_data
            }
            
            token_usage = {
                "input_tokens": summary_usage.get("input_tokens", 0),
                "output_tokens": (
                    transcription_usage.get("transcription_tokens", 0) + 
                    summary_usage.get("output_tokens", 0)
                ),
                "total_tokens": (
                    transcription_usage.get("transcription_tokens", 0) + 
                    summary_usage.get("total_tokens", 0)
                ),
                "cost_estimate": round(total_cost, 6),
                "cost_breakdown": {
                    "whisper_cost": whisper_cost,
                    "summary_cost": summary_cost
                }
            }

            logger.info(f"Total processing cost: Whisper=${whisper_cost:.6f} + Summary=${summary_cost:.6f} = ${total_cost:.6f}")

            return result_data, token_usage

        except Exception as e:
            logger.error(f"Audio processing pipeline failed: {e}")
            if hasattr(e, 'status_code'):  # HTTPException
                raise
            raise_internal_server_error("Audio processing pipeline failed", str(e))