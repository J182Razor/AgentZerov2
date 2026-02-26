"""
Tool Cache System for Agent Zero
Provides LRU caching with TTL for tool class resolution
Target: <1ms tool lookup (was 50-200ms)
"""
import asyncio
import functools
import time
from typing import Type, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
import threading


@dataclass
class CacheEntry:
 """Cached tool entry"""
 tool_class: Type
 cached_at: float
 ttl: float
 access_count: int = 0


class ToolCache:
 """
 LRU cache for tool class resolution with TTL support.
 Eliminates filesystem scanning and module import overhead on every tool call.
 """
 
 _instance = None
 _lock = threading.Lock()
 
 def __new__(cls, *args, **kwargs):
 if cls._instance is None:
 with cls._lock:
 if cls._instance is None:
 cls._instance = super().__new__(cls)
 cls._instance._initialized = False
 return cls._instance
 
 def __init__(self, max_size: int = 256, default_ttl: float = 3600.0):
 if self._initialized:
 return
 
 self._cache: Dict[str, CacheEntry] = {}
 self._max_size = max_size
 self._default_ttl = default_ttl
 self._access_order: list = []
 self._hits = 0
 self._misses = 0
 self._initialized = True
 
 def get(self, tool_name: str) -> Optional[Type]:
 """Get cached tool class by name"""
 if tool_name not in self._cache:
 self._misses += 1
 return None
 
 entry = self._cache[tool_name]
 
 # Check TTL
 if time.time() - entry.cached_at > entry.ttl:
 self._evict(tool_name)
 self._misses += 1
 return None
 
 # Update access tracking
 entry.access_count += 1
 self._hits += 1
 
 # Move to end of access order (most recently used)
 if tool_name in self._access_order:
 self._access_order.remove(tool_name)
 self._access_order.append(tool_name)
 
 return entry.tool_class
 
 def set(self, tool_name: str, tool_class: Type, ttl: Optional[float] = None) -> None:
 """Cache a tool class"""
 # Evict LRU if at capacity
 while len(self._cache) >= self._max_size and self._access_order:
 lru_tool = self._access_order.pop(0)
 self._evict(lru_tool)
 
 self._cache[tool_name] = CacheEntry(
 tool_class=tool_class,
 cached_at=time.time(),
 ttl=ttl or self._default_ttl
 )
 self._access_order.append(tool_name)
 
 def _evict(self, tool_name: str) -> None:
 """Remove entry from cache"""
 if tool_name in self._cache:
 del self._cache[tool_name]
 if tool_name in self._access_order:
 self._access_order.remove(tool_name)
 
 def clear(self) -> None:
 """Clear all cached entries"""
 self._cache.clear()
 self._access_order.clear()
 self._hits = 0
 self._misses = 0
 
 def stats(self) -> Dict[str, Any]:
 """Get cache statistics"""
 total = self._hits + self._misses
 hit_rate = self._hits / total if total > 0 else 0
 return {
 "size": len(self._cache),
 "max_size": self._max_size,
 "hits": self._hits,
 "misses": self._misses,
 "hit_rate": f"{hit_rate:.2%}",
 }


# Global cache instance
_tool_cache = ToolCache()


def get_cached_tool(tool_name: str) -> Optional[Type]:
 """Get tool class from cache"""
 return _tool_cache.get(tool_name)


def cache_tool(tool_name: str, tool_class: Type, ttl: Optional[float] = None) -> None:
 """Cache a tool class"""
 _tool_cache.set(tool_name, tool_class, ttl)


def clear_tool_cache() -> None:
 """Clear the tool cache"""
 _tool_cache.clear()


def tool_cache_stats() -> Dict[str, Any]:
 """Get tool cache statistics"""
 return _tool_cache.stats()


# Decorator for caching tool lookups
def cached_tool_lookup(func: Callable) -> Callable:
 """Decorator to cache tool lookup results"""
 @functools.wraps(func)
 def wrapper(tool_name: str, *args, **kwargs):
 cached = get_cached_tool(tool_name)
 if cached is not None:
 return cached
 
 result = func(tool_name, *args, **kwargs)
 if result is not None:
 cache_tool(tool_name, result)
 return result
 return wrapper
