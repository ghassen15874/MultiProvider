"""
Universal AI Framework - Application Configuration
"""
import os
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

def get_api_keys() -> List[str]:
    raw = os.getenv("GROQ_API_KEYS", "")
    if raw:
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if keys:
            return keys
    return []

class Settings:
    PROJECT_NAME: str = "Universal AI Framework"
    VERSION: str = "1.0.0"
    API_KEYS: List[str] = get_api_keys()
    DEFAULT_STRATEGY: str = os.getenv("DEFAULT_STRATEGY", "smart-adaptive")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "qwen/qwen3.8-27b")
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Available Free Models on Groq with capabilities & benchmarks
    MODELS: Dict[str, Dict[str, Any]] = {
        "allam-2-7b": {
            "name": "ALLaM 2 (7B Instruct)",
            "provider": "SDAIA",
            "context_window": 4096,
            "strengths": "Native Arabic Foundation Model, Culture, Poetry, Video Scripts",
            "badge": "Arabic Specialist",
            "recommended_for": ["arabic_video_script", "arabic_chat"],
            "speed_rating": "Ultra Fast (~850 t/s)"
        },
        "qwen/qwen3.8-27b": {
            "name": "Qwen 3.8 (27B)",
            "provider": "Alibaba Cloud",
            "context_window": 131072,
            "strengths": "Full-Stack Code Generation, HTML/CSS/JS, Reasoning, Multilingual",
            "badge": "Top Code & Reasoning",
            "recommended_for": ["code_generation", "web_design", "multilingual"],
            "speed_rating": "Very Fast (~410 t/s)"
        },
        "openai/gpt-oss-120b": {
            "name": "GPT OSS 120B",
            "provider": "OpenAI",
            "context_window": 131072,
            "strengths": "Massive 120B Reasoning Model, Production Scripts, Architecture",
            "badge": "Deep Reasoning 120B",
            "recommended_for": ["deep_reasoning", "script_tables", "complex_code"],
            "speed_rating": "Fast (~360 t/s)"
        },
        "openai/gpt-oss-20b": {
            "name": "GPT OSS 20B",
            "provider": "OpenAI",
            "context_window": 131072,
            "strengths": "Lightweight Reasoning, Clean Output, Fast Response",
            "badge": "Fast Reasoning 20B",
            "recommended_for": ["fast_code", "summaries"],
            "speed_rating": "Ultra Fast (~530 t/s)"
        },
        "openai/gpt-oss-safeguard-20b": {
            "name": "GPT OSS Safeguard 20B",
            "provider": "OpenAI",
            "context_window": 131072,
            "strengths": "Safety Moderation, Prompt Guard",
            "badge": "Safety Filter",
            "recommended_for": ["content_safety"],
            "speed_rating": "Fast (~450 t/s)"
        }
    }

settings = Settings()
