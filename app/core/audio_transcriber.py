# app/core/audio_transcriber.py
import logging
from faster_whisper import WhisperModel
from typing import List, Dict, Any, Tuple
from app.utils.response_models import ChunkInfo

logger = logging.getLogger(__name__)

class AudioTranscriber:
    """Local Whisper transcriber using faster-whisper"""
    
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size
        self._model = None
    
    def _get_model(self) -> WhisperModel:
        """Get or load the Whisper model (singleton pattern)"""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = WhisperModel(
                self.model_size,
                device="cpu", 
                compute_type="int8"
            )
        return self._model

    async def transcribe_file(
        self,
        file_path: str,
        include_timestamps: bool = True,
        confidence_threshold: float = -2.0
    ) -> Dict[str, Any]:
        """Transcribe single audio file and return structured results"""
        try:
            model = self._get_model()
            segments, info = model.transcribe(file_path, **self._get_transcribe_params())
            return self._process_results(segments, info, include_timestamps, confidence_threshold)
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def transcribe_chunks(self, chunks: List[Dict]) -> Tuple[List[ChunkInfo], Dict]:
        """Transcribe multiple chunks and return results with usage stats"""
        try:
            logger.info(f"Starting transcription of {len(chunks)} chunks")
            
            # Pre-load model once for all chunks
            model = self._get_model()
            
            transcription_results = []
            total_input_tokens = 0
            total_output_tokens = 0
            failed_count = 0
            
            for chunk in chunks:
                try:
                    chunk_info, usage_info = await self._transcribe_single_chunk(chunk)
                    transcription_results.append(chunk_info)
                    
                    total_input_tokens += usage_info.get("input_tokens", 0)
                    total_output_tokens += usage_info.get("output_tokens", 0)
                    
                except Exception as e:
                    logger.error(f"Chunk {chunk['chunk_id']} failed: {e}")
                    failed_count += 1
                    
                    failed_chunk = ChunkInfo(
                        chunk_id=chunk['chunk_id'],
                        start_time=chunk['start_time'],
                        end_time=chunk['end_time'],
                        duration=chunk['duration'],
                        transcript="[Transcription failed]",
                        confidence=0.0
                    )
                    transcription_results.append(failed_chunk)
            
            usage_summary = {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "failed_chunks": failed_count,
                "successful_chunks": len(chunks) - failed_count,
                "chunks_processed": len(chunks),
                "model_used": self.model_size
            }
            
            return transcription_results, usage_summary
            
        except Exception as e:
            raise Exception(f"Transcription process failed: {str(e)}")

    async def _transcribe_single_chunk(self, chunk: Dict) -> Tuple[ChunkInfo, Dict]:
        """Transcribe single chunk and return chunk info with usage stats"""
        try:
            model = self._get_model()  # Uses cached model
            segments, info = model.transcribe(chunk['path'], **self._get_transcribe_params())
            
            segments_list = list(segments)
            full_text_parts = []
            
            for segment in segments_list:
                text = segment.text.strip()
                if text:
                    full_text_parts.append(text)
            
            transcript_text = " ".join(full_text_parts)
            
            # Token estimates
            input_tokens = max(1, int(chunk['duration'] * 10))
            output_tokens = max(1, len(transcript_text) // 4)
            
            usage_info = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "audio_duration_seconds": chunk['duration'],
                "chunk_id": chunk['chunk_id']
            }
            
            chunk_info = ChunkInfo(
                chunk_id=chunk['chunk_id'],
                start_time=chunk['start_time'],
                end_time=chunk['end_time'],
                duration=chunk['duration'],
                transcript=transcript_text,
                confidence=1.0
            )
            
            return chunk_info, usage_info
            
        except Exception as e:
            logger.error(f"Single chunk transcription failed for chunk {chunk['chunk_id']}: {e}")
            raise e

    def combine_transcripts(self, transcriptions: List[ChunkInfo]) -> str:
        """Combine all chunk transcripts into a single text"""
        try:
            logger.info(f"Combining {len(transcriptions)} transcripts")
            
            if not transcriptions:
                return ""
            
            sorted_transcriptions = sorted(transcriptions, key=lambda x: x.chunk_id)
            
            combined_parts = []
            for trans in sorted_transcriptions:
                if trans.transcript and trans.transcript != "[Transcription failed]":
                    start_minutes = int(trans.start_time // 60)
                    start_seconds = int(trans.start_time % 60)
                    timestamp = f"[{start_minutes:02d}:{start_seconds:02d}]"
                    combined_parts.append(f"{timestamp} {trans.transcript}")
            
            return "\n\n".join(combined_parts) if combined_parts else "[No valid transcriptions available]"
            
        except Exception as e:
            logger.error(f"Failed to combine transcripts: {e}")
            raise Exception(f"Transcript combination failed: {str(e)}")
    
    def _get_transcribe_params(self) -> Dict[str, Any]:
        """Get optimized Whisper transcription parameters"""
        return {
            "beam_size": 5,
            "language": None,
            "condition_on_previous_text": False,
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "log_prob_threshold": -1.0,
            "no_speech_threshold": 0.6,
            "vad_filter": True,
            "vad_parameters": {
                "min_silence_duration_ms": 1000,
                "speech_pad_ms": 400
            }
        }
    
    def _process_results(
        self, 
        segments, 
        info, 
        include_timestamps: bool, 
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """Process transcription results for single file transcription"""
        segments_list = list(segments)
        logger.info(f"Processing {len(segments_list)} segments")
        
        processed_segments = []
        full_text_parts = []

        for segment in segments_list:
            confidence = getattr(segment, 'avg_logprob', None)
            
            if confidence is not None and confidence < confidence_threshold:
                continue
            
            text = segment.text.strip()
            if not text:
                continue
                
            segment_data = {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text,
                "confidence": round(confidence, 3) if confidence else None
            }
            
            if include_timestamps:
                processed_segments.append(segment_data)
            
            full_text_parts.append(text)
        
        return {
            "full_text": " ".join(full_text_parts),
            "language": getattr(info, 'language', 'unknown'),
            "language_confidence": round(getattr(info, 'language_probability', 0), 3),
            "segments": processed_segments,
            "duration": getattr(info, 'duration', 0),
            "model_used": self.model_size
        }