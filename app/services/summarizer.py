from app.services.openai_service import OpenAIService
from app.services.gemini_service import GeminiService
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class SummarizerService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.gemini_service = GeminiService()
    
    async def summarize(self, text: str, service: str = None) -> str:
        """Generate summary using specified AI service"""
        if not service:
            service = settings.SUMMARIZER_SERVICE
        
        try:
            if service.lower() == "openai":
                return await self.openai_service.generate_summary(text)
            elif service.lower() == "gemini":
                return await self.gemini_service.generate_summary(text)
            else:
                logger.warning(f"Unknown service: {service}, defaulting to {settings.SUMMARIZER_SERVICE}")
                return await self.summarize(text, settings.SUMMARIZER_SERVICE)
                
        except Exception as e:
            logger.error(f"Summarization failed with {service}: {e}")
            # Try fallback service
            fallback_service = "openai" if service.lower() == "gemini" else "gemini"
            logger.info(f"Attempting fallback to {fallback_service}")
            
            try:
                return await self.summarize(text, fallback_service)
            except Exception as fallback_error:
                logger.error(f"Fallback summarization also failed: {fallback_error}")
                raise Exception(f"All summarization services failed. Last error: {str(fallback_error)}")

