"""Typed Extension Registry for Agent Zero"""
from enum import Enum, auto
from typing import Callable, Dict, List, Any
from dataclasses import dataclass

class ExtensionPoint(Enum):
 AGENT_INIT = auto()
 AGENT_START = auto()
 BEFORE_MONOLOGUE = auto()
 AFTER_MONOLOGUE = auto()
 BEFORE_TOOL = auto()
 AFTER_TOOL = auto()

@dataclass
class ExtensionMeta:
 name: str
 point: ExtensionPoint
 handler: Callable
 priority: int = 100

class ExtensionRegistry:
 _inst = None
 
 def __new__(cls):
 if cls._inst is None:
 cls._inst = super().__new__(cls)
 cls._inst._reg = {}
 return cls._inst
 
 def register(self, point, name, handler, priority=100):
 if point not in self._reg:
 self._reg[point] = []
 m = ExtensionMeta(name=name, point=point, handler=handler, priority=priority)
 self._reg[point].append(m)
 return m
 
 def get_handlers(self, point):
 return [x for x in self._reg.get(point, [])]

_reg = ExtensionRegistry()
