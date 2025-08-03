# app/services/subtitle_service.py
import yt_dlp
import logging
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
from app.utils.response_helpers import raise_unprocessable_entity_error

logger = logging.getLogger(__name__)

class SubtitleService:
    def __init__(self):
        # Default fallback order
        self.fallback_languages = ['auto', 'en', 'id']
        
    async def check_and_extract_subtitles(self, video_url: str) -> Dict[str, Any]:
        """Check if video has subtitles and extract them if available"""
        try:
            logger.info(f"Checking for subtitles in video: {video_url}")
            
            # Get video info and subtitle URLs
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'writesubtitles': False,
                'listsubtitles': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                logger.info(f"Available subtitles: {list(subtitles.keys())}")
                logger.info(f"Available auto captions: {list(automatic_captions.keys())}")
                
                # Detect video language and set priority
                video_language = self._detect_video_language(info, subtitles, automatic_captions)
                logger.info(f"Detected video language: {video_language}")
                
                # Extract subtitle content with language-aware priority
                subtitle_text = self._extract_subtitle_content_with_language_priority(
                    subtitles, automatic_captions, video_language
                )
                
                if subtitle_text:
                    logger.info(f"Successfully extracted subtitles: {len(subtitle_text)} characters")

                    return {
                        "has_subtitles": True,
                        "subtitle_text": subtitle_text,
                        "subtitle_source": self._determine_subtitle_source(subtitles, automatic_captions),
                        "detected_language": video_language,
                        "video_info": {
                            "title": info.get('title', 'Unknown'),
                            "duration": info.get('duration'),
                            "uploader": info.get('uploader')
                        }
                    }
                else:
                    logger.info("No usable subtitles found")
                    return {"has_subtitles": False}
                    
        except Exception as e:
            logger.error(f"Subtitle extraction failed: {e}")
            return {"has_subtitles": False, "error": str(e)}
    
    def _detect_video_language(self, video_info: Dict, subtitles: Dict, automatic_captions: Dict) -> str:
        """Detect the primary language of the video"""
        
        # Method 1: Check video metadata
        video_language = video_info.get('language')
        if video_language:
            logger.info(f"Video language from metadata: {video_language}")
            return video_language
        
        # Method 2: Check uploader location/country
        uploader_country = video_info.get('uploader_country')
        if uploader_country:
            country_to_lang = {
                'ID': 'id', 'Indonesia': 'id',
                'US': 'en', 'United States': 'en',
                'GB': 'en', 'United Kingdom': 'en',
                'MY': 'ms', 'Malaysia': 'ms',
                'SG': 'en', 'Singapore': 'en'
            }
            if uploader_country in country_to_lang:
                detected_lang = country_to_lang[uploader_country]
                logger.info(f"Language detected from uploader country {uploader_country}: {detected_lang}")
                return detected_lang
        
        # Method 3: Analyze available subtitle languages
        all_subtitle_langs = set(subtitles.keys()) | set(automatic_captions.keys())
        
        # Prioritize based on what's most commonly available
        lang_priority = ['id', 'en', 'auto']
        for lang in lang_priority:
            if lang in all_subtitle_langs:
                logger.info(f"Language detected from available subtitles: {lang}")
                return lang
        
        # Method 4: Check title for language hints
        title = video_info.get('title', '').lower()
        
        # Indonesian indicators
        indonesian_words = ['cara', 'bagaimana', 'tutorial', 'tips', 'belajar', 'indonesia', 'indo', 'yang', 'dan', 'untuk']
        if any(word in title for word in indonesian_words):
            logger.info("Indonesian language detected from title keywords")
            return 'id'
        
        # Default fallback
        logger.info("Could not detect language, using fallback")
        return 'auto'
    
    def _extract_subtitle_content_with_language_priority(
        self, subtitles: Dict, automatic_captions: Dict, detected_language: str
    ) -> Optional[str]:
        """Extract subtitle content with language-aware priority"""
        
        # Create priority list based on detected language
        if detected_language == 'id':
            priority_languages = ['id', 'auto', 'en']
        elif detected_language == 'en':
            priority_languages = ['en', 'auto', 'id']
        else:
            priority_languages = ['auto', 'id', 'en']
        
        logger.info(f"Language priority order: {priority_languages}")
        
        # Build subtitle sources with new priority
        subtitle_sources = []
        
        # Manual subtitles first (highest quality)
        for lang in priority_languages:
            if lang in subtitles and subtitles[lang]:
                subtitle_sources.append(('manual', lang, subtitles[lang]))
                logger.info(f"Found manual subtitles for: {lang}")
        
        # Auto-generated subtitles second
        for lang in priority_languages:
            if lang in automatic_captions and automatic_captions[lang]:
                subtitle_sources.append(('auto', lang, automatic_captions[lang]))
                logger.info(f"Found auto captions for: {lang}")
        
        if not subtitle_sources:
            logger.info("No subtitle sources found")
            return None
        
        # Try each source in priority order
        for source_type, lang, subtitle_list in subtitle_sources:
            logger.info(f"🔍 Trying {source_type} subtitles for {lang}...")
            
            for i, subtitle_format in enumerate(subtitle_list):
                format_ext = subtitle_format.get('ext', 'unknown')
                subtitle_url = subtitle_format.get('url')
                
                if format_ext in ['vtt', 'srv3', 'srv2', 'srv1'] and subtitle_url:
                    try:
                        logger.info(f"  ⬇️ Downloading {format_ext} format...")
                        raw_content = self._download_subtitle_from_url(subtitle_url)
                        
                        if raw_content:
                            cleaned_content = self._clean_subtitle_text_debug(raw_content)
                            
                            if cleaned_content and len(cleaned_content.strip()) > 100:
                                logger.info(f"  ✅ Successfully got subtitles in {lang}")
                                logger.info(f"  📝 Content length: {len(cleaned_content)} characters")
                                logger.info(f"  📝 Preview: {cleaned_content[:200]}...")
                                return cleaned_content
                            else:
                                logger.warning(f"Content too short after cleaning: {len(cleaned_content) if cleaned_content else 0} chars")
                        else:
                            logger.warning(f"Failed to download content")
                            
                    except Exception as e:
                        logger.warning(f"  💥 Error with {format_ext}: {e}")
                        continue
        
        return None
    
    def _download_subtitle_from_url(self, subtitle_url: str) -> Optional[str]:
        """Download subtitle content with better error handling"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/vtt,text/plain,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        }
        
        try:
            request = urllib.request.Request(subtitle_url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 200:
                    content = response.read()
                    
                    # Try different encodings
                    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                        try:
                            text_content = content.decode(encoding)
                            logger.debug(f"Successfully decoded with {encoding}")
                            return text_content
                        except UnicodeDecodeError:
                            continue
                    
                    logger.error("Failed to decode content with any encoding")
                    return None
                else:
                    logger.warning(f"HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def _clean_subtitle_text_debug(self, subtitle_content: str) -> str:
        """Clean subtitle content with debugging"""
        import re
        
        logger.info(f"🧹 Starting subtitle cleaning process...")
        
        try:
            lines = subtitle_content.split('\n')
            logger.info(f"📄 Total lines to process: {len(lines)}")
            
            text_lines = []
            skipped_lines = 0
            
            for i, line in enumerate(lines):
                original_line = line
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip WebVTT headers
                if any(line.startswith(header) for header in ['WEBVTT', 'NOTE', 'Kind:', 'Language:']):
                    skipped_lines += 1
                    continue
                
                # Skip timestamp lines
                if '-->' in line:
                    skipped_lines += 1
                    continue
                
                # Skip pure numbers (sequence numbers)
                if line.isdigit():
                    skipped_lines += 1
                    continue
                
                # Skip timestamp patterns
                if re.match(r'^\d{2}:\d{2}:\d{2}[.,]\d{3}', line):
                    skipped_lines += 1
                    continue
                
                # Clean the line but preserve content
                cleaned_line = line
                
                # Remove HTML/XML tags but keep content
                cleaned_line = re.sub(r'<[^>]*>', '', cleaned_line)
                
                # Remove WebVTT cue settings
                cleaned_line = re.sub(r'\{[^}]*\}', '', cleaned_line)
                
                # Remove sound effects but keep speech
                cleaned_line = re.sub(r'\[(?:Music|Applause|Laughter|Sound effects?)\]', '', cleaned_line, flags=re.IGNORECASE)
                
                # Remove obvious speaker tags like "Speaker 1:", "John:" but be careful
                cleaned_line = re.sub(r'^[A-Z][a-z]*\s*\d*:\s*', '', cleaned_line)
                
                # Clean up multiple spaces
                cleaned_line = re.sub(r'\s+', ' ', cleaned_line).strip()
                
                # Only keep lines with substantial content
                if cleaned_line and len(cleaned_line) > 1 and not cleaned_line.isdigit():
                    text_lines.append(cleaned_line)
                    if i < 10:  # Debug first 10 lines
                        logger.debug(f"Line {i+1}: '{original_line.strip()}' -> '{cleaned_line}'")
                else:
                    skipped_lines += 1
            
            logger.info(f"📊 Processing stats: {len(text_lines)} kept, {skipped_lines} skipped")
            
            # Join and final cleanup
            full_text = ' '.join(text_lines)
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            logger.info(f"🎯 Final text length: {len(full_text)} characters")
            
            return full_text
            
        except Exception as e:
            logger.error(f"💥 Error in subtitle cleaning: {e}")
            # Return original content if cleaning fails
            return subtitle_content.strip()
    
    def _determine_subtitle_source(self, subtitles: Dict, automatic_captions: Dict) -> str:
        """Determine subtitle source type"""
        # Check if we used manual subtitles
        for lang in ['id', 'auto', 'en']:  # Use same priority as detection
            if lang in subtitles:
                return "manual"
        
        # Check if we used auto-generated
        for lang in ['id', 'auto', 'en']:
            if lang in automatic_captions:
                return "auto-generated"
        
        return "unknown"