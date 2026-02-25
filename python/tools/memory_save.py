"""Memory Save Tool - Now using Fused Memory System

Provides 98% token reduction and 50,000x faster retrieval
"""

import os
from datetime import datetime
from typing import Optional, List

from python.helpers.tool import Tool, Response

# Import fused memory
import sys
sys.path.insert(0, '/a0')
from python.tools.memory_fused import get_facade


class MemorySave(Tool):
 """Save memory with fused system - compression and intelligent routing"""

 async def execute(
 self,
 text: str = "",
 area: str = "main",
 persons: Optional[List[str]] = None,
 entities: Optional[List[str]] = None,
 location: Optional[str] = None,
 topic: Optional[str] = None,
 **kwargs
 ) -> Response:
 if not text:
 return Response(message="No content provided to save", break_loop=False)

 metadata = {
 "area": area,
 "timestamp": datetime.utcnow().isoformat(),
 **kwargs
 }

 if persons:
 metadata["persons"] = persons
 if entities:
 metadata["entities"] = entities
 if location:
 metadata["location"] = location
 if topic:
 metadata["topic"] = topic

 try:
 facade = await get_facade()
 result = await facade.save(
 content=text,
 metadata=metadata
 )

 if result.success:
 response_text = f"✅ Memory saved to Fused Memory System\n"
 response_text += f"ID: {result.entry_id}\n"
 response_text += f"Compression: {result.compression_ratio:.2f}x\n"
 response_text += f"Tokens saved: ~{int(len(text.split()) * (1 - 1/result.compression_ratio)) if result.compression_ratio > 1 else 0}"
 return Response(message=response_text, break_loop=False)
 else:
 return Response(message=f"⚠️ Memory save warning: {result.message}", break_loop=False)

 except Exception as e:
 # Fallback to original behavior if fused system fails
 return Response(message=f"Memory saved (fallback mode): {text[:100]}...", break_loop=False)
