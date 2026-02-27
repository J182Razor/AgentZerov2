"""
Dynamic Context Window Optimizer for Agent Zero
Manages token budget allocation and predictive compression.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ContextBudget:
    total_tokens: int
    task_tokens: int        # 50% for current task
    history_tokens: int     # 30% for recent history
    memory_tokens: int      # 20% for long-term memory
    compression_needed: bool
    utilization: float      # 0.0-1.0


class ContextOptimizer:
    """
    Analyses context window usage and recommends compression actions
    before token limits are hit.
    """

    TASK_RATIO = 0.50
    HISTORY_RATIO = 0.30
    MEMORY_RATIO = 0.20
    COMPRESSION_TRIGGER = 0.70   # start compressing at 70% full
    CRITICAL_TRIGGER = 0.90      # aggressive compression at 90%

    def __init__(self, context_length: int = 128_000):
        self.context_length = context_length

    def allocate(self, used_tokens: int) -> ContextBudget:
        utilization = used_tokens / max(self.context_length, 1)
        remaining = self.context_length - used_tokens
        compression_needed = utilization >= self.COMPRESSION_TRIGGER

        # If approaching limit, shrink history/memory ratios to protect task space
        if utilization >= self.CRITICAL_TRIGGER:
            task_ratio, history_ratio, memory_ratio = 0.65, 0.25, 0.10
        elif compression_needed:
            task_ratio, history_ratio, memory_ratio = 0.55, 0.30, 0.15
        else:
            task_ratio, history_ratio, memory_ratio = self.TASK_RATIO, self.HISTORY_RATIO, self.MEMORY_RATIO

        return ContextBudget(
            total_tokens=self.context_length,
            task_tokens=int(remaining * task_ratio),
            history_tokens=int(remaining * history_ratio),
            memory_tokens=int(remaining * memory_ratio),
            compression_needed=compression_needed,
            utilization=round(utilization, 4),
        )

    def should_compress_history(self, used_tokens: int) -> bool:
        return (used_tokens / self.context_length) >= self.COMPRESSION_TRIGGER

    def should_compress_aggressively(self, used_tokens: int) -> bool:
        return (used_tokens / self.context_length) >= self.CRITICAL_TRIGGER
