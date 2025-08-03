# app/utils/pdf_generator.py
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import  TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from app.config import settings

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self):
        self.storage_dir = Path(settings.STORAGE_DIR) / "reports"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2c3e50'),
            alignment=TA_CENTER
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=HexColor('#34495e'),
            leftIndent=0
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=HexColor('#7f8c8d'),
            leftIndent=10
        ))
        
        # Content style
        self.styles.add(ParagraphStyle(
            name='ContentText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=10,
            alignment=TA_JUSTIFY,
            leftIndent=10,
            rightIndent=10
        ))
        
        # Metadata style
        self.styles.add(ParagraphStyle(
            name='MetadataText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=HexColor('#95a5a6'),
            spaceAfter=6
        ))
    
    async def generate_summary_report(self, processing_result: Dict[str, Any], session_id: str) -> str:
        """Generate PDF report from processing result"""
        try:
            logger.info(f"Generating PDF report for session: {session_id}")
            
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_report_{session_id[:8]}_{timestamp}.pdf"
            file_path = self.storage_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build content
            story = []
            self._add_header(story, processing_result)
            self._add_video_info(story, processing_result)
            self._add_summary_section(story, processing_result)
            self._add_transcript_section(story, processing_result)
            self._add_chunks_section(story, processing_result)
            self._add_metadata_section(story, processing_result)
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF report generated successfully: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise Exception(f"PDF generation failed: {str(e)}")
    
    def _add_header(self, story: list, data: Dict[str, Any]):
        """Add document header"""
        # Main title
        video_title = data.get('meta', {}).get('video_info', {}).get('title', 'Video Analysis Report')
        title = Paragraph(f"📄 {video_title}", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Generation info
        generation_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        processing_method = data.get('meta', {}).get('processing_stats', {}).get('processing_method', 'unknown')
        
        info_text = f"Generated on {generation_date} | Processing Method: {processing_method.replace('_', ' ').title()}"
        info_para = Paragraph(info_text, self.styles['MetadataText'])
        story.append(info_para)
        story.append(Spacer(1, 20))
    
    def _add_video_info(self, story: list, data: Dict[str, Any]):
        """Add video information section"""
        video_info = data.get('meta', {}).get('video_info', {})
        processing_stats = data.get('meta', {}).get('processing_stats', {})
        
        if not video_info and not processing_stats:
            return
        
        # Section header
        header = Paragraph("📹 Video Information", self.styles['SectionHeader'])
        story.append(header)
        
        # Create info table
        info_data = []
        
        if video_info.get('title'):
            info_data.append(['Title:', video_info['title']])
        if video_info.get('uploader'):
            info_data.append(['Channel:', video_info['uploader']])
        if video_info.get('duration'):
            duration_mins = video_info['duration'] // 60
            duration_secs = video_info['duration'] % 60
            info_data.append(['Duration:', f"{duration_mins}:{duration_secs:02d}"])
        if processing_stats.get('source_url'):
            info_data.append(['Source URL:', processing_stats['source_url']])
        
        if info_data:
            table = Table(info_data, colWidths=[1.5*inch, 4.5*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(table)
        
        story.append(Spacer(1, 20))
    
    def _add_summary_section(self, story: list, data: Dict[str, Any]):
        """Add summary section"""
        summary = data.get('data', {}).get('summary', '')
        if not summary:
            return
        
        # Section header
        header = Paragraph("📋 Summary", self.styles['SectionHeader'])
        story.append(header)
        
        # Process summary content
        summary_parts = self._parse_summary_content(summary)
        
        for part_title, part_content in summary_parts:
            if part_title:
                subheader = Paragraph(part_title, self.styles['SubsectionHeader'])
                story.append(subheader)
            
            if part_content:
                content_para = Paragraph(part_content, self.styles['ContentText'])
                story.append(content_para)
        
        story.append(Spacer(1, 20))
    
    def _parse_summary_content(self, summary: str) -> list:
        """Parse summary content into sections"""
        import re
        
        # Split by markdown headers
        sections = re.split(r'##\s*(.+)', summary)
        
        parts = []
        current_title = None
        
        for i, section in enumerate(sections):
            if i == 0 and section.strip():
                # Content before first header
                parts.append((None, section.strip()))
            elif i % 2 == 1:
                # This is a header
                current_title = section.strip()
            else:
                # This is content
                if current_title:
                    parts.append((current_title, section.strip()))
                    current_title = None
        
        return parts
    
    def _add_transcript_section(self, story: list, data: Dict[str, Any]):
        """Add transcript section"""
        transcript = data.get('data', {}).get('transcript', '')
        if not transcript:
            return
        
        # Section header
        header = Paragraph("📝 Full Transcript", self.styles['SectionHeader'])
        story.append(header)
        
        # Limit transcript length for PDF
        max_transcript_length = 5000
        if len(transcript) > max_transcript_length:
            transcript = transcript[:max_transcript_length] + "\n\n[Transcript truncated for PDF. Full transcript available in original response.]"
        
        # Split into paragraphs for better formatting
        paragraphs = transcript.split('\n\n')
        for para in paragraphs:
            if para.strip():
                para_obj = Paragraph(para.strip(), self.styles['ContentText'])
                story.append(para_obj)
        
        story.append(Spacer(1, 20))
    
    def _add_chunks_section(self, story: list, data: Dict[str, Any]):
        """Add chunks information section"""
        chunks = data.get('data', {}).get('chunks', [])
        if not chunks:
            return
        
        # Section header
        header = Paragraph("🔗 Transcript Chunks", self.styles['SectionHeader'])
        story.append(header)
        
        # Create chunks table
        chunk_data = [['#', 'Time', 'Duration', 'Content Preview']]
        
        for chunk in chunks[:10]:  # Limit to first 10 chunks
            chunk_id = chunk.get('chunk_id', 0)
            start_time = chunk.get('start_time', 0)
            duration = chunk.get('duration', 0)
            transcript = chunk.get('transcript', '')
            
            # Format time
            start_mins = int(start_time // 60)
            start_secs = int(start_time % 60)
            time_str = f"{start_mins}:{start_secs:02d}"
            
            # Truncate content
            content_preview = transcript[:100] + "..." if len(transcript) > 100 else transcript
            
            chunk_data.append([
                str(chunk_id + 1),
                time_str,
                f"{duration:.1f}s",
                content_preview
            ])
        
        if len(chunks) > 10:
            chunk_data.append(['...', '...', '...', f'[{len(chunks) - 10} more chunks available]'])
        
        table = Table(chunk_data, colWidths=[0.5*inch, 0.8*inch, 0.8*inch, 3.9*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#bdc3c7')),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#ecf0f1')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
    
    def _add_metadata_section(self, story: list, data: Dict[str, Any]):
        """Add metadata and processing information"""
        meta = data.get('meta', {})
        if not meta:
            return
        
        # Section header
        header = Paragraph("📊 Processing Information", self.styles['SectionHeader'])
        story.append(header)
        
        # Token usage
        token_usage = meta.get('token_usage', {})
        if token_usage:
            token_header = Paragraph("Token Usage & Cost", self.styles['SubsectionHeader'])
            story.append(token_header)
            
            token_data = []
            if token_usage.get('input_tokens'):
                token_data.append(['Input Tokens:', f"{token_usage['input_tokens']:,}"])
            if token_usage.get('output_tokens'):
                token_data.append(['Output Tokens:', f"{token_usage['output_tokens']:,}"])
            if token_usage.get('total_tokens'):
                token_data.append(['Total Tokens:', f"{token_usage['total_tokens']:,}"])
            if token_usage.get('cost_estimate'):
                token_data.append(['Estimated Cost:', f"${token_usage['cost_estimate']:.6f}"])
            
            # Cost breakdown
            cost_breakdown = token_usage.get('cost_breakdown', {})
            if cost_breakdown:
                if cost_breakdown.get('whisper_cost', 0) > 0:
                    token_data.append(['Whisper Cost:', f"${cost_breakdown['whisper_cost']:.6f}"])
                if cost_breakdown.get('summary_cost', 0) > 0:
                    token_data.append(['Summary Cost:', f"${cost_breakdown['summary_cost']:.6f}"])
            
            if token_data:
                token_table = Table(token_data, colWidths=[2*inch, 2*inch])
                token_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(token_table)
        
        # Processing stats
        processing_stats = meta.get('processing_stats', {})
        if processing_stats:
            stats_header = Paragraph("Processing Statistics", self.styles['SubsectionHeader'])
            story.append(stats_header)
            
            stats_data = []
            if processing_stats.get('total_time_seconds'):
                stats_data.append(['Processing Time:', f"{processing_stats['total_time_seconds']:.2f} seconds"])
            if processing_stats.get('file_size_mb'):
                stats_data.append(['File Size:', f"{processing_stats['file_size_mb']:.2f} MB"])
            if processing_stats.get('session_id'):
                stats_data.append(['Session ID:', processing_stats['session_id'][:16] + "..."])
            
            if stats_data:
                stats_table = Table(stats_data, colWidths=[2*inch, 3*inch])
                stats_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(stats_table)
        
        # Optimization info
        optimization_info = meta.get('optimization_info', {})
        if optimization_info:
            opt_text = f"Method: {optimization_info.get('method_used', 'unknown').replace('_', ' ').title()}"
            if optimization_info.get('subtitle_source'):
                opt_text += f" | Subtitle Source: {optimization_info['subtitle_source'].title()}"
            if optimization_info.get('cost_saved'):
                opt_text += f" | {optimization_info['cost_saved']}"
            
            opt_para = Paragraph(opt_text, self.styles['MetadataText'])
            story.append(Spacer(1, 10))
            story.append(opt_para)
    
    def get_report_url(self, file_path: str) -> str:
        """Get accessible URL for the generated report"""
        filename = Path(file_path).name
        # Assuming you have a static file server setup
        return f"/storage/reports/{filename}"
    
    def cleanup_old_reports(self, max_age_hours: int = 24):
        """Clean up old PDF reports"""
        import time
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        try:
            for file_path in self.storage_dir.glob("*.pdf"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink(missing_ok=True)
                    logger.info(f"Cleaned old report: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning old reports: {e}")