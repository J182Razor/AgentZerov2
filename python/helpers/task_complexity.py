"""
Task Complexity Scorer for Agent Zero
Scores task complexity to decide whether to auto-trigger StarSwarm.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class ComplexityScore:
    score: float          # 0.0 - 10.0
    reasons: list[str]
    should_swarm: bool    # True if score > SWARM_THRESHOLD


SWARM_THRESHOLD = 6.5

# Keywords that indicate complexity
HIGH_COMPLEXITY_PATTERNS = [
    (r'\b(research|analyze|compare|evaluate|synthesize|investigate)\b', 1.5),
    (r'\b(multiple|several|various|different|comprehensive)\b', 1.0),
    (r'\b(step[s]?|phase[s]?|stage[s]?|pipeline)\b', 1.0),
    (r'\b(parallel|concurrent|simultaneously|at the same time)\b', 1.5),
    (r'\b(integrate|combine|merge|aggregate)\b', 1.0),
    (r'\b(report|summary|plan|strategy|architecture)\b', 1.2),
    (r'\band\b.{1,30}\band\b', 0.8),           # multiple conjunctions
    (r'\?.*\?', 0.5),                            # multiple questions
]

LOW_COMPLEXITY_PATTERNS = [
    (r'^(what is|who is|when did|where is|how much|how many)\b', -2.0),
    (r'^(yes|no|ok|sure|thanks|hello|hi)\b', -3.0),
    (r'\b(simple|quick|brief|just|only)\b', -1.0),
]


def score_task(task_text: str) -> ComplexityScore:
    """Score a task string for complexity. Returns ComplexityScore."""
    text = task_text.lower().strip()
    score = 2.0  # baseline
    reasons = []

    # Length bonus (longer tasks tend to be more complex)
    word_count = len(text.split())
    if word_count > 100:
        score += 2.0
        reasons.append(f"long task ({word_count} words)")
    elif word_count > 50:
        score += 1.0
        reasons.append(f"medium length ({word_count} words)")

    # High complexity patterns
    for pattern, weight in HIGH_COMPLEXITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            score += weight
            reasons.append(f"+{weight} for pattern '{pattern[:30]}'")

    # Low complexity patterns
    for pattern, weight in LOW_COMPLEXITY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            score += weight
            reasons.append(f"{weight} for simple pattern")

    score = max(0.0, min(10.0, score))
    return ComplexityScore(
        score=round(score, 2),
        reasons=reasons,
        should_swarm=score >= SWARM_THRESHOLD,
    )
