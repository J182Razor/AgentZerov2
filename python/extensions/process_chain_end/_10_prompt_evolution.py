"""
Prompt Evolution Extension (Iteration 3)
After each process chain, scores the interaction quality and logs
improvement candidates for prompt optimization over time.
"""
import json
import os
from datetime import datetime
from python.helpers.extension import Extension

EVOLUTION_LOG_DIR = "knowledge/prompt_evolution"
MIN_ITERATIONS_TO_SCORE = 2    # only score if agent did real work


class PromptEvolution(Extension):
    async def execute(self, loop_data=None, **kwargs):
        try:
            agent = self.agent
            # Fetch fresh loop_data from agent state; the passed parameter may be
            # stale by the time process_chain_end fires.
            loop_data = getattr(agent, 'loop_data', None) or loop_data
            if not loop_data:
                return
            iterations = getattr(loop_data, 'iteration', 0)
            if iterations < MIN_ITERATIONS_TO_SCORE:
                return

            score = self._score_interaction(agent, iterations)
            await self._log_evolution_candidate(agent, score, iterations)
        except Exception:
            pass   # Never block the process chain

    def _score_interaction(self, agent, iterations: int) -> dict:
        """Heuristic scoring: fewer retries + fewer iterations = better."""
        retries = getattr(agent, '_error_retries', 0)
        efficiency = max(0.0, 1.0 - (iterations / 20.0) - (retries * 0.1))
        return {
            "efficiency": round(efficiency, 3),
            "iterations": iterations,
            "retries": retries,
            "timestamp": datetime.now().isoformat(),
        }

    async def _log_evolution_candidate(self, agent, score: dict, iterations: int):
        """Append score to the rolling evolution log."""
        try:
            os.makedirs(EVOLUTION_LOG_DIR, exist_ok=True)
            log_file = os.path.join(EVOLUTION_LOG_DIR, "scores.jsonl")
            entry = {
                "context_id": agent.context.id if hasattr(agent, 'context') else "unknown",
                "agent_number": agent.number,
                **score,
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
