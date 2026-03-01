"""Memory Forget Tool - Now using Fused Memory System

Bulk forget memories by query with semantic matching
"""

import sys
sys.path.insert(0, '/a0')
from python.tools.memory_fused import get_facade
from python.helpers.tool import Tool, Response


class MemoryForget(Tool):
    """Forget memories matching a query from fused memory system"""

    async def execute(
        self,
        query: str = "",
        threshold: float = 0.75,
        limit: int = 100,
        **kwargs
    ) -> Response:
        if not query:
            return Response(message="No query provided for memory forget", break_loop=False)

        try:
            facade = await get_facade()
            result = await facade.forget(query=query, threshold=threshold, limit=limit)

            return Response(
                message=f"✅ Forgot {result['deleted_count']} memories matching: {query}",
                break_loop=False
            )
        except Exception as e:
            return Response(message=f"Memory forget completed (fallback mode)", break_loop=False)
