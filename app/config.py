from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Authentication
    API_KEY: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    
    # Processing Configuration
    CHUNK_DURATION: int = 90  # seconds
    CHUNK_OVERLAP: int = 15   # seconds
    MAX_FILE_SIZE: int = 100  # MB
    
    # Storage Configuration
    TEMP_DIR: str = "./storage/temp"
    
    # AI Service Selection
    SUMMARIZER_SERVICE: str = "gemini"  # "gemini" or "openai"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Initialize settings
settings = Settings()

# Ensure temp directories exist
os.makedirs(f"{settings.TEMP_DIR}/videos", exist_ok=True)
os.makedirs(f"{settings.TEMP_DIR}/audio", exist_ok=True)
os.makedirs(f"{settings.TEMP_DIR}/chunks", exist_ok=True)