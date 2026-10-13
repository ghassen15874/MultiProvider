"""
Fallback & Key Pool State Management
Tracks rate limits, cooldowns, latencies, and health for each Groq key.
"""
import time
from typing import List, Dict, Any, Optional

class KeyStatus:
    ACTIVE = "active"
    COOLING = "cooling"
    EXHAUSTED = "exhausted"
    INVALID = "invalid"

class FallbackManager:
    def __init__(self, api_keys: List[str] = None):
        self.keys: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.max_events = 100

        if api_keys:
            for idx, key in enumerate(api_keys):
                self.add_key(key, f"Key {idx + 1}")

    @staticmethod
    def mask_key(key: str) -> str:
        if not key or len(key) < 12:
            return "***"
        return f"{key[:8]}...{key[-4:]}"

    def add_key(self, api_key: str, name: Optional[str] = None) -> Dict[str, Any]:
        api_key = (api_key or "").strip()
        if not api_key:
            return None

        # Check existing
        for k in self.keys:
            if k["api_key"] == api_key:
                return k

        idx = len(self.keys) + 1
        key_id = f"groq_key_{idx}_{int(time.time() * 1000) % 100000}"
        key_obj = {
            "id": key_id,
            "name": name or f"Key {idx}",
            "api_key": api_key,
            "masked_key": self.mask_key(api_key),
            "status": KeyStatus.ACTIVE,
            "cooldown_until": 0.0,
            "cooldown_reason": None,
            "remaining_requests": 7000,
            "remaining_tokens": 6000,
            "limit_requests": 7000,
            "limit_tokens": 6000,
            "reset_requests_sec": 0.0,
            "reset_tokens_sec": 0.0,
            "total_calls": 0,
            "success_calls": 0,
            "failed_calls": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "last_used_at": 0.0,
            "last_latency_ms": 0.0,
            "last_error": None
        }
        self.keys.append(key_obj)
        self.log_event("KEY_REGISTERED", f"Added {key_obj['name']} ({key_obj['masked_key']})")
        return key_obj

    def remove_key(self, id_or_key: str) -> bool:
        for i, k in enumerate(self.keys):
            if k["id"] == id_or_key or k["api_key"] == id_or_key:
                removed = self.keys.pop(i)
                self.log_event("KEY_REMOVED", f"Removed {removed['name']} ({removed['masked_key']})")
                return True
        return False

    def is_available(self, key_obj: Dict[str, Any]) -> bool:
        if key_obj["status"] == KeyStatus.INVALID:
            return False

        if key_obj["cooldown_until"] > 0:
            now = time.time()
            if now >= key_obj["cooldown_until"]:
                key_obj["status"] = KeyStatus.ACTIVE
                key_obj["cooldown_until"] = 0.0
                key_obj["cooldown_reason"] = None
                self.log_event("KEY_RECOVERED", f"{key_obj['name']} cooldown expired, restored to pool")
                return True
            return False

        return key_obj["status"] == KeyStatus.ACTIVE

    def get_available_keys(self) -> List[Dict[str, Any]]:
        return [k for k in self.keys if self.is_available(k)]

    def set_cooldown(self, key_obj: Dict[str, Any], duration_sec: float, reason: str = "Rate limit"):
        key_obj["status"] = KeyStatus.COOLING
        key_obj["cooldown_until"] = time.time() + max(0.1, duration_sec)
        key_obj["cooldown_reason"] = reason
        self.log_event("KEY_COOLDOWN", f"{key_obj['name']} paused for {duration_sec:.1f}s ({reason})")

    def mark_success(
        self,
        key_obj: Dict[str, Any],
        rate_limits: Dict[str, Any],
        latency_ms: float = 0.0,
        usage: Dict[str, Any] = None
    ):
        key_obj["total_calls"] += 1
        key_obj["success_calls"] += 1
        key_obj["last_used_at"] = time.time()
        key_obj["last_latency_ms"] = round(latency_ms, 2)
        key_obj["last_error"] = None

        if usage:
            key_obj["total_prompt_tokens"] += usage.get("prompt_tokens", 0)
            key_obj["total_completion_tokens"] += usage.get("completion_tokens", 0)

        if rate_limits:
            if "remaining_requests" in rate_limits:
                key_obj["remaining_requests"] = rate_limits["remaining_requests"]
            if "remaining_tokens" in rate_limits:
                key_obj["remaining_tokens"] = rate_limits["remaining_tokens"]
            if "limit_requests" in rate_limits:
                key_obj["limit_requests"] = rate_limits["limit_requests"]
            if "limit_tokens" in rate_limits:
                key_obj["limit_tokens"] = rate_limits["limit_tokens"]
            if "reset_requests_sec" in rate_limits:
                key_obj["reset_requests_sec"] = rate_limits["reset_requests_sec"]
            if "reset_tokens_sec" in rate_limits:
                key_obj["reset_tokens_sec"] = rate_limits["reset_tokens_sec"]

            # Preventive cooldown if quota is nearly zero
            if key_obj["remaining_tokens"] < 100 or key_obj["remaining_requests"] < 2:
                cooldown = max(key_obj["reset_tokens_sec"], key_obj["reset_requests_sec"], 5.0)
                self.set_cooldown(key_obj, cooldown, "Low token/request headroom")

    def mark_failure(
        self,
        key_obj: Dict[str, Any],
        error_msg: str,
        status_code: int = 0,
        rate_limits: Dict[str, Any] = None
    ):
        key_obj["total_calls"] += 1
        key_obj["failed_calls"] += 1
        key_obj["last_error"] = str(error_msg)
        key_obj["last_used_at"] = time.time()

        if status_code == 401:
            key_obj["status"] = KeyStatus.INVALID
            key_obj["cooldown_reason"] = "401 Unauthorized"
            self.log_event("KEY_INVALID", f"{key_obj['name']} rejected: 401 Invalid Key")
            return

        if status_code == 429:
            cooldown_sec = 10.0
            if rate_limits:
                if "retry_after_sec" in rate_limits:
                    cooldown_sec = rate_limits["retry_after_sec"]
                elif "reset_tokens_sec" in rate_limits:
                    cooldown_sec = rate_limits["reset_tokens_sec"]
            self.set_cooldown(key_obj, cooldown_sec, "429 Rate Limit Exceeded")
            return

        if status_code >= 500 or status_code == 0 or status_code == 408:
            self.set_cooldown(key_obj, 5.0, f"Server/Network Error ({status_code})")

    def log_event(self, event_type: str, message: str):
        evt = {
            "time": time.strftime("%H:%M:%S", time.localtime()),
            "type": event_type,
            "message": message
        }
        self.events.insert(0, evt)
        if len(self.events) > self.max_events:
            self.events.pop()

    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "total_keys": len(self.keys),
            "available_keys": len(self.get_available_keys()),
            "keys": [
                {
                    "id": k["id"],
                    "name": k["name"],
                    "masked_key": k["masked_key"],
                    "status": KeyStatus.ACTIVE if self.is_available(k) else k["status"],
                    "cooldown_remaining_sec": max(0, int(k["cooldown_until"] - time.time())) if k["cooldown_until"] else 0,
                    "cooldown_reason": k["cooldown_reason"],
                    "remaining_requests": k["remaining_requests"],
                    "remaining_tokens": k["remaining_tokens"],
                    "limit_requests": k["limit_requests"],
                    "limit_tokens": k["limit_tokens"],
                    "total_calls": k["total_calls"],
                    "success_calls": k["success_calls"],
                    "failed_calls": k["failed_calls"],
                    "success_rate": round((k["success_calls"] / max(1, k["total_calls"])) * 100, 1),
                    "last_latency_ms": k["last_latency_ms"],
                    "last_error": k["last_error"]
                }
                for k in self.keys
            ],
            "recent_events": self.events[:25]
        }
