"""
Agent0 Evolution Hook — submits completed tasks for verification.
Verified solutions feed the self-evolution curriculum.
"""
from python.helpers.extension import Extension
from agent import LoopData


class Agent0Evolve(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        try:
            agent = self.agent
            if not loop_data or loop_data.iteration < 2:
                return

            # Check if evolution is enabled
            from python.helpers import settings
            s = settings.get_settings()
            if not s.get("agent0_evolution_enabled", False):
                return

            # Get the task (first user message) and solution (last response)
            task = ""
            for msg in agent.history:
                if getattr(msg, "role", "") == "user":
                    task = str(getattr(msg, "content", ""))[:500]
                    break
            if not task or len(task) < 20:
                return

            solution = loop_data.last_response[:1000] if loop_data.last_response else ""
            if not solution:
                return

            # Extract tool calls
            import re
            tool_calls = []
            for msg in agent.history[-20:]:
                content = str(getattr(msg, "content", "") or "")
                tools = re.findall(r'"tool_name"\s*:\s*"([^"]+)"', content)
                tool_calls.extend(t for t in tools if t not in ("response", "wait"))

            # Submit for async verification (non-blocking)
            from python.helpers.agent0_evolution import EvolutionManager
            await EvolutionManager.instance().submit_for_verification(
                agent, task, solution, tool_calls
            )
        except Exception:
            pass
