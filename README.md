# =============================================================================

# File: README.md

# =============================================================================

# File Processing Pipeline API

AI-powered video processing service with transcription and summarization capabilities.

## Features

- **Video to Text**: Extract audio from video files and transcribe using OpenAI Whisper
- **AI Summarization**: Generate intelligent summaries using Gemini 1.5 Flash or GPT-3.5-turbo
- **Chunk Processing**: Efficient processing of large files with 90-second chunks and overlap
- **Multiple Input Methods**: Upload files directly or process from URLs
- **Clean Architecture**: Modular, maintainable codebase with proper error handling
- **Docker Ready**: Containerized deployment with health checks

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Run with Docker

```bash
# Build and start the service
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Process video file
curl -X POST "http://localhost:8000/api/v1/video/process" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-video.mp4"

# Process video from URL
curl -X POST "http://localhost:8000/api/v1/video/process-url" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://example.com/video.mp4"}'
```

## API Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

| Environment Variable | Default | Description                      |
| -------------------- | ------- | -------------------------------- |
| `API_KEY`            | -       | Your API authentication key      |
| `OPENAI_API_KEY`     | -       | OpenAI API key for Whisper & GPT |
| `GEMINI_API_KEY`     | -       | Google Gemini API key            |
| `CHUNK_DURATION`     | 90      | Audio chunk duration (seconds)   |
| `CHUNK_OVERLAP`      | 15      | Chunk overlap (seconds)          |
| `MAX_FILE_SIZE`      | 100     | Maximum file size (MB)           |
| `SUMMARIZER_SERVICE` | gemini  | AI service (gemini/openai)       |

## Supported Formats

**Video**: MP4, AVI, MOV, MKV, WebM, FLV, WMV

## Architecture

```
Client Request
    ↓
FastAPI (Authentication & Routing)
    ↓
Video Processor (Core Pipeline)
    ↓
Audio Extractor (FFmpeg)
    ↓
Audio Chunker (90s chunks + 15s overlap)
    ↓
Transcriber (OpenAI Whisper - Batch processing)
    ↓
Summarizer (Gemini 1.5 Flash / GPT-3.5-turbo)
    ↓
Response (Transcript + Summary + Metadata)
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Project Structure

```
file_processing_pipeline/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Business logic
│   ├── services/     # External service integrations
│   └── utils/        # Utilities & helpers
├── storage/          # Temporary file storage
└── logs/            # Application logs
```

## Performance Notes

- **Memory Usage**: ~2-4GB during processing
- **Processing Time**: ~2-3x video duration
- **Concurrent Limit**: 3 simultaneous transcriptions
- **File Size Limit**: 100MB (configurable)

## Monitoring

- **Health Check**: `GET /health`
- **Logs**: Available in `/logs` directory
- **Metrics**: Processing time and success rates logged

## Security

- API Key authentication required
- File validation and size limits
- Temporary file cleanup
- Non-root container execution

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Ensure FFmpeg is installed in container
2. **API Key errors**: Check X-API-Key header format
3. **Memory issues**: Reduce chunk size or limit concurrent processing
4. **Transcription failures**: Verify OpenAI API key and quota

### Logs

```bash
# View container logs
docker-compose logs -f file-processor

# View application logs
tail -f logs/app.log
```

## License

MIT License - See LICENSE file for details. dispatch(self, request: Request, call_next): # Skip authentication for docs and health endpoints
if request.url.path in ["/docs", "/openapi.json", "/redoc", "/health"]:
return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            logger.warning(f"Missing API key for {request.url.path}")
            raise HTTPException(
                status_code=401,
                detail="API Key required. Provide X-API-Key header."
            )

        if api_key != settings.API_KEY:
            logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
            raise HTTPException(
                status_code=401,
                detail="Invalid API Key"
            )

        response = await call_next(request)
        return response

# =============================================================================

# File: app/utils/response_models.py

# =============================================================================

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChunkInfo(BaseModel):
chunk_id: int
start_time: float
end_time: float
duration: float
transcript: str
confidence: Optional[float] = None

class ProcessingResponse(BaseModel):
success: bool
message: str
transcript: Optional[str] = None
summary: Optional[str] = None
chunks: Optional[List[ChunkInfo]] = None
processing_stats: Optional[dict] = None
timestamp: datetime = datetime.now()
error_details: Optional[str] = None

class HealthResponse(BaseModel):
status: str
service: str
version: str
timestamp: datetime = datetime.now()

class ErrorResponse(BaseModel):
success: bool = False
error: str
details: Optional[str] = None
timestamp: datetime = datetime.now()
