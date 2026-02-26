"""Dependency Injection Container for Agent Zero"""
from typing import Any, Callable, Dict, Type, TypeVar
from enum import Enum, auto
import threading

T = TypeVar("T")

class Lifecycle(Enum):
 SINGLETON = auto()
 TRANSIENT = auto()

class Container:
 _inst = None
 _lock = threading.Lock()
 
 def __new__(cls):
 if cls._inst is None:
 with cls._lock:
 if cls._inst is None:
 cls._inst = super().__new__(cls)
 cls._inst._reg = {}
 cls._inst._singletons = {}
 return cls._inst
 
 def register(self, iface, impl, lc=None):
 self._reg[iface] = {"impl": impl, "lc": lc or Lifecycle.SINGLETON}
 
 def get(self, iface):
 d = self._reg[iface]
 if d["lc"] == Lifecycle.SINGLETON and iface in self._singletons:
 return self._singletons[iface]
 impl = d["impl"]
 inst = impl() if callable(impl) else impl
 if d["lc"] == Lifecycle.SINGLETON:
 self._singletons[iface] = inst
 return inst

_cont = Container()
get_container = lambda: _cont
inject = lambda iface: _cont.get(iface)
