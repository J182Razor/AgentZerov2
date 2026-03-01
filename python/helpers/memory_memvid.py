"""
Memvid Memory Backend — ultra-low-latency .mv2 capsule-based memory.
Wraps the memvid Python SDK as an alternative memory store for AgentZero.
Falls back gracefully if memvid is not installed.
"""
from __future__ import annotations
import os
import time
from typing import Any
from python.helpers import files
from python.helpers.print_style import PrintStyle

_MEMVID_AVAILABLE = False
try:
    import memvid
    _MEMVID_AVAILABLE = True
except ImportError:
    pass

CAPSULE_DIR = "knowledge/memvid"


class MemvidStore:
    """Singleton wrapper around a memvid capsule file."""
    _instances: dict[str, "MemvidStore"] = {}

    @classmethod
    def get(cls, namespace: str = "default") -> "MemvidStore":
        if namespace not in cls._instances:
            cls._instances[namespace] = cls(namespace)
        return cls._instances[namespace]

    @classmethod
    def is_available(cls) -> bool:
        return _MEMVID_AVAILABLE

    def __init__(self, namespace: str):
        self.namespace = namespace
        self.capsule_path = files.get_abs_path(CAPSULE_DIR, f"{namespace}.mv2")
        self._capsule = None
        os.makedirs(files.get_abs_path(CAPSULE_DIR), exist_ok=True)
        if _MEMVID_AVAILABLE:
            try:
                if os.path.exists(self.capsule_path):
                    self._capsule = memvid.load(self.capsule_path)
                else:
                    self._capsule = memvid.create(self.capsule_path)
            except Exception as e:
                PrintStyle.error(f"Memvid init failed for {namespace}: {e}")

    def append(self, text: str, metadata: dict[str, Any] | None = None) -> bool:
        """Append a text frame to the capsule."""
        if not self._capsule:
            return False
        try:
            frame_meta = metadata or {}
            frame_meta["timestamp"] = time.time()
            self._capsule.append(text, metadata=frame_meta)
            self._capsule.save()
            return True
        except Exception as e:
            PrintStyle.error(f"Memvid append failed: {e}")
            return False

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search the capsule for matching frames."""
        if not self._capsule:
            return []
        try:
            results = self._capsule.search(query, top_k=limit)
            return [
                {"text": r.text, "score": r.score, "metadata": r.metadata}
                for r in results
            ]
        except Exception as e:
            PrintStyle.error(f"Memvid search failed: {e}")
            return []

    def count(self) -> int:
        """Return number of frames in capsule."""
        if not self._capsule:
            return 0
        try:
            return len(self._capsule)
        except Exception:
            return 0

    def to_dict(self) -> dict:
        return {
            "namespace": self.namespace,
            "capsule_path": self.capsule_path,
            "available": _MEMVID_AVAILABLE,
            "frame_count": self.count(),
        }
