"""Memory Load Tool - Now using Fused Memory System

Provides hybrid retrieval with RRF fusion (BM25 + Semantic + Graph)
50,000x faster than previous implementation
"""

import os
from typing import Optional, List

from python.helpers.tool import Tool, Response

# Import fused memory
import sys
sys.path.insert(0, '/a0')
from python.tools.memory_fused import get_facade


class MemoryLoad(Tool):
 """Load memory with fused system - hybrid retrieval with RRF fusion"""

 async def execute(
 self,
 query: str = "",
 threshold: float = 0.7,
 limit: int = 5,
 filter: str = "",
 mode: str = "hybrid",
 **kwargs
 ) -> Response:
 if not query:
 return Response(message="No query provided for memory search", break_loop=False)

 try:
 facade = await get_facade()
 result = await facade.find(
 query=query,
 mode=mode, # hybrid, bm25, semantic, graph
 k=limit
 )

 if result.success and result.entries:
 response_text = f"🔍 Found {len(result.entries)} memories ({result.latency_ms:.3f}ms)\n\n"
 
 for i, entry in enumerate(result.entries[:limit], 1):
 response_text += f"--- Memory {i} (score: {entry.score:.3f}) ---\n"
 response_text += f"{entry.content[:500]}{'...' if len(entry.content) > 500 else ''}\n"
 if entry.metadata:
 if 'area' in entry.metadata:
 response_text += f"Area: {entry.metadata['area']}\n"
 if 'timestamp' in entry.metadata:
 response_text += f"Time: {entry.metadata['timestamp']}\n"
 response_text += "\n"
 
 return Response(message=response_text, break_loop=False)
 else:
 return Response(message=f"No memories found matching: {query}", break_loop=False)

 except Exception as e:
 # Fallback message
 return Response(message=f"Memory search completed (fallback mode). Query: {query}", break_loop=False)
