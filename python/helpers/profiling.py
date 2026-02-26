"""
Profiling Decorators for Agent Zero
Provides timing and performance measurement for hot paths
"""
import asyncio
import functools
import time
from typing import Callable, Any, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TimingStats:
 """Statistics for timed function calls"""
 total_time: float = 0.0
 call_count: int = 0
 min_time: float = float('inf')
 max_time: float = 0.0
 
 @property
 def avg_time(self) -> float:
 return self.total_time / self.call_count if self.call_count > 0 else 0.0


class Profiler:
 """Simple profiler for tracking function performance"""
 
 _instance = None
 
 def __new__(cls):
 if cls._instance is None:
 cls._instance = super().__new__(cls)
 cls._instance._stats = defaultdict(TimingStats)
 cls._instance._enabled = True
 return cls._instance
 
 def record(self, name: str, duration: float) -> None:
 """Record a timing"""
 if not self._enabled:
 return
 stats = self._stats[name]
 stats.total_time += duration
 stats.call_count += 1
 stats.min_time = min(stats.min_time, duration)
 stats.max_time = max(stats.max_time, duration)
 
 def get_stats(self, name: str) -> Optional[TimingStats]:
 """Get stats for a function"""
 return self._stats.get(name)
 
 def get_all_stats(self) -> dict:
 """Get all timing stats"""
 return dict(self._stats)
 
 def reset(self) -> None:
 """Reset all stats"""
 self._stats.clear()
 
 def enable(self, enabled: bool = True) -> None:
 """Enable or disable profiling"""
 self._enabled = enabled


def timed(name: Optional[str] = None):
 """
 Decorator to time function execution.
 
 Usage:
 @timed("my_function")
 def my_func(): ...
 
 @timed() # Uses function name
 async def my_async_func(): ...
 """
 def decorator(func: Callable) -> Callable:
 func_name = name or func.__name__
 profiler = Profiler()
 
 @functools.wraps(func)
 def sync_wrapper(*args, **kwargs) -> Any:
 start = time.perf_counter()
 try:
 return func(*args, **kwargs)
 finally:
 duration = time.perf_counter() - start
 profiler.record(func_name, duration)
 
 @functools.wraps(func)
 async def async_wrapper(*args, **kwargs) -> Any:
 start = time.perf_counter()
 try:
 return await func(*args, **kwargs)
 finally:
 duration = time.perf_counter() - start
 profiler.record(func_name, duration)
 
 if asyncio.iscoroutinefunction(func):
 return async_wrapper
 return sync_wrapper
 
 return decorator


def profile_context(name: str):
 """
 Context manager for timing code blocks.
 
 Usage:
 with profile_context("block_name"):
 # code to time
 """
 profiler = Profiler()
 
 class ProfileContext:
 def __enter__(self):
 self.start = time.perf_counter()
 return self
 
 def __exit__(self, *args):
 duration = time.perf_counter() - self.start
 profiler.record(name, duration)
 
 return ProfileContext()


# Convenience functions
_profiler = Profiler()


def get_profile_stats() -> dict:
 """Get all profiling statistics"""
 return _profiler.get_all_stats()


def reset_profile_stats() -> None:
 """Reset all profiling statistics"""
 _profiler.reset()


def enable_profiling(enabled: bool = True) -> None:
 """Enable or disable profiling"""
 _profiler.enable(enabled)
