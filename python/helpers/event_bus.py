"""Event Bus for Agent Zero"""
import asyncio
from enum import Enum, auto
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field

class EventType(Enum):
 AGENT_STARTED = auto()
 MONOLOGUE_START = auto()
 MONOLOGUE_END = auto()
 TOOL_CALLED = auto()
 TOOL_COMPLETED = auto()

@dataclass
class Event:
 type: EventType
 data: Dict[str, Any] = field(default_factory=dict)

class EventBus:
 _inst = None
 
 def __new__(cls):
 if cls._inst is None:
 cls._inst = super().__new__(cls)
 cls._inst._subs = {}
 return cls._inst
 
 def subscribe(self, et, handler, priority=100):
 if et not in self._subs:
 self._subs[et] = []
 self._subs[et].append({"h": handler, "p": priority})
 
 async def publish(self, et, data=None):
 ev = Event(type=et, data=data or {})
 for sub in self._subs.get(et, []):
 try:
 if asyncio.iscoroutinefunction(sub["h"]):
 await sub["h"](ev)
 else:
 sub["h"](ev)
 except Exception as e:
 print(f"Event err: {e}")
 return ev

_bus = EventBus()
get_event_bus = lambda: _bus
