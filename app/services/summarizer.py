# app/services/summarizer.py
from app.services.openai_service import OpenAIService
from app.services.gemini_service import GeminiService
from app.config import settings
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class SummarizerService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.gemini_service = GeminiService()
    
    async def summarize_with_usage(self, text: str, service: str = None) -> Tuple[str, Dict]:
        """Generate summary with usage statistics using fallback strategy"""
        
        primary_service = service or settings.SUMMARIZER_SERVICE
        fallback_service = "openai" if primary_service.lower() == "gemini" else "gemini"
        
        # Try primary service
        try:
            logger.info(f"Attempting summarization with {primary_service}")
            return await self._call_service(text, primary_service)
        except Exception as e:
            logger.warning(f"Primary service {primary_service} failed: {e}")
        
        # Try fallback service
        try:
            logger.info(f"Attempting summarization with fallback service {fallback_service}")
            return await self._call_service(text, fallback_service)
        except Exception as e:
            logger.error(f"Fallback service {fallback_service} failed: {e}")
        
        # If both fail, raise error
        raise Exception("All summarization services failed")
    
    async def _call_service(self, text: str, service: str) -> Tuple[str, Dict]:
        """Call specific summarization service"""
        service = service.lower()
        
        if service == "openai":
            return await self.openai_service.generate_summary_with_usage(text)
        elif service == "gemini":
            return await self.gemini_service.generate_summary_with_usage(text)
        else:
            raise ValueError(f"Unsupported service: {service}")

