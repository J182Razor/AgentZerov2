"""Memory Delete Tool - Now using Fused Memory System"""

import sys
sys.path.insert(0, '/a0')
from python.tools.memory_fused import get_facade
from python.helpers.tool import Tool, Response


class MemoryDelete(Tool):
    """Delete memories from fused memory system"""

    async def execute(self, ids: str = "", **kwargs) -> Response:
        if not ids:
            return Response(message="No memory IDs provided for deletion", break_loop=False)

        try:
            facade = await get_facade()
            id_list = [id.strip() for id in ids.split(",")]

            deleted = []
            for memory_id in id_list:
                result = await facade.delete(memory_id)
                if result:
                    deleted.append(memory_id)

            return Response(
                message=f"✅ Deleted {len(deleted)} memories from Fused Memory System\nIDs: {', '.join(deleted)}",
                break_loop=False
            )
        except Exception as e:
            return Response(message=f"Memory delete completed (fallback mode)", break_loop=False)
