"""
NVIDIA Quota Manager — adaptive rate limiting with predictive backoff.
Monitors quota usage via response headers and model-switches before hitting limits.
"""
from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field
from collections import deque


@dataclass
class QuotaState:
    model: str
    requests_remaining: int = 10_000
    tokens_remaining: int = 1_000_000
    requests_limit: int = 10_000      # initial limit from x-ratelimit-limit-requests
    tokens_limit: int = 1_000_000     # initial limit from x-ratelimit-limit-tokens
    reset_at: float = 0.0        # unix timestamp
    last_updated: float = field(default_factory=time.time)


class QuotaManager:
    """
    Tracks per-model quota from NVIDIA API response headers.
    Warns before limits are hit and suggests fallback models.
    """
    _instance: "QuotaManager | None" = None
    _lock = threading.Lock()

    # Trigger warnings at these thresholds
    REQUEST_WARN_PCT = 0.15    # warn when <15% requests remain
    TOKEN_WARN_PCT   = 0.10    # warn when <10% tokens remain

    # Fallback chain: if primary is throttled, try these in order
    FALLBACK_CHAIN: dict[str, list[str]] = {
        "qwen/qwen3.5-397b-a17b":                 ["z-ai/glm5", "stepfun-ai/step-3.5-flash"],
        "minimaxai/minimax-m2.1":                  ["stepfun-ai/step-3.5-flash"],
        "mistralai/devstral-2-123b-instruct-2512": ["z-ai/glm5", "stepfun-ai/step-3.5-flash"],
        "z-ai/glm5":                               ["stepfun-ai/step-3.5-flash"],
        "moonshotai/kimi-k2.5":                    ["nvidia/llama-3.2-11b-vision-instruct"],
    }

    def __init__(self):
        self._states: dict[str, QuotaState] = {}
        self._lock = threading.Lock()

    @classmethod
    def instance(cls) -> "QuotaManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def update_from_headers(self, model: str, headers: dict):
        """Parse NVIDIA rate-limit headers and update quota state."""
        with self._lock:
            state = self._states.setdefault(model, QuotaState(model=model))
            # Standard NVIDIA NIM / OpenAI-compatible headers
            if "x-ratelimit-limit-requests" in headers:
                try:
                    state.requests_limit = int(headers["x-ratelimit-limit-requests"])
                except (ValueError, TypeError):
                    pass
            if "x-ratelimit-limit-tokens" in headers:
                try:
                    state.tokens_limit = int(headers["x-ratelimit-limit-tokens"])
                except (ValueError, TypeError):
                    pass
            if "x-ratelimit-remaining-requests" in headers:
                try:
                    state.requests_remaining = int(headers["x-ratelimit-remaining-requests"])
                except (ValueError, TypeError):
                    pass
            if "x-ratelimit-remaining-tokens" in headers:
                try:
                    state.tokens_remaining = int(headers["x-ratelimit-remaining-tokens"])
                except (ValueError, TypeError):
                    pass
            if "x-ratelimit-reset-requests" in headers:
                try:
                    state.reset_at = time.time() + float(headers["x-ratelimit-reset-requests"].rstrip("s"))
                except (ValueError, TypeError):
                    pass
            state.last_updated = time.time()

    def is_healthy(self, model: str) -> bool:
        """Returns False if quota is critically low for this model."""
        with self._lock:
            state = self._states.get(model)
            if not state:
                return True   # unknown = assume healthy
            # Check reset window — if quota period elapsed, treat as reset
            if state.reset_at and time.time() > state.reset_at:
                return True
            # Compare remaining against the observed initial limit * threshold
            req_ok = state.requests_remaining > (state.requests_limit * self.REQUEST_WARN_PCT)
            tok_ok = state.tokens_remaining   > (state.tokens_limit   * self.TOKEN_WARN_PCT)
            return req_ok and tok_ok

    def get_fallback(self, model: str) -> str | None:
        """Return a healthy fallback model if the primary is throttled."""
        for fallback in self.FALLBACK_CHAIN.get(model, []):
            if self.is_healthy(fallback):
                return fallback
        return None

    def to_dict(self) -> dict:
        with self._lock:
            return {
                model: {
                    "requests_remaining": s.requests_remaining,
                    "tokens_remaining": s.tokens_remaining,
                    "healthy": self.is_healthy(model),
                    "fallback": self.get_fallback(model),
                }
                for model, s in self._states.items()
            }
