"""
Groq API Provider Implementation using Async HTTPX
"""
import time
import json
import httpx
from typing import Dict, Any, Tuple, Optional, AsyncIterator

class GroqProvider:
    def __init__(self, base_url: str = "https://api.groq.com/openai/v1"):
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def parse_reset_seconds(val: Any) -> float:
        if not val:
            return 1.0
        val_str = str(val).strip().lower()
        try:
            if val_str.endswith("ms"):
                return max(0.1, float(val_str[:-2]) / 1000.0)
            if val_str.endswith("s"):
                return max(0.1, float(val_str[:-1]))
            if val_str.endswith("m"):
                return max(1.0, float(val_str[:-1]) * 60.0)
            return max(0.1, float(val_str))
        except ValueError:
            return 1.0

    @classmethod
    def extract_rate_limits(cls, headers: Dict[str, str]) -> Dict[str, Any]:
        """Extracts standard Groq rate limit metrics from response headers."""
        h = {k.lower(): v for k, v in headers.items()}
        result = {}

        if "x-ratelimit-remaining-tokens" in h:
            try: result["remaining_tokens"] = int(h["x-ratelimit-remaining-tokens"])
            except: pass
        if "x-ratelimit-remaining-requests" in h:
            try: result["remaining_requests"] = int(h["x-ratelimit-remaining-requests"])
            except: pass
        if "x-ratelimit-limit-tokens" in h:
            try: result["limit_tokens"] = int(h["x-ratelimit-limit-tokens"])
            except: pass
        if "x-ratelimit-limit-requests" in h:
            try: result["limit_requests"] = int(h["x-ratelimit-limit-requests"])
            except: pass
        if "x-ratelimit-reset-tokens" in h:
            result["reset_tokens_sec"] = cls.parse_reset_seconds(h["x-ratelimit-reset-tokens"])
        if "x-ratelimit-reset-requests" in h:
            result["reset_requests_sec"] = cls.parse_reset_seconds(h["x-ratelimit-reset-requests"])
        if "retry-after" in h:
            result["retry_after_sec"] = cls.parse_reset_seconds(h["retry-after"])

        return result

    async def list_models(self, api_key: str, timeout: float = 10.0) -> Tuple[bool, Any, float]:
        """Validates key and fetches active models."""
        t0 = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {api_key.strip()}",
                        "User-Agent": "UniversalGroqFramework/1.0"
                    }
                )
                latency_ms = (time.time() - t0) * 1000.0
                if resp.status_code == 200:
                    data = resp.json()
                    return True, data.get("data", []), latency_ms
                else:
                    return False, f"HTTP {resp.status_code}: {resp.text[:100]}", latency_ms
            except Exception as e:
                latency_ms = (time.time() - t0) * 1000.0
                return False, str(e), latency_ms

    async def chat_completion(
        self,
        api_key: str,
        payload: Dict[str, Any],
        timeout: float = 60.0
    ) -> Tuple[int, Any, Dict[str, str], float]:
        """
        Executes non-streaming chat completion.
        Returns: (status_code, response_json_or_error_dict, headers_dict, latency_ms)
        """
        t0 = time.time()
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "UniversalGroqFramework/1.0"
        }

        # Ensure stream is False
        body = {**payload, "stream": False}

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body
                )
                latency_ms = (time.time() - t0) * 1000.0
                resp_headers = dict(resp.headers.items())

                if resp.status_code == 200:
                    data = resp.json()
                    return 200, data, resp_headers, latency_ms
                else:
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    return resp.status_code, {"error": err_msg}, resp_headers, latency_ms

            except httpx.TimeoutException:
                latency_ms = (time.time() - t0) * 1000.0
                return 408, {"error": "Request Timeout"}, {}, latency_ms
            except Exception as e:
                latency_ms = (time.time() - t0) * 1000.0
                return 0, {"error": str(e)}, {}, latency_ms

    async def stream_chat(
        self,
        api_key: str,
        payload: Dict[str, Any],
        timeout: float = 60.0
    ) -> AsyncIterator[Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, str]]]]:
        """
        Executes streaming chat completion.
        Yields: (token, reasoning_or_delta, headers)
        """
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "UniversalGroqFramework/1.0"
        }
        body = {**payload, "stream": True}

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = error_text.decode("utf-8", errors="replace")
                    try:
                        err_json = json.loads(error_msg)
                        error_msg = err_json.get("error", {}).get("message", error_msg)
                    except Exception:
                        pass
                    raise RuntimeError(f"HTTP {response.status_code}: {error_msg}")

                resp_headers = dict(response.headers.items())

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line == "data: [DONE]":
                        break
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            reasoning = delta.get("reasoning", delta.get("reasoning_content", ""))
                            yield content, {"reasoning": reasoning, "chunk": chunk}, resp_headers
                        except Exception:
                            continue
