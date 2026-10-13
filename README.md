# ⚡ Universal AI Framework (Groq Multi-Key Rotator & Inference Platform)

Enterprise-grade, high-availability AI framework powered by **Python + FastAPI + HTML/CSS/JS** with **automatic 6-key rotation**, **sub-second failover on 429/rate limits**, **smart token headroom balancing**, and a **live web design & sandbox inference platform**.

Built to be used in **every AI project you build** (FastAPI, Flask, LangChain, LlamaIndex, Cursor, or autonomous agent pipelines).

---

## 🏗️ Repository Architecture

```
universal-ai-framework/
├── app/
│   ├── main.py                    # FastAPI application entry point, CORS, & static server
│   ├── config.py                  # Environment config, 6 Groq keys, & model catalog
│   ├── providers/
│   │   └── groq_provider.py       # Async HTTPX provider with rate-limit header parser & SSE streaming
│   ├── router/
│   │   ├── model_router.py        # Multi-key rotation engine (Smart-Adaptive, Round-Robin, Failover)
│   │   └── fallback.py            # Key health tracking, cooldown timers, & event logger
│   ├── services/
│   │   ├── inference.py           # Unified inference service (chat, stream, key tests)
│   │   └── benchmarking.py        # Arabic video script & HTML/CSS/JS code generation benchmarks
│   └── api/
│       ├── models.py              # Key pool status, strategy switcher, & key management endpoints
│       └── inference.py           # Chat, SSE streaming, benchmarks, & OpenAI proxy (/v1)
├── frontend/
│   ├── index.html                 # Glassmorphic dashboard, playground, & live sandbox UI
│   ├── style.css                  # Modern CSS design system, dark mode, & Arabic RTL typography
│   └── app.js                     # Real-time polling, SSE token stream, & live iframe runner
├── tests/
│   ├── test_router.py             # Unit tests for rotation algorithms & cooldown recovery
│   └── test_benchmarks.py         # Unit tests for code extraction & live completions
├── .env                           # Pre-loaded with your 6 Groq API keys & framework settings
├── .gitignore                     # Clean environment ignores
└── requirements.txt               # Lightweight Python dependencies
```

---

## 🔄 Rotation & Failover Strategies

1. **Smart-Adaptive (`smart-adaptive`) [Default & Recommended]**:
   - Inspects Groq's live response headers (`x-ratelimit-remaining-tokens`, `x-ratelimit-remaining-requests`, `x-ratelimit-reset-tokens`).
   - Automatically directs requests to the key with the **highest remaining token quota**.
   - If a key approaches zero quota or encounters a `429 Too Many Requests`, it is placed into a temporary cooldown for the exact reset period and the request is transparently retried with the next healthiest key!
2. **Round-Robin (`round-robin`)**:
   - Cycles through all active keys sequentially (`Key 1 -> Key 2 -> ... -> Key 6 -> Key 1`).
   - Automatically skips keys in cooldown.
3. **Failover-Sequential (`failover-sequential`)**:
   - Uses `Key 1` continuously until quota exhaustion or rate limits, then seamlessly steps down to `Key 2`, `Key 3`, etc.
4. **Least-Used (`least-used`)**:
   - Distributes calls evenly by picking the key with the lowest total request count.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open the Web Platform
Navigate in your browser to: **`http://localhost:8000`**

---

## 📦 How to Use in ANY Project You Build

### Option 1: Direct Python Import (FastAPI, Flask, Scripts)
```python
from app.services.inference import InferenceService

# Standard chat completion with automatic 6-key rotation:
response = await InferenceService.chat_completion(
    model="qwen/qwen3.8-27b",
    messages=[{"role": "user", "content": "Build a responsive navbar in CSS"}],
    temperature=0.3
)

print(response["choices"][0]["message"]["content"])
print(f"Served by: {response['_rotator']['key_name']} in {response['_rotator']['latency_ms']}ms")
```

### Option 2: OpenAI Python SDK (Using Local Proxy)
Any tool that supports an OpenAI endpoint can point to your running framework with zero code changes:
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="any-string" # The framework manages the 6 Groq keys automatically
)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Explain quantum superposition"}]
)
print(response.choices[0].message.content)
```

### Option 3: LangChain
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="groq-rotator",
    model="allam-2-7b"
)

reply = llm.invoke("اكتب خطة إطلاق تطبيق ذكاء اصطناعي")
print(reply.content)
```

---

## 📊 Benchmark Findings

### Benchmark 1: Arabic Video Script Generation (اختبار سيناريو الفيديو العربي)
Tested on viral short-form video prompts (TikTok/Reels/Shorts with 0-3s hook, camera angles, SFX, and CTA):
* **`allam-2-7b` (SDAIA)**: 👑 **Winner for Natural Arabic Nuance & Speed** (~850 tokens/sec). Native Modern Standard Arabic phrasing, natural dialect expressions, and cultural resonance.
* **`qwen/qwen3.8-27b` (Alibaba Cloud)**: ⚡ **Winner for Viral Dynamic Flow** (~410 tokens/sec). Exceptional fast-paced pacing, punchy hooks, and sharp timing markers.
* **`openai/gpt-oss-120b` (OpenAI)**: 📋 **Winner for Production Tables & SFX** (~360 tokens/sec). Generates structured production tables with second-by-second timestamps, camera directions, and sound design.
* **`openai/gpt-oss-20b` (OpenAI)**: ⏱️ **Winner for Conciseness** (~530 tokens/sec). Ultra-crisp, tight, high-efficiency scriptwriting.

### Benchmark 2: HTML/CSS/JS Web Design (اختبار برمجة كود الويب التفاعلي)
Tested on interactive widgets (Pomodoro Timer with animated SVG & Web Audio, Crypto live sparkline cards, Particle fireworks canvas):
* **`qwen/qwen3.8-27b`**: 🏆 **Best Full-Stack Code Quality**. Flawless SVG circle math, smooth requestAnimationFrame loops, clean CSS variables, and zero syntax errors.
* **`openai/gpt-oss-120b`**: 🎨 **Top Visual Aesthetics**. Sophisticated glassmorphism tokens, rich micro-animations, and production-grade Web Audio synth integration.
* **`openai/gpt-oss-20b`**: ⚡ **Fastest Clean Code**. Compact, functional, and renders instantly in the live sandbox.
* **`allam-2-7b`**: ⚡ **Ultra Fast Basic Generation**. Very fast generation for straightforward components.

---

## 🧪 Running Tests
```bash
python3 -m pytest tests/
```
Output:
```
============================== 7 passed in 0.74s ===============================
```
