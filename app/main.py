"""
Universal AI Framework - FastAPI Application Entry Point
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.models import router as models_router
from app.api.inference import router as inference_router

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Key Groq Rotator Framework & Live Inference Platform"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(models_router)
app.include_router(inference_router)

# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "loaded_keys": len(settings.API_KEYS)
    }

# Serve Frontend static assets
if FRONTEND_DIR.exists():
    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("🚀 Universal AI Framework (Groq Rotator) Started")
    print(f"🔑 Pre-configured API Keys: {len(settings.API_KEYS)}")
    print(f"🔄 Active Strategy: {settings.DEFAULT_STRATEGY}")
    print(f"🤖 Default Model: {settings.DEFAULT_MODEL}")
    print(f"🌐 Dashboard: http://{settings.HOST}:{settings.PORT}")
    print(f"🔌 OpenAI Proxy: http://{settings.HOST}:{settings.PORT}/v1/chat/completions")
    print("=" * 60)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
