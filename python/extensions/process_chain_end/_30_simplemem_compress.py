"""
SimpleMem Compression — compress dialogue history after each process chain.
"""
from python.helpers.extension import Extension
from agent import LoopData


class SimpleMemCompress(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        try:
            agent = self.agent
            if not loop_data or loop_data.iteration < 3:
                return

            from python.helpers.simple_mem import SimpleMemClient
            client = SimpleMemClient.instance()

            # Check if SimpleMem is available
            if not await client.health():
                return

            # Use context ID as session
            session_id = agent.context.id if agent.context else "default"

            # Send recent dialogue for compression
            for msg in agent.history[-10:]:
                role = getattr(msg, "role", "user")
                content = str(getattr(msg, "content", "") or "")[:500]
                if content:
                    await client.add_dialogue(session_id, role, content)

            # Trigger compression
            await client.finalize(session_id)
        except Exception:
            pass
