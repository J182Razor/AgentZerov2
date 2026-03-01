"""
SimpleMem Client — semantic structured compression for long-term memory.
Wraps the SimpleMem REST API for dialogue compression and intent-aware retrieval.
"""
from __future__ import annotations
import os
from python.helpers.print_style import PrintStyle

try:
    import aiohttp as _aiohttp
except ImportError:
    _aiohttp = None  # type: ignore

SIMPLEMEM_URL = os.environ.get("SIMPLEMEM_URL", "http://localhost:8765")


class SimpleMemClient:
    """Async client for SimpleMem REST API."""
    _instance: "SimpleMemClient | None" = None

    @classmethod
    def instance(cls) -> "SimpleMemClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or SIMPLEMEM_URL).rstrip("/")

    async def add_dialogue(self, session_id: str, role: str, content: str) -> dict:
        """Add a dialogue turn for semantic compression."""
        try:
            async with _aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/dialogue",
                    json={"session_id": session_id, "role": role, "content": content},
                    timeout=_aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return await resp.json()
        except Exception as e:
            PrintStyle.error(f"SimpleMem add_dialogue failed: {e}")
            return {"error": str(e)}

    async def finalize(self, session_id: str) -> dict:
        """Trigger semantic compression for a session."""
        try:
            async with _aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/finalize",
                    json={"session_id": session_id},
                    timeout=_aiohttp.ClientTimeout(total=30),
                ) as resp:
                    return await resp.json()
        except Exception as e:
            PrintStyle.error(f"SimpleMem finalize failed: {e}")
            return {"error": str(e)}

    async def ask(self, session_id: str, query: str, limit: int = 5) -> dict:
        """Intent-aware retrieval from compressed memory."""
        try:
            async with _aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/ask",
                    params={"session_id": session_id, "query": query, "limit": str(limit)},
                    timeout=_aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return await resp.json()
        except Exception as e:
            PrintStyle.error(f"SimpleMem ask failed: {e}")
            return {"error": str(e)}

    async def health(self) -> bool:
        """Check if SimpleMem server is reachable."""
        try:
            async with _aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=_aiohttp.ClientTimeout(total=3),
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
