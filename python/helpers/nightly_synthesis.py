"""
Nightly Synthesis Job for Agent Zero
Scheduled batch that summarizes daily interactions, compresses prompt evolution
logs, and generates optimization insights. Runs as a deferred periodic task.
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field


SYNTHESIS_DIR = "knowledge/nightly_synthesis"
EVOLUTION_LOG = "knowledge/prompt_evolution/scores.jsonl"
SYNTHESIS_INTERVAL_HOURS = 24


@dataclass
class SynthesisReport:
    date: str
    total_interactions: int
    avg_efficiency: float
    top_contexts: list[str]
    recommendations: list[str]
    telemetry_summary: dict = field(default_factory=dict)


def _read_evolution_scores(since_hours: int = 24) -> list[dict]:
    """Read recent prompt evolution scores."""
    if not os.path.exists(EVOLUTION_LOG):
        return []
    cutoff = time.time() - (since_hours * 3600)
    scores = []
    try:
        with open(EVOLUTION_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", "")
                    if ts:
                        from datetime import datetime as dt
                        parsed = dt.fromisoformat(ts)
                        if parsed.timestamp() >= cutoff:
                            scores.append(entry)
                    else:
                        scores.append(entry)
                except (json.JSONDecodeError, ValueError):
                    continue
    except Exception:
        pass
    return scores


def _get_telemetry_summary() -> dict:
    """Fetch current telemetry summary."""
    try:
        from python.helpers.telemetry import TelemetryCollector
        return TelemetryCollector.instance().to_dict()
    except Exception:
        return {}


def _generate_recommendations(scores: list[dict], telemetry: dict) -> list[str]:
    """Generate optimization recommendations based on daily data."""
    recs = []

    if not scores:
        return ["No interaction data available for analysis."]

    # Efficiency analysis
    efficiencies = [s.get("efficiency", 0) for s in scores]
    avg_eff = sum(efficiencies) / len(efficiencies) if efficiencies else 0

    if avg_eff < 0.5:
        recs.append("Low average efficiency ({:.1%}). Consider simplifying prompts or breaking complex tasks into sub-tasks.".format(avg_eff))
    elif avg_eff > 0.8:
        recs.append("High efficiency ({:.1%}). Current prompt configuration is performing well.".format(avg_eff))

    # Retry analysis
    high_retry = [s for s in scores if s.get("retries", 0) >= 3]
    if len(high_retry) > len(scores) * 0.2:
        recs.append(f"{len(high_retry)} interactions had 3+ retries. Check model reliability or rate limits.")

    # Iteration analysis
    high_iter = [s for s in scores if s.get("iterations", 0) >= 10]
    if high_iter:
        recs.append(f"{len(high_iter)} tasks required 10+ iterations. Consider improving task decomposition.")

    # Telemetry-based
    roles = telemetry.get("roles", [])
    for role in roles:
        if role.get("success_rate", 1) < 0.9:
            recs.append(f"Role '{role['role']}' has {role['success_rate']:.0%} success rate. Review error patterns.")
        if role.get("p95_latency_ms", 0) > 5000:
            recs.append(f"Role '{role['role']}' P95 latency is {role['p95_latency_ms']:.0f}ms. Consider a faster model.")

    if not recs:
        recs.append("All systems operating within normal parameters.")

    return recs


def run_synthesis() -> SynthesisReport:
    """Run the nightly synthesis and save the report."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scores = _read_evolution_scores(since_hours=SYNTHESIS_INTERVAL_HOURS)
    telemetry = _get_telemetry_summary()

    efficiencies = [s.get("efficiency", 0) for s in scores]
    avg_eff = sum(efficiencies) / len(efficiencies) if efficiencies else 0.0

    # Find top contexts by interaction count
    ctx_counts: dict[str, int] = {}
    for s in scores:
        ctx = s.get("context_id", "unknown")
        ctx_counts[ctx] = ctx_counts.get(ctx, 0) + 1
    top_contexts = sorted(ctx_counts, key=ctx_counts.get, reverse=True)[:5]

    recommendations = _generate_recommendations(scores, telemetry)

    report = SynthesisReport(
        date=today,
        total_interactions=len(scores),
        avg_efficiency=round(avg_eff, 4),
        top_contexts=top_contexts,
        recommendations=recommendations,
        telemetry_summary=telemetry,
    )

    # Save report to disk
    try:
        os.makedirs(SYNTHESIS_DIR, exist_ok=True)
        report_path = os.path.join(SYNTHESIS_DIR, f"synthesis_{today}.json")
        with open(report_path, "w") as f:
            json.dump({
                "date": report.date,
                "total_interactions": report.total_interactions,
                "avg_efficiency": report.avg_efficiency,
                "top_contexts": report.top_contexts,
                "recommendations": report.recommendations,
                "telemetry_summary": report.telemetry_summary,
            }, f, indent=2)
    except Exception:
        pass

    return report


async def nightly_synthesis_loop():
    """Async loop that runs synthesis once per day."""
    import asyncio
    while True:
        try:
            run_synthesis()
        except Exception:
            pass
        await asyncio.sleep(SYNTHESIS_INTERVAL_HOURS * 3600)
