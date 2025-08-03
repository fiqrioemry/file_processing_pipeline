import logging
from app.config import settings
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/","/docs", "/openapi.json", "/redoc", "/health", "favicon.ico"]:
            return await call_next(request)
        
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            raise HTTPException(
                status_code=401, 
                detail="API Key required. Provide X-API-Key header."
            )
        
        if api_key != settings.API_KEY:
            raise HTTPException(
                status_code=401, 
                detail="Invalid API Key"
            )
        
        response = await call_next(request)
        return response
