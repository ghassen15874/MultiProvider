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

    # All Official Groq Models (Production & Preview)
    MODELS: Dict[str, Dict[str, Any]] = {
        # --- Production Models ---
        "llama-3.1-8b-instant": {
            "name": "Llama 3.1 8B Instant",
            "provider": "Meta",
            "tier": "Production",
            "context_window": 131072,
            "max_completion": 131072,
            "speed": "560 t/s",
            "strengths": "Ultra-fast response, lightweight instruction following",
            "badge": "560 t/s • Production"
        },
        "llama-3.3-70b-versatile": {
            "name": "Llama 3.3 70B Versatile",
            "provider": "Meta",
            "tier": "Production",
            "context_window": 131072,
            "max_completion": 32768,
            "speed": "280 t/s",
            "strengths": "State-of-the-art open weights, high reasoning, versatile",
            "badge": "280 t/s • Production"
        },
        "openai/gpt-oss-120b": {
            "name": "GPT OSS 120B",
            "provider": "OpenAI",
            "tier": "Production",
            "context_window": 131072,
            "max_completion": 65536,
            "speed": "500 t/s",
            "strengths": "Massive 120B deep reasoning, structured architecture, code",
            "badge": "500 t/s • Production"
        },
        "openai/gpt-oss-20b": {
            "name": "GPT OSS 20B",
            "provider": "OpenAI",
            "tier": "Production",
            "context_window": 131072,
            "max_completion": 65536,
            "speed": "1000 t/s",
            "strengths": "Extreme 1000 t/s speed, lightweight reasoning, clean output",
            "badge": "1000 t/s • Production"
        },
        "whisper-large-v3": {
            "name": "Whisper Large V3",
            "provider": "OpenAI",
            "tier": "Production",
            "context_window": 448,
            "max_completion": 448,
            "speed": "Fast Audio",
            "strengths": "Multilingual audio transcription, speech recognition",
            "badge": "Audio • Production"
        },
        "whisper-large-v3-turbo": {
            "name": "Whisper Large V3 Turbo",
            "provider": "OpenAI",
            "tier": "Production",
            "context_window": 448,
            "max_completion": 448,
            "speed": "Ultra Audio",
            "strengths": "High throughput audio transcription and translation",
            "badge": "Audio • Production"
        },

        # --- Preview Models ---
        "qwen/qwen3.8-27b": {
            "name": "Qwen 3.8 (27B)",
            "provider": "Alibaba Cloud",
            "tier": "Preview",
            "context_window": 131072,
            "max_completion": 16384,
            "speed": "450 t/s",
            "strengths": "Full-stack code generation, HTML/CSS/JS, advanced reasoning",
            "badge": "450 t/s • Preview"
        },
        "minimaxai/minimax-m2.7": {
            "name": "MiniMax M2.7",
            "provider": "MiniMax AI",
            "tier": "Preview",
            "context_window": 196608,
            "max_completion": 131072,
            "speed": "260 t/s",
            "strengths": "Massive 196k context window, long document analysis",
            "badge": "196k Context • Preview"
        },
        "allam-2-7b": {
            "name": "ALLaM 2 (7B Instruct)",
            "provider": "SDAIA",
            "tier": "Preview",
            "context_window": 4096,
            "max_completion": 4096,
            "speed": "850 t/s",
            "strengths": "Native Arabic foundation model, cultural nuances, poetry",
            "badge": "Arabic Specialist"
        },
        "openai/gpt-oss-safeguard-20b": {
            "name": "Safety GPT OSS 20B",
            "provider": "OpenAI",
            "tier": "Preview",
            "context_window": 131072,
            "max_completion": 65536,
            "speed": "1000 t/s",
            "strengths": "Safety moderation, content filtering, prompt safety",
            "badge": "Safety Guard"
        },
        "meta-llama/llama-prompt-guard-2-86m": {
            "name": "Prompt Guard 2 (86M)",
            "provider": "Meta",
            "tier": "Preview",
            "context_window": 512,
            "max_completion": 512,
            "speed": "Instant",
            "strengths": "Injection and jailbreak detection",
            "badge": "Prompt Defense"
        },
        "meta-llama/llama-prompt-guard-2-22m": {
            "name": "Llama Prompt Guard 2 (22M)",
            "provider": "Meta",
            "tier": "Preview",
            "context_window": 512,
            "max_completion": 512,
            "speed": "Instant",
            "strengths": "Lightweight prompt defense and classification",
            "badge": "Prompt Defense"
        },
        "canopylabs/orpheus-arabic-saudi": {
            "name": "Canopy Labs Orpheus Arabic Saudi",
            "provider": "Canopy Labs",
            "tier": "Preview",
            "context_window": 4000,
            "max_completion": 50000,
            "speed": "Speech Synthesis",
            "strengths": "Natural Saudi Arabic text-to-speech voice generation",
            "badge": "Speech • Preview"
        },
        "canopylabs/orpheus-v1-english": {
            "name": "Canopy Labs Orpheus V1 English",
            "provider": "Canopy Labs",
            "tier": "Preview",
            "context_window": 4000,
            "max_completion": 50000,
            "speed": "Speech Synthesis",
            "strengths": "High-fidelity English text-to-speech voice generation",
            "badge": "Speech • Preview"
        }
    }

settings = Settings()
