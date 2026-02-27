"""
Swarm Hint Extension
When the current user message scores above the complexity threshold,
inject a hint into the prompt suggesting StarSwarm for better results.
"""
from python.helpers.extension import Extension
from agent import LoopData


class SwarmHint(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Only hint on the first iteration to avoid repeated nudges
        if loop_data.iteration > 0:
            return

        try:
            from python.helpers.task_complexity import score_task, SWARM_THRESHOLD

            # Get the user message text from history.Message.content
            last_user_msg = ""
            if loop_data and hasattr(loop_data, 'user_message') and loop_data.user_message:
                msg = loop_data.user_message
                content = getattr(msg, 'content', None)
                if isinstance(content, str):
                    last_user_msg = content
                elif isinstance(content, list):
                    last_user_msg = ' '.join(
                        item if isinstance(item, str) else item.get('text', '') if isinstance(item, dict) else ''
                        for item in content
                    )
                elif content is not None:
                    last_user_msg = str(content)

            if not last_user_msg or len(last_user_msg) < 20:
                return

            result = score_task(last_user_msg)
            if result.should_swarm:
                hint = (
                    f"**Complexity Analysis**: This task scores {result.score}/10.0 "
                    f"(threshold: {SWARM_THRESHOLD}). "
                    "Consider using `swarm_star` for parallel decomposition "
                    "to produce higher quality results through multi-agent coordination."
                )
                loop_data.extras_temporary["swarm_hint"] = hint
        except Exception:
            pass
