
"""
Profiling Decorators for Agent Zero
"""
import asyncio
import functools
import time
from typing import Callable, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class TimingStats:
    total_time: float = 0.0
    call_count: int = 0
    min_time: float = float('inf')
    max_time: float = 0.0

    def get_avg_time(self):
        return self.total_time / self.call_count if self.call_count > 0 else 0.0

class Profiler:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._stats = defaultdict(TimingStats)
            cls._instance._enabled = True
        return cls._instance

    def record(self, name, duration):
        if not self._enabled:
            return
        stats = self._stats[name]
        stats.total_time += duration
        stats.call_count += 1
        stats.min_time = min(stats.min_time, duration)
        stats.max_time = max(stats.max_time, duration)

    def get_stats(self, name):
        return self._stats.get(name)

    def get_all_stats(self):
        return dict(self._stats)

    def reset(self):
        self._stats = defaultdict(TimingStats)

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

def timed(func_or_name=None):
    """Decorator that records timing. Supports both @timed and @timed("name")."""
    def _make_wrapper(func, name):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                Profiler().record(name, duration)
        return wrapper

    if func_or_name is None:
        def decorator(func):
            return _make_wrapper(func, func.__name__)
        return decorator
    elif callable(func_or_name):
        return _make_wrapper(func_or_name, func_or_name.__name__)
    else:
        def decorator(func):
            return _make_wrapper(func, func_or_name)
        return decorator

def async_timed(func_or_name=None):
    """Async decorator that records timing. Supports both @async_timed and @async_timed("name")."""
    def _make_wrapper(func, name):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                Profiler().record(name, duration)
        return wrapper

    if func_or_name is None:
        def decorator(func):
            return _make_wrapper(func, func.__name__)
        return decorator
    elif callable(func_or_name):
        return _make_wrapper(func_or_name, func_or_name.__name__)
    else:
        def decorator(func):
            return _make_wrapper(func, func_or_name)
        return decorator
