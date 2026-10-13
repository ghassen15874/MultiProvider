"""
Tests for Key Pool, Rotation Strategies, and Failover Management
"""
import pytest
from app.router.fallback import FallbackManager, KeyStatus
from app.router.model_router import ModelRouter, Strategy

TEST_KEYS = [
    "gsk_key1_test_aaaaaaaaaaaaaaaaaaaaaaaa",
    "gsk_key2_test_bbbbbbbbbbbbbbbbbbbbbbbb",
    "gsk_key3_test_cccccccccccccccccccccccc"
]

def test_fallback_manager_initialization():
    mgr = FallbackManager(api_keys=TEST_KEYS)
    assert len(mgr.keys) == 3
    assert mgr.keys[0]["status"] == KeyStatus.ACTIVE
    assert mgr.is_available(mgr.keys[0]) is True

def test_fallback_cooldown_and_recovery():
    mgr = FallbackManager(api_keys=TEST_KEYS)
    k0 = mgr.keys[0]

    # Set 0.2s cooldown
    mgr.set_cooldown(k0, 0.2, "Test cooldown")
    assert k0["status"] == KeyStatus.COOLING
    assert mgr.is_available(k0) is False

    # Wait for cooldown to expire
    import time
    time.sleep(0.25)
    assert mgr.is_available(k0) is True
    assert k0["status"] == KeyStatus.ACTIVE

def test_round_robin_strategy():
    mgr = FallbackManager(api_keys=TEST_KEYS)
    router = ModelRouter(fallback_mgr=mgr, strategy=Strategy.ROUND_ROBIN)

    k1 = router.select_key()
    k2 = router.select_key()
    k3 = router.select_key()
    k4 = router.select_key()

    assert k1["id"] != k2["id"]
    assert k2["id"] != k3["id"]
    assert k4["id"] == k1["id"]

def test_smart_adaptive_strategy_prefers_highest_headroom():
    mgr = FallbackManager(api_keys=TEST_KEYS)
    router = ModelRouter(fallback_mgr=mgr, strategy=Strategy.SMART_ADAPTIVE)

    # Key 0 has 1000 tokens left, Key 1 has 5500 tokens left
    mgr.keys[0]["remaining_tokens"] = 1000
    mgr.keys[1]["remaining_tokens"] = 5500
    mgr.keys[2]["remaining_tokens"] = 3000

    chosen = router.select_key()
    assert chosen["id"] == mgr.keys[1]["id"]
