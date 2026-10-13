"""
API Endpoints: Inference, Streaming, Benchmarks, and OpenAI-Compatible Proxy
"""
import json
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.services.inference import InferenceService
from app.services.benchmarking import BenchmarkingService

router = APIRouter(tags=["inference"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False

class ArabicBenchmarkRequest(BaseModel):
    topic: Optional[str] = None
    models: Optional[List[str]] = None

class WebDesignBenchmarkRequest(BaseModel):
    prompt: Optional[str] = None
    models: Optional[List[str]] = None

# ==========================================================
# 1. Standard Inference Endpoints
# ==========================================================

@router.post("/api/inference/chat")
async def chat_inference(req: ChatRequest):
    """Executes chat completion with automatic key rotation and failover."""
    try:
        messages_dict = [{"role": m.role, "content": m.content} for m in req.messages]
        result = await InferenceService.chat_completion(
            messages=messages_dict,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            top_p=req.top_p
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/inference/stream")
async def stream_inference(req: ChatRequest):
    """Real-time SSE token streaming with connection failover."""
    messages_dict = [{"role": m.role, "content": m.content} for m in req.messages]

    async def event_generator():
        try:
            async for chunk in InferenceService.stream_chat(
                messages=messages_dict,
                model=req.model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                top_p=req.top_p
            ):
                event_type = chunk.get("type", "token")
                yield f"event: {event_type}\ndata: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# ==========================================================
# 2. Benchmark Endpoints
# ==========================================================

@router.post("/api/inference/benchmark/arabic-script")
async def benchmark_arabic_script(req: ArabicBenchmarkRequest):
    """Runs Arabic Video Script Benchmark across models."""
    try:
        results = await BenchmarkingService.run_arabic_video_script_benchmark(
            topic=req.topic,
            models=req.models
        )
        return {"status": "ok", **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/inference/benchmark/web-design")
async def benchmark_web_design(req: WebDesignBenchmarkRequest):
    """Runs HTML/CSS/JS Web Design Benchmark across models with live preview extraction."""
    try:
        results = await BenchmarkingService.run_web_design_benchmark(
            prompt=req.prompt,
            models=req.models
        )
        return {"status": "ok", **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# 3. OpenAI-Compatible Proxy (/v1/chat/completions)
# Drop-in compatible with Cursor, LangChain, and OpenAI Python SDK!
# ==========================================================

@router.post("/v1/chat/completions")
async def openai_proxy_chat(request: Request):
    """OpenAI-compatible proxy endpoint supporting both stream and non-stream."""
    body = await request.json()
    is_stream = body.get("stream", False)

    messages = body.get("messages", [])
    model = body.get("model", "qwen/qwen3.8-27b")
    temperature = body.get("temperature", 0.7)
    max_tokens = body.get("max_tokens", 1024)
    top_p = body.get("top_p", 1.0)

    if is_stream:
        async def proxy_stream():
            try:
                async for chunk in InferenceService.stream_chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p
                ):
                    chunk_type = chunk.get("type")
                    if chunk_type == "token":
                        data_chunk = {
                            "id": f"chatcmpl-{int(time.time()*1000)}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk.get("token", "")},
                                "finish_reason": None
                            }],
                            "_rotator": chunk.get("meta")
                        }
                        yield f"data: {json.dumps(data_chunk)}\n\n"
                    elif chunk_type == "done":
                        final_chunk = {
                            "id": f"chatcmpl-{int(time.time()*1000)}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }],
                            "_rotator": chunk.get("meta")
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        break
                    elif chunk_type == "error":
                        yield f"data: {json.dumps({'error': {'message': chunk.get('error')}})}\n\n"
                        break
            except Exception as e:
                yield f"data: {json.dumps({'error': {'message': str(e)}})}\n\n"

        return StreamingResponse(
            proxy_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    else:
        try:
            res = await InferenceService.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )
            return res
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error": {"message": str(e)}})
