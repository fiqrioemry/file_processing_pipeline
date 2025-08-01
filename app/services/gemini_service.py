import google.generativeai as genai
from typing import Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def generate_summary(self, text: str) -> str:
        """Generate summary using Gemini 1.5 Flash"""
        try:
            prompt = f"""
            Please create a comprehensive and well-structured summary of the following transcript. 
            Include:
            - Main topics and key points
            - Important details and insights
            - Clear organization with sections if applicable
            
            Transcript:
            {text}
            
            Summary:
            """
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise Exception("Empty response from Gemini")
            
            logger.info("Successfully generated summary with Gemini")
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini summary generation failed: {e}")
            raise Exception(f"Summary generation failed: {str(e)}")
