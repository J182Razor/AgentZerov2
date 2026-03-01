"""
Agent0 Evolution — self-improving agent via competitive co-evolution.
Implements a simplified version of Agent0's curriculum/executor/verifier loop
using AgentZero's existing utility model.
"""
from __future__ import annotations
import os
import json
import time
from datetime import datetime
from python.helpers import files
from python.helpers.print_style import PrintStyle

EVOLUTION_DIR = "knowledge/agent0_evolution"
CURRICULUM_FILE = "curriculum.jsonl"
VERIFIED_FILE = "verified.jsonl"


class EvolutionManager:
    """
    Manages the self-evolution feedback loop:
    1. After each task, submit task+solution to verifier
    2. Verified solutions are added to the curriculum
    3. Nightly batch generates harder variants (curriculum agent)
    """
    _instance: "EvolutionManager | None" = None

    @classmethod
    def instance(cls) -> "EvolutionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._dir = files.get_abs_path(EVOLUTION_DIR)
        os.makedirs(self._dir, exist_ok=True)

    async def submit_for_verification(
        self, agent, task: str, solution: str, tool_calls: list[str]
    ) -> dict:
        """
        Submit a completed task for verification using the utility model.
        Returns verification result with score and feedback.
        """
        try:
            prompt = (
                "You are a solution verifier. Evaluate whether this solution correctly "
                "addresses the task. Score 0-10 and provide brief feedback.\n\n"
                f"TASK: {task[:500]}\n\n"
                f"SOLUTION: {solution[:1000]}\n\n"
                f"TOOLS USED: {', '.join(tool_calls[:10])}\n\n"
                "Respond in JSON: {\"score\": N, \"feedback\": \"...\", \"verified\": true/false}"
            )
            result = await agent.call_utility_model(
                system="You are a strict but fair solution verifier. Return valid JSON only.",
                message=prompt,
                background=True,
            )
            try:
                parsed = json.loads(result.strip().strip("```json").strip("```"))
            except json.JSONDecodeError:
                parsed = {"score": 5, "feedback": result[:200], "verified": False}

            # Log verified solutions
            if parsed.get("verified", False):
                self._append_verified(task, solution, tool_calls, parsed)

            return parsed
        except Exception as e:
            PrintStyle.error(f"Evolution verification failed: {e}")
            return {"score": 0, "feedback": str(e), "verified": False}

    def _append_verified(self, task: str, solution: str, tools: list[str], result: dict):
        """Append a verified solution to the curriculum."""
        path = os.path.join(self._dir, VERIFIED_FILE)
        entry = {
            "task": task[:500],
            "solution": solution[:1000],
            "tools": tools[:10],
            "score": result.get("score", 0),
            "timestamp": datetime.now().isoformat(),
        }
        try:
            with open(path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            PrintStyle.error(f"Evolution append failed: {e}")

    async def generate_curriculum(self, agent, count: int = 5) -> list[dict]:
        """
        Generate harder task variants from verified solutions (curriculum agent).
        Called during nightly synthesis.
        """
        verified = self._read_verified(limit=20)
        if not verified:
            return []

        tasks_text = "\n".join(
            f"- {v['task']}" for v in verified[-10:]
        )
        prompt = (
            f"Based on these successfully completed tasks:\n{tasks_text}\n\n"
            f"Generate {count} NEW, harder task variants that build on these skills. "
            "Each should be more challenging but achievable. "
            "Return as JSON array: [{\"task\": \"...\", \"difficulty\": N}]"
        )
        try:
            result = await agent.call_utility_model(
                system="You are a curriculum designer. Generate progressively harder tasks.",
                message=prompt,
                background=True,
            )
            parsed = json.loads(result.strip().strip("```json").strip("```"))
            # Save to curriculum
            path = os.path.join(self._dir, CURRICULUM_FILE)
            for item in parsed:
                item["generated"] = datetime.now().isoformat()
                with open(path, "a") as f:
                    f.write(json.dumps(item) + "\n")
            return parsed
        except Exception as e:
            PrintStyle.error(f"Curriculum generation failed: {e}")
            return []

    def _read_verified(self, limit: int = 50) -> list[dict]:
        path = os.path.join(self._dir, VERIFIED_FILE)
        if not os.path.exists(path):
            return []
        try:
            entries = []
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            return entries[-limit:]
        except Exception:
            return []

    def get_stats(self) -> dict:
        verified = self._read_verified(limit=10000)
        return {
            "total_verified": len(verified),
            "avg_score": sum(v.get("score", 0) for v in verified) / max(len(verified), 1),
            "last_verified": verified[-1]["timestamp"] if verified else None,
        }
