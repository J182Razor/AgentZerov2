"""
Telemetry & Observability for Agent Zero
Tracks per-model latency, token usage, cost, and error rates.
Provides Prometheus-compatible export and per-role NVIDIA cost tracking.
"""
from __future__ import annotations
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ModelMetric:
    model: str
    role: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    success: bool
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class RoleSummary:
    role: str
    model: str
    call_count: int
    error_count: int
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: float
    p95_latency_ms: float
    success_rate: float


class TelemetryCollector:
    """
    Thread-safe singleton that collects LLM call metrics.
    Keeps a rolling 24h window of metrics per model/role.
    """
    _instance: "TelemetryCollector | None" = None
    _lock = threading.Lock()
    WINDOW_SECONDS = 86_400  # 24 hours

    def __init__(self):
        self._metrics: deque[ModelMetric] = deque()
        self._lock = threading.Lock()

    @classmethod
    def instance(cls) -> "TelemetryCollector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def record(
        self,
        model: str,
        role: str,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        error: str = "",
    ):
        with self._lock:
            self._metrics.append(ModelMetric(
                model=model, role=role, latency_ms=latency_ms,
                input_tokens=input_tokens, output_tokens=output_tokens,
                success=success, error=error,
            ))
            self._evict()

    def _evict(self):
        cutoff = time.time() - self.WINDOW_SECONDS
        while self._metrics and self._metrics[0].timestamp < cutoff:
            self._metrics.popleft()

    def _recent(self) -> list[ModelMetric]:
        with self._lock:
            self._evict()
            return list(self._metrics)

    def summary_by_role(self) -> list[RoleSummary]:
        metrics = self._recent()
        by_role: dict[str, list[ModelMetric]] = defaultdict(list)
        for m in metrics:
            by_role[m.role].append(m)

        summaries = []
        for role, ms in by_role.items():
            latencies = sorted(m.latency_ms for m in ms)
            n = len(latencies)
            summaries.append(RoleSummary(
                role=role,
                model=ms[-1].model if ms else "",
                call_count=n,
                error_count=sum(1 for m in ms if not m.success),
                total_input_tokens=sum(m.input_tokens for m in ms),
                total_output_tokens=sum(m.output_tokens for m in ms),
                avg_latency_ms=round(sum(latencies) / n, 2) if n else 0.0,
                p95_latency_ms=round(latencies[int(n * 0.95)] if n > 1 else (latencies[0] if latencies else 0.0), 2),
                success_rate=round(sum(1 for m in ms if m.success) / n, 4) if n else 1.0,
            ))
        return sorted(summaries, key=lambda s: s.role)

    def to_prometheus(self) -> str:
        """Return Prometheus text-format metrics."""
        lines = ["# HELP agz_llm_calls_total Total LLM calls per role"]
        lines.append("# TYPE agz_llm_calls_total counter")
        for s in self.summary_by_role():
            label = f'role="{s.role}",model="{s.model}"'
            lines.append(f'agz_llm_calls_total{{{label}}} {s.call_count}')
            lines.append(f'agz_llm_errors_total{{{label}}} {s.error_count}')
            lines.append(f'agz_llm_input_tokens_total{{{label}}} {s.total_input_tokens}')
            lines.append(f'agz_llm_output_tokens_total{{{label}}} {s.total_output_tokens}')
            lines.append(f'agz_llm_latency_avg_ms{{{label}}} {s.avg_latency_ms}')
            lines.append(f'agz_llm_latency_p95_ms{{{label}}} {s.p95_latency_ms}')
        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict:
        return {
            "window_hours": 24,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "roles": [
                {
                    "role": s.role, "model": s.model,
                    "calls": s.call_count, "errors": s.error_count,
                    "success_rate": s.success_rate,
                    "tokens_in": s.total_input_tokens,
                    "tokens_out": s.total_output_tokens,
                    "avg_latency_ms": s.avg_latency_ms,
                    "p95_latency_ms": s.p95_latency_ms,
                }
                for s in self.summary_by_role()
            ],
        }
