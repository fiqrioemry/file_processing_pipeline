import openai
from typing import Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio file using Whisper API"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
                
            logger.info(f"Successfully transcribed audio: {audio_file_path}")
            return transcript
            
        except Exception as e:
            logger.error(f"OpenAI transcription failed for {audio_file_path}: {e}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def generate_summary(self, text: str, max_tokens: int = 500) -> str:
        """Generate summary using GPT-3.5-turbo"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at creating concise, well-structured summaries. Create a summary that captures the key points, main topics, and important details from the transcript."
                    },
                    {
                        "role": "user", 
                        "content": f"Please create a detailed summary of this transcript:\n\n{text}"
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            logger.info("Successfully generated summary with OpenAI")
            return summary
            
        except Exception as e:
            logger.error(f"OpenAI summary generation failed: {e}")
            raise Exception(f"Summary generation failed: {str(e)}")