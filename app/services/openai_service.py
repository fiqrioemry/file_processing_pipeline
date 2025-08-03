
# app/services/openai_service.py
import openai
import ffmpeg
from typing import Tuple, Dict
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def transcribe_audio(self, audio_file_path: str) -> Tuple[str, Dict]:
        try:
            with open(audio_file_path, "rb") as audio_file:
                probe = ffmpeg.probe(audio_file_path)
                actual_duration_seconds = float(probe['streams'][0]['duration'])
                actual_duration_minutes = actual_duration_seconds / 60.0
                
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
                
                # CORRECT WHISPER PRICING: $0.006 per minute
                actual_whisper_cost = actual_duration_minutes * 0.006
                
                # Estimate output tokens for tracking (not for cost calculation)
                estimated_tokens = len(transcript) // 4
                
                usage_info = {
                    "input_tokens": 0,  # Audio input, not text tokens
                    "output_tokens": estimated_tokens,
                    "total_tokens": estimated_tokens,
                    "audio_duration_seconds": round(actual_duration_seconds, 2),
                    "audio_duration_minutes": round(actual_duration_minutes, 2),
                    "cost_estimate": round(actual_whisper_cost, 6),
                    "pricing_model": "whisper_per_minute",
                    "service_used": "openai_whisper"
                }
                
                logger.info(f"Whisper transcription: {actual_duration_minutes:.2f} min @ $0.006/min = ${actual_whisper_cost:.6f}")
                
                return transcript, usage_info
                
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def generate_summary_with_usage(self, text: str) -> Tuple[str, Dict]:
        prompt = """Anda adalah seorang ahli dalam membuat ringkasan yang komprehensif dan terstruktur dengan baik.

            Buatlah ringkasan dari transkrip berikut dengan format:

            ## Topik Utama
            [Tuliskan topik utama yang dibahas]

            ## Poin-Poin Kunci
            - [Poin penting 1]
            - [Poin penting 2]
            - [Poin penting 3]

            ## Detail dan Insight
            [Jelaskan detail penting dan wawasan yang dapat diambil]

            ## Kesimpulan
            [Rangkum kesimpulan utama]

            Gunakan bahasa Indonesia yang jelas dan mudah dipahami."""
                    
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Transkrip:\n\n{text}"}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            usage = response.usage
            
            # TOKEN PRICING
            input_cost = (usage.prompt_tokens / 1000) * 0.0005   # $0.0005 per 1K input tokens
            output_cost = (usage.completion_tokens / 1000) * 0.0015  # $0.0015 per 1K output tokens
            total_cost = input_cost + output_cost
            
            usage_info = {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
                "cost_estimate": round(total_cost, 6),
                "pricing_model": "gpt35_turbo_updated",
                "service_used": "openai"
            }
            
            logger.info(f"GPT-3.5-turbo: {usage.prompt_tokens} input + {usage.completion_tokens} output = ${total_cost:.6f}")
            
            return summary, usage_info
            
        except Exception as e:
            raise Exception(f"OpenAI summary failed: {str(e)}")