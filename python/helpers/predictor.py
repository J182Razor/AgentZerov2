"""
Task Predictor for Agent Zero (Iteration 3 foundation)
Tracks user message patterns to pre-load relevant context.
"""
from __future__ import annotations
import re
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PredictionResult:
    likely_category: str
    confidence: float          # 0.0-1.0
    suggested_preloads: list[str]   # memory areas to pre-warm
    metadata: dict = field(default_factory=dict)


class TaskPredictor:
    """
    Lightweight pattern predictor. Tracks recent task categories
    and suggests which memory/skills to pre-load for the next turn.
    """

    CATEGORIES = {
        "coding":    [r'\b(code|function|class|bug|debug|implement|script|python|js)\b'],
        "research":  [r'\b(research|find|search|look up|what is|explain|summarize)\b'],
        "writing":   [r'\b(write|draft|essay|email|document|report|article)\b'],
        "analysis":  [r'\b(analyze|compare|evaluate|assess|review|audit)\b'],
        "planning":  [r'\b(plan|schedule|organize|design|architect|roadmap)\b'],
        "data":      [r'\b(data|csv|json|database|sql|table|chart|graph)\b'],
        "system":    [r'\b(install|config|setup|deploy|docker|server|system)\b'],
    }

    PRELOAD_MAP = {
        "coding":   ["solutions", "fragments"],
        "research": ["main", "fragments"],
        "writing":  ["main"],
        "analysis": ["main", "solutions"],
        "planning": ["main", "solutions"],
        "data":     ["solutions", "fragments"],
        "system":   ["solutions"],
    }

    def __init__(self, history_size: int = 20):
        self._history: deque[str] = deque(maxlen=history_size)
        self._category_counts: Counter = Counter()

    def observe(self, message: str):
        """Record a new user message."""
        self._history.append(message.lower())
        cat = self._classify(message)
        if cat:
            self._category_counts[cat] += 1

    def _classify(self, text: str) -> str | None:
        text_lower = text.lower()
        for cat, patterns in self.CATEGORIES.items():
            for p in patterns:
                if re.search(p, text_lower, re.IGNORECASE):
                    return cat
        return None

    def predict_next(self) -> PredictionResult:
        """Predict the most likely next task category."""
        if not self._category_counts:
            return PredictionResult("unknown", 0.0, [])

        most_common, count = self._category_counts.most_common(1)[0]
        total = sum(self._category_counts.values())
        confidence = count / max(total, 1)

        return PredictionResult(
            likely_category=most_common,
            confidence=round(confidence, 3),
            suggested_preloads=self.PRELOAD_MAP.get(most_common, []),
            metadata={"history_size": len(self._history), "counts": dict(self._category_counts)},
        )

    def reset(self):
        self._history.clear()
        self._category_counts.clear()


# Module-level singleton per context
_predictors: dict[str, TaskPredictor] = {}

def get_predictor(context_id: str) -> TaskPredictor:
    if context_id not in _predictors:
        _predictors[context_id] = TaskPredictor()
    return _predictors[context_id]
