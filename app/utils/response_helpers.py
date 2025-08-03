# app/utils/response_helpers.py
from fastapi import HTTPException

class VideoProcessingError(Exception):
    """Custom exception for video processing errors"""
    def __init__(self, message: str, details: str = None, status_code: int = 500):
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(self.message)

def raise_error(message: str, details: str = None, status_code: int = 500):
    """Raise HTTPException with consistent error format"""
    raise HTTPException(
        status_code=status_code,
        detail=f"{message}: {details}" if details else message
    )

def raise_validation_error(message: str, details: str = None):
    """Raise validation error (400)"""
    raise_error(message, details, 400)

def raise_not_found_error(message: str, details: str = None):
    """Raise not found error (404)"""
    raise_error(message, details, 404)

def raise_payload_too_large_error(message: str, details: str = None):
    """Raise payload too large error (413)"""
    raise_error(message, details, 413)

def raise_unprocessable_entity_error(message: str, details: str = None):
    """Raise unprocessable entity error (422)"""
    raise_error(message, details, 422)

def raise_internal_server_error(message: str, details: str = None):
    """Raise internal server error (500)"""
    raise_error(message, details, 500)