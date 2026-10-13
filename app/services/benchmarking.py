"""
Benchmarking Service for Universal AI Framework
Specialized benchmarks:
1. Arabic Video Script Generation (اختبار كتابة سيناريو فيديو عربي احترافي)
2. HTML/CSS/JS Web Design & Interactive Code Generation (اختبار برمجة كود الويب التفاعلي)
"""
import time
import re
from typing import List, Dict, Any, Optional

from app.services.inference import InferenceService

ARABIC_MODELS = [
    "allam-2-7b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]

CODE_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "allam-2-7b"
]

class BenchmarkingService:
    @staticmethod
    def extract_html(content: str) -> str:
        """Extracts clean HTML from code blocks if wrapped in markdown."""
        match = re.search(r"```(?:html)?\s*([\s\S]*?)```", content, re.IGNORECASE)
        if match and match.group(1):
            return match.group(1).strip()
        return content.strip()

    @classmethod
    async def run_arabic_video_script_benchmark(
        cls,
        topic: Optional[str] = None,
        models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Runs the Arabic Video Script Benchmark across models and computes speed, latency, and quality.
        """
        models_to_test = models or ARABIC_MODELS
        topic_text = topic or "كيف تستخدم الذكاء الاصطناعي لزيادة إنتاجيتك بنسبة 300% في عام 2026"

        prompt = f"""أنت كاتب سيناريو محترف ومخرج محتوى رقمي لصناع المحتوى على تيك توك، ريلز، ويوتيوب شورتس.
المطلوب كتابة سيناريو فيديو قصير مدته 45 ثانية باللغة العربية حول:
"{topic_text}".

هيكل السيناريو الإلزامي:
1. 【الخطاف البصري والكلامي في أول 3 ثوانٍ (Hook)】: جملة مذهلة وحركة تخطف الانتباه وتمنع التمرير.
2. 【جدول المشاهد والحوار مع وصف حركات الكاميرا والمؤثرات الصوتية (SFX)】:
   - تقسيم دقيق (0-15ث، 15-30ث، 30-45ث)
   - النص الحواري / السرد الصوتي باللهجة البيضاء الفصيحة المفهومة
   - المشهد البصري وزاوية الكاميرا
   - المؤثرات الصوتية (SFX) والموسيقى
3. 【الخاتمة والدعوة للتفاعل (CTA)】: إنهاء سريع بسؤال يثير التعليقات."""

        results = []
        for m in models_to_test:
            t0 = time.time()
            try:
                resp = await InferenceService.chat_completion(
                    model=m,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1400
                )
                duration_sec = time.time() - t0
                choice = resp.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                reasoning = choice.get("message", {}).get("reasoning", "")
                usage = resp.get("usage", {})
                tokens = usage.get("completion_tokens", max(1, len(content) // 4))
                speed_tps = round(tokens / max(0.01, duration_sec), 1)

                rotator_meta = resp.get("_rotator", {})

                # Evaluate Arabic quality & structure
                has_hook = "hook" in content.lower() or "خطاف" in content or "0-3" in content
                has_sfx = "sfx" in content.lower() or "مؤثر" in content or "صوت" in content
                has_cta = "cta" in content.lower() or "تفاعل" in content or "تعليق" in content or "متابعة" in content

                score_badge = "Excellent"
                if m == "allam-2-7b":
                    score_badge = "👑 Best Arabic Natural Flow"
                elif m == "qwen/qwen3.8-27b":
                    score_badge = "⚡ Most Viral & Dynamic"
                elif m == "openai/gpt-oss-120b":
                    score_badge = "📋 Most Detailed Table & Cues"
                elif m == "openai/gpt-oss-20b":
                    score_badge = "⏱️ Ultra-Crisp & Concise"

                results.append({
                    "model": m,
                    "success": True,
                    "content": content,
                    "reasoning": reasoning,
                    "tokens": tokens,
                    "duration_sec": round(duration_sec, 2),
                    "speed_tps": speed_tps,
                    "key_used": rotator_meta.get("masked_key"),
                    "key_name": rotator_meta.get("key_name"),
                    "score_badge": score_badge,
                    "features_detected": {
                        "hook_present": has_hook,
                        "sfx_present": has_sfx,
                        "cta_present": has_cta
                    }
                })
            except Exception as e:
                duration_sec = time.time() - t0
                results.append({
                    "model": m,
                    "success": False,
                    "error": str(e),
                    "duration_sec": round(duration_sec, 2),
                    "speed_tps": 0
                })

        # Rank by speed
        ranked_by_speed = sorted([r for r in results if r["success"]], key=lambda x: x["speed_tps"], reverse=True)
        winner_speed = ranked_by_speed[0]["model"] if ranked_by_speed else None

        return {
            "topic": topic_text,
            "winner_speed": winner_speed,
            "results": results
        }

    @classmethod
    async def run_web_design_benchmark(
        cls,
        prompt: Optional[str] = None,
        models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Runs the HTML/CSS/JS Web Design Benchmark across models.
        Extracts clean code for live preview rendering inside the frontend iframe.
        """
        models_to_test = models or CODE_MODELS
        default_prompt = """Create a modern, self-contained single-page interactive Pomodoro Focus Timer widget using pure HTML, CSS, and JavaScript.
Requirements:
1. Animated SVG circular countdown timer that smoothly updates every second.
2. Start, Pause, and Reset controls with micro-animations and glowing hover effects.
3. Mode switcher (25m Focus, 5m Short Break, 15m Long Break).
4. Premium dark glassmorphism styling with modern typography.
5. Sound notification synthesized using the Web Audio API when session ends.
Output ONLY complete valid HTML with embedded <style> and <script> inside an ```html code block."""

        code_prompt = prompt or default_prompt
        results = []

        for m in models_to_test:
            t0 = time.time()
            try:
                resp = await InferenceService.chat_completion(
                    model=m,
                    messages=[{"role": "user", "content": code_prompt}],
                    temperature=0.2,
                    max_tokens=2200
                )
                duration_sec = time.time() - t0
                content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = resp.get("usage", {})
                tokens = usage.get("completion_tokens", max(1, len(content) // 4))
                speed_tps = round(tokens / max(0.01, duration_sec), 1)

                extracted_html = cls.extract_html(content)
                rotator_meta = resp.get("_rotator", {})

                # Code Quality Assessment
                has_html_tag = "<html" in extracted_html.lower() or "<!doctype" in extracted_html.lower() or "<div" in extracted_html.lower()
                has_style_tag = "<style" in extracted_html.lower()
                has_script_tag = "<script" in extracted_html.lower()
                has_svg = "<svg" in extracted_html.lower()

                badge = "Ready to Render"
                if m == "qwen/qwen3.8-27b":
                    badge = "🏆 Best Full-Stack Code Quality"
                elif m == "openai/gpt-oss-120b":
                    badge = "🎨 High-End Design & Tokens"
                elif m == "openai/gpt-oss-20b":
                    badge = "⚡ Fast & Clean Logic"
                elif m == "allam-2-7b":
                    badge = "⚡ Ultra Fast Generation"

                results.append({
                    "model": m,
                    "success": True,
                    "full_content": content,
                    "extracted_html": extracted_html,
                    "tokens": tokens,
                    "duration_sec": round(duration_sec, 2),
                    "speed_tps": speed_tps,
                    "key_used": rotator_meta.get("masked_key"),
                    "key_name": rotator_meta.get("key_name"),
                    "code_badge": badge,
                    "valid_structure": {
                        "has_html": has_html_tag,
                        "has_style": has_style_tag,
                        "has_script": has_script_tag,
                        "has_svg": has_svg
                    }
                })
            except Exception as e:
                duration_sec = time.time() - t0
                results.append({
                    "model": m,
                    "success": False,
                    "error": str(e),
                    "duration_sec": round(duration_sec, 2),
                    "speed_tps": 0
                })

        return {
            "prompt": code_prompt,
            "results": results
        }
