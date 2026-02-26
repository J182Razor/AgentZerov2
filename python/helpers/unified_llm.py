"""Unified LLM Class for Agent Zero"""
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import time
import threading

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class CircuitBreaker:
    def __init__(self, threshold=5, timeout=60.0):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_fail = 0
        self.lock = threading.Lock()
    
    def record_success(self):
        with self.lock:
            self.failures = 0
    
    def record_failure(self):
        with self.lock:
            self.failures += 1
            self.last_fail = time.time()
    
    def can_execute(self):
        with self.lock:
            if self.failures < self.threshold:
                return True
            if time.time() - self.last_fail > self.timeout:
                self.failures = 0
                return True
            return False

@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0

class UnifiedLLM:
    def __init__(self, config):
        self.config = config
        self.circuit = CircuitBreaker()
        self.client = None
    
    async def complete(self, messages, **kw):
        if not self.circuit.can_execute():
            raise Exception("Circuit open")
        import openai
        if not self.client:
            self.client = openai.AsyncOpenAI(api_key=self.config.api_key)
        start = time.perf_counter()
        r = await self.client.chat.completions.create(
            model=kw.get("model", self.config.model),
            messages=messages,
            max_tokens=kw.get("max_tokens", self.config.max_tokens),
            temperature=kw.get("temperature", self.config.temperature))
        self.circuit.record_success()
        return LLMResponse(
            content=r.choices[0].message.content,
            model=r.model,
            usage={"total": r.usage.total_tokens},
            latency_ms=(time.perf_counter()-start)*1000)
