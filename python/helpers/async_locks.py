"""
Async Lock Primitives for Agent Zero
Replaces threading primitives with async-compatible versions
"""
import asyncio
from typing import Optional, Any
from contextlib import asynccontextmanager


class AsyncRLock:
 """Async-compatible reentrant lock"""
 
 def __init__(self):
 self._lock = asyncio.Lock()
 self._owner: Optional[int] = None
 self._count = 0
 
 async def acquire(self):
 """Acquire the lock"""
 current_task = id(asyncio.current_task())
 if self._owner == current_task:
 self._count += 1
 return True
 await self._lock.acquire()
 self._owner = current_task
 self._count = 1
 return True
 
 def release(self):
 """Release the lock"""
 current_task = id(asyncio.current_task())
 if self._owner != current_task:
 raise RuntimeError("Cannot release un-acquired lock")
 self._count -= 1
 if self._count == 0:
 self._owner = None
 self._lock.release()
 
 async def __aenter__(self):
 await self.acquire()
 return self
 
 async def __aexit__(self, exc_type, exc_val, exc_tb):
 self.release()
 return False


class AsyncContextManager:
 """Async context manager for AgentContext isolation"""
 
 def __init__(self):
 self._current_context: dict = {}
 
 async def get(self, key: str, default: Any = None) -> Any:
 return self._current_context.get(key, default)
 
 async def set(self, key: str, value: Any) -> None:
 self._current_context[key] = value
 
 async def delete(self, key: str) -> None:
 self._current_context.pop(key, None)


# Pre-compiled regex patterns
import re

PROMPT_PATTERNS = tuple(re.compile(p) for p in [
 r'\(venv\).+[$#] ?$',
 r'\([^)]+\)[^$#]*[$#] ?$',
 r'^\s*[$#]\s*$',
 r'^\s*>>>\s*$',
 r'^\s*\.\.\.\s*$',
])


def compile_patterns():
 """Return pre-compiled patterns"""
 return PROMPT_PATTERNS
