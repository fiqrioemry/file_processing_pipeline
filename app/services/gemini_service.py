import google.generativeai as genai
from typing import Tuple, Dict
from app.config import settings

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def generate_summary_with_usage(self, text: str) -> Tuple[str, Dict]:
        """Generate summary with cost calculation"""
        
        prompt = """Anda adalah seorang ahli dalam membuat ringkasan yang komprehensif dan terstruktur dengan baik.

Buatlah ringkasan dari transkrip berikut dengan format:

## Topik Utama
[Tuliskan topik utama yang dibahas]

## Poin-Poin Kunci
- [Poin penting 1]
- [Poin penting 2]
- [Poin penting 3]

## Detail dan Insight
[Jelaskan detail penting dan wawasan yang dapat diambil]

## Kesimpulan
[Rangkum kesimpulan utama]

Gunakan bahasa Indonesia yang jelas dan mudah dipahami.

Transkrip:
""" + text
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=800,
                    temperature=0.3,
                )
            )
            
            if not response.text:
                raise Exception("Empty response from Gemini")
            
            summary = response.text
            
            # Calculate tokens and cost
            input_tokens = self._count_tokens(prompt)
            output_tokens = self._count_tokens(summary)
            total_tokens = input_tokens + output_tokens
            
            # Gemini 1.5 Flash pricing (as of 2024)
            # Input: $0.075 per 1M tokens, Output: $0.30 per 1M tokens
            input_cost = (input_tokens / 1_000_000) * 0.075
            output_cost = (output_tokens / 1_000_000) * 0.30
            total_cost = input_cost + output_cost
            
            usage_info = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_estimate": round(total_cost, 6),
                "service_used": "gemini"
            }
            
            return summary, usage_info
            
        except Exception as e:
            raise Exception(f"Gemini summary failed: {str(e)}")
    
    async def generate_summary(self, text: str) -> str:
        """Simple summary without usage info"""
        summary, _ = await self.generate_summary_with_usage(text)
        return summary
    
    def _count_tokens(self, text: str) -> int:
        """Estimate token count (4 chars ≈ 1 token for Indonesian)"""
        return max(1, len(text) // 4)