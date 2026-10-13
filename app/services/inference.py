"""
Inference Service Layer
Provides unified chat, streaming, and key pool management.
"""
from typing import List, Dict, Any, Optional, AsyncIterator

from app.config import settings
from app.providers.groq_provider import GroqProvider
from app.router.fallback import FallbackManager
from app.router.model_router import ModelRouter, Strategy

# Global Singleton Instances
groq_provider = GroqProvider(base_url=settings.GROQ_BASE_URL)
fallback_manager = FallbackManager(api_keys=settings.API_KEYS)
model_router = ModelRouter(
    fallback_mgr=fallback_manager,
    provider=groq_provider,
    strategy=settings.DEFAULT_STRATEGY
)

class InferenceService:
    @staticmethod
    def get_router() -> ModelRouter:
        return model_router

    @staticmethod
    def get_fallback_manager() -> FallbackManager:
        return fallback_manager

    @staticmethod
    def get_pool_status() -> Dict[str, Any]:
        snapshot = fallback_manager.get_snapshot()
        return {
            "strategy": model_router.strategy,
            "default_model": settings.DEFAULT_MODEL,
            **snapshot
        }

    @staticmethod
    def set_strategy(strategy: str):
        model_router.set_strategy(strategy)
        return model_router.strategy

    @staticmethod
    def add_key(api_key: str, name: Optional[str] = None):
        return fallback_manager.add_key(api_key, name)

    @staticmethod
    def remove_key(key_id: str) -> bool:
        return fallback_manager.remove_key(key_id)

    @staticmethod
    async def test_all_keys() -> List[Dict[str, Any]]:
        results = []
        for key_obj in fallback_manager.keys:
            ok, data, latency_ms = await groq_provider.list_models(key_obj["api_key"])
            if ok:
                key_obj["status"] = "active"
                key_obj["last_error"] = None
                results.append({
                    "id": key_obj["id"],
                    "name": key_obj["name"],
                    "masked_key": key_obj["masked_key"],
                    "valid": True,
                    "latency_ms": round(latency_ms, 2),
                    "models_count": len(data) if isinstance(data, list) else 0,
                    "error": None
                })
            else:
                key_obj["status"] = "invalid"
                key_obj["last_error"] = str(data)
                results.append({
                    "id": key_obj["id"],
                    "name": key_obj["name"],
                    "masked_key": key_obj["masked_key"],
                    "valid": False,
                    "latency_ms": round(latency_ms, 2),
                    "models_count": 0,
                    "error": str(data)
                })
        return results

    @staticmethod
    async def chat_completion(
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 1.0,
        **extra
    ) -> Dict[str, Any]:
        payload = {
            "model": model or settings.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            **extra
        }
        return await model_router.execute_chat(payload)

    @staticmethod
    async def stream_chat(
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 1.0,
        **extra
    ) -> AsyncIterator[Dict[str, Any]]:
        payload = {
            "model": model or settings.DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            **extra
        }
        async for chunk in model_router.execute_stream(payload):
            yield chunk
