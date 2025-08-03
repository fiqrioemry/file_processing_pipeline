# app/utils/storage_manager.py
import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import HTTPException
from fastapi.responses import FileResponse
import logging

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        self.storage_root = Path(settings.STORAGE_DIR)
        self.reports_dir = self.storage_root / "reports"
        self.temp_dir = self.storage_root / "temp"
        
        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_report_path(self, filename: str) -> Optional[Path]:
        """Get full path for a report file"""
        file_path = self.reports_dir / filename
        if file_path.exists() and file_path.is_file():
            return file_path
        return None
    
    def create_download_response(self, filename: str) -> FileResponse:
        """Create file download response"""
        file_path = self.get_report_path(filename)
        if not file_path:
            raise HTTPException(status_code=404, detail="Report file not found")
        
        return FileResponse(
            path=str(file_path),
            media_type='application/pdf',
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics"""
        try:
            reports_count = len(list(self.reports_dir.glob("*.pdf")))
            
            # Calculate total size
            total_size = 0
            for file_path in self.reports_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return {
                "reports_count": reports_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_path": str(self.reports_dir)
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}