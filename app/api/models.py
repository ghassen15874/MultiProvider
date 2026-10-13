"""
API Endpoints: Models & Key Pool Management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.config import settings
from app.services.inference import InferenceService

router = APIRouter(prefix="/api/models", tags=["models"])

class StrategyRequest(BaseModel):
    strategy: str

class AddKeyRequest(BaseModel):
    api_key: str
    name: Optional[str] = None

@router.get("")
async def list_models():
    """Returns active models and capability catalog."""
    return {
        "status": "ok",
        "models": settings.MODELS,
        "default_model": settings.DEFAULT_MODEL
    }

@router.get("/pool-status")
async def get_pool_status():
    """Returns real-time key metrics, token headroom, and failover event log."""
    return {
        "status": "ok",
        **InferenceService.get_pool_status()
    }

@router.post("/strategy")
async def set_strategy(req: StrategyRequest):
    """Dynamically changes the active rotation strategy."""
    try:
        active_strategy = InferenceService.set_strategy(req.strategy)
        return {"status": "ok", "active_strategy": active_strategy}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/keys/test")
async def test_all_keys():
    """Executes live ping & model fetch across all keys to verify health and latency."""
    results = await InferenceService.test_all_keys()
    return {"status": "ok", "results": results}

@router.post("/keys")
async def add_key(req: AddKeyRequest):
    """Registers a new Groq API key into the rotation pool."""
    key_obj = InferenceService.add_key(req.api_key, req.name)
    if not key_obj:
        raise HTTPException(status_code=400, detail="Invalid API key")
    return {
        "status": "ok",
        "key": {
            "id": key_obj["id"],
            "name": key_obj["name"],
            "masked_key": key_obj["masked_key"],
            "status": key_obj["status"]
        }
    }

@router.delete("/keys/{key_id}")
async def remove_key(key_id: str):
    """Removes a key from the pool."""
    success = InferenceService.remove_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "ok", "removed_id": key_id}
