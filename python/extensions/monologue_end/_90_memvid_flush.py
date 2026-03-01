"""
Memvid Flush — persist conversation turns to .mv2 capsule.
"""
from python.helpers.extension import Extension
from agent import LoopData


class MemvidFlush(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        try:
            from python.helpers.memory_memvid import MemvidStore
            if not MemvidStore.is_available():
                return

            agent = self.agent
            if not loop_data or not loop_data.last_response:
                return

            # Get agent's memory namespace
            from python.helpers.memory import get_agent_memory_subdir
            namespace = get_agent_memory_subdir(agent)
            store = MemvidStore.get(namespace)

            # Build conversation summary to persist
            task = ""
            if loop_data.user_message:
                content = getattr(loop_data.user_message, "content", None)
                if isinstance(content, str):
                    task = content[:500]
                elif isinstance(content, list):
                    task = " ".join(
                        item if isinstance(item, str) else item.get("text", "") if isinstance(item, dict) else ""
                        for item in content
                    )[:500]

            if not task:
                return

            text = f"User: {task}\nAssistant: {loop_data.last_response[:1000]}"
            metadata = {
                "agent": agent.agent_name,
                "iteration": loop_data.iteration,
            }
            store.append(text, metadata)
        except Exception:
            pass
