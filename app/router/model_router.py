"""
Universal Model Router with Key Rotation, Smart Balancing, and Failover
"""
import time
import asyncio
from typing import Set, Dict, Any, List, Optional, AsyncIterator

from app.providers.groq_provider import GroqProvider
from app.router.fallback import FallbackManager, KeyStatus

class Strategy:
    SMART_ADAPTIVE = "smart-adaptive"
    ROUND_ROBIN = "round-robin"
    FAILOVER_SEQUENTIAL = "failover-sequential"
    LEAST_USED = "least-used"

class ModelRouter:
    def __init__(
        self,
        fallback_mgr: FallbackManager,
        provider: GroqProvider = None,
        strategy: str = Strategy.SMART_ADAPTIVE,
        max_retries: int = 6
    ):
        self.fallback = fallback_mgr
        self.provider = provider or GroqProvider()
        self.strategy = strategy
        self.max_retries = max_retries
        self._rr_index = 0

    def set_strategy(self, strategy: str):
        valid = [Strategy.SMART_ADAPTIVE, Strategy.ROUND_ROBIN, Strategy.FAILOVER_SEQUENTIAL, Strategy.LEAST_USED]
        if strategy not in valid:
            raise ValueError(f"Invalid strategy '{strategy}'. Valid: {valid}")
        self.strategy = strategy
        self.fallback.log_event("STRATEGY_CHANGED", f"Active rotation strategy changed to {strategy}")

    def select_key(self, excluded_ids: Set[str] = None) -> Dict[str, Any]:
        if excluded_ids is None:
            excluded_ids = set()

        available = [k for k in self.fallback.get_available_keys() if k["id"] not in excluded_ids]

        if not available:
            # If all are cooling, check if any non-invalid key is cooling with lowest cooldown
            non_invalid = [k for k in self.fallback.keys if k["status"] != KeyStatus.INVALID and k["id"] not in excluded_ids]
            if not non_invalid:
                raise RuntimeError("All Groq API keys are currently exhausted or invalid.")
            non_invalid.sort(key=lambda k: k.get("cooldown_until", 0))
            return non_invalid[0]

        if self.strategy == Strategy.SMART_ADAPTIVE:
            return self._select_smart_adaptive(available)
        elif self.strategy == Strategy.ROUND_ROBIN:
            return self._select_round_robin(available)
        elif self.strategy == Strategy.FAILOVER_SEQUENTIAL:
            return self._select_failover_sequential(available)
        elif self.strategy == Strategy.LEAST_USED:
            return self._select_least_used(available)
        else:
            return self._select_smart_adaptive(available)

    def _select_smart_adaptive(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prioritizes keys with highest remaining tokens and remaining requests."""
        def score(k):
            return (
                k.get("remaining_tokens", 0),
                k.get("remaining_requests", 0),
                -k.get("last_latency_ms", 0)
            )
        return max(candidates, key=score)

    def _select_round_robin(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        self._rr_index = (self._rr_index + 1) % len(candidates)
        return candidates[self._rr_index]

    def _select_failover_sequential(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        cand_ids = {c["id"] for c in candidates}
        for k in self.fallback.keys:
            if k["id"] in cand_ids:
                return k
        return candidates[0]

    def _select_least_used(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        return min(candidates, key=lambda k: k["total_calls"])

    async def execute_chat(
        self,
        payload: Dict[str, Any],
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Executes chat completion with transparent multi-key retry and failover.
        """
        attempted_ids = set()
        max_attempts = min(self.max_retries, max(3, len(self.fallback.keys) * 2))
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                key_obj = self.select_key(attempted_ids)
            except RuntimeError as e:
                if len(attempted_ids) >= len(self.fallback.keys):
                    attempted_ids.clear()
                    key_obj = self.select_key(attempted_ids)
                else:
                    raise e

            attempted_ids.add(key_obj["id"])
            model = payload.get("model", "unknown")

            self.fallback.log_event("CALL_ATTEMPT", f"Attempt {attempt}: routing to {key_obj['name']} ({key_obj['masked_key']}) for {model}")

            status_code, resp_data, headers, latency_ms = await self.provider.chat_completion(
                key_obj["api_key"],
                payload,
                timeout=timeout
            )

            rate_limits = self.provider.extract_rate_limits(headers)

            if status_code == 200 and isinstance(resp_data, dict) and "choices" in resp_data:
                self.fallback.mark_success(key_obj, rate_limits, latency_ms, resp_data.get("usage"))
                self.fallback.log_event(
                    "CALL_SUCCESS",
                    f"{key_obj['name']} completed in {latency_ms:.0f}ms | {resp_data.get('usage', {}).get('total_tokens', 0)} tokens"
                )

                # Attach rotation metadata
                resp_data["_rotator"] = {
                    "key_name": key_obj["name"],
                    "masked_key": key_obj["masked_key"],
                    "key_id": key_obj["id"],
                    "attempts": attempt,
                    "latency_ms": round(latency_ms, 2),
                    "strategy": self.strategy,
                    "model": model
                }
                return resp_data

            # On failure:
            err_msg = resp_data.get("error", f"HTTP {status_code}") if isinstance(resp_data, dict) else str(resp_data)
            self.fallback.mark_failure(key_obj, err_msg, status_code, rate_limits)
            last_error = err_msg

            self.fallback.log_event(
                "FAILOVER_TRIGGERED",
                f"{key_obj['name']} failed ({status_code}): {err_msg[:60]} -> Auto-switching to next key"
            )

            # Non-retriable client errors (except rate limits)
            if status_code == 400 and "rate limit" not in err_msg.lower():
                raise RuntimeError(f"Groq API Error (400): {err_msg}")

            await asyncio.sleep(min(1.0, 0.15 * attempt))

        raise RuntimeError(f"All {max_attempts} attempts failed across key pool. Last error: {last_error}")

    async def execute_stream(
        self,
        payload: Dict[str, Any],
        timeout: float = 60.0
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Streaming generator with failover on initial connection.
        Yields dict chunks: {"type": "token"|"reasoning"|"done"|"error", ...}
        """
        attempted_ids = set()
        max_attempts = min(self.max_retries, max(3, len(self.fallback.keys) * 2))
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                key_obj = self.select_key(attempted_ids)
            except RuntimeError as e:
                if len(attempted_ids) >= len(self.fallback.keys):
                    attempted_ids.clear()
                    key_obj = self.select_key(attempted_ids)
                else:
                    yield {"type": "error", "error": str(e)}
                    return

            attempted_ids.add(key_obj["id"])
            t0 = time.time()
            full_content = []
            full_reasoning = []
            headers_captured = {}

            meta = {
                "key_name": key_obj["name"],
                "masked_key": key_obj["masked_key"],
                "model": payload.get("model"),
                "attempts": attempt,
                "strategy": self.strategy
            }

            try:
                async for token, extra, hdrs in self.provider.stream_chat(
                    key_obj["api_key"],
                    payload,
                    timeout=timeout
                ):
                    if hdrs:
                        headers_captured.update(hdrs)

                    if token:
                        full_content.append(token)
                        yield {"type": "token", "token": token, "meta": meta}

                    if extra and extra.get("reasoning"):
                        full_reasoning.append(extra["reasoning"])
                        yield {"type": "reasoning", "reasoning": extra["reasoning"], "meta": meta}

                latency_ms = (time.time() - t0) * 1000.0
                rate_limits = self.provider.extract_rate_limits(headers_captured)
                completion_tokens = max(1, len("".join(full_content)) // 4)

                self.fallback.mark_success(key_obj, rate_limits, latency_ms, {
                    "prompt_tokens": 0,
                    "completion_tokens": completion_tokens
                })

                yield {
                    "type": "done",
                    "full_content": "".join(full_content),
                    "full_reasoning": "".join(full_reasoning),
                    "meta": {**meta, "latency_ms": round(latency_ms, 2), "tokens": completion_tokens}
                }
                return

            except Exception as e:
                last_error = str(e)
                self.fallback.mark_failure(key_obj, str(e), 429 if "429" in str(e) else 0)
                self.fallback.log_event("STREAM_FAILOVER", f"{key_obj['name']} stream failed: {str(e)[:50]} -> switching key")
                continue

        yield {"type": "error", "error": f"Stream failed across all keys: {last_error}"}
