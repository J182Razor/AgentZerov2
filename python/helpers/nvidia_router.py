"""
NVIDIA Multi-Model Router for Agent Zero
Provides dynamic role-to-model-to-apikey mapping with live reconfiguration.
"""
import json
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import os

NVIDIA_API_BASE = "https://integrate.api.nvidia.com/v1"

class NvidiaRole(str, Enum):
    CHAT = "chat"
    UTILITY = "utility"
    BROWSER = "browser"
    CODE = "code"
    REASONING = "reasoning"
    FAST = "fast"
    EMBEDDING = "embedding"

@dataclass
class NvidiaRoleConfig:
    role: NvidiaRole
    model: str
    api_key_env: str
    api_base: str = NVIDIA_API_BASE

NVIDIA_DEFAULTS: dict[NvidiaRole, NvidiaRoleConfig] = {
    NvidiaRole.CHAT:      NvidiaRoleConfig(NvidiaRole.CHAT,      "qwen/qwen3.5-397b-a17b",                 "NVIDIA_API_KEY_CHAT"),
    NvidiaRole.UTILITY:   NvidiaRoleConfig(NvidiaRole.UTILITY,   "minimaxai/minimax-m2.1",                 "NVIDIA_API_KEY_UTILITY"),
    NvidiaRole.BROWSER:   NvidiaRoleConfig(NvidiaRole.BROWSER,   "moonshotai/kimi-k2.5",                   "NVIDIA_API_KEY_BROWSER"),
    NvidiaRole.CODE:      NvidiaRoleConfig(NvidiaRole.CODE,      "mistralai/devstral-2-123b-instruct-2512","NVIDIA_API_KEY_CODE"),
    NvidiaRole.REASONING: NvidiaRoleConfig(NvidiaRole.REASONING, "z-ai/glm5",                              "NVIDIA_API_KEY_REASONING"),
    NvidiaRole.FAST:      NvidiaRoleConfig(NvidiaRole.FAST,      "stepfun-ai/step-3.5-flash",              "NVIDIA_API_KEY_FAST"),
    NvidiaRole.EMBEDDING: NvidiaRoleConfig(NvidiaRole.EMBEDDING, "nvidia/nv-embed-v2",                     "NVIDIA_API_KEY_EMBEDDING"),
}

KNOWN_NVIDIA_MODELS = [
    {"id": "qwen/qwen3.5-397b-a17b",                  "label": "Qwen 3.5 397B",             "roles": ["chat"]},
    {"id": "minimaxai/minimax-m2.1",                   "label": "MiniMax M2.1",               "roles": ["utility"]},
    {"id": "moonshotai/kimi-k2.5",                     "label": "Moonshot Kimi K2.5",         "roles": ["browser"]},
    {"id": "mistralai/devstral-2-123b-instruct-2512",  "label": "Devstral 2 123B",            "roles": ["code"]},
    {"id": "z-ai/glm5",                                "label": "Z.AI GLM5",                  "roles": ["reasoning", "chat"]},
    {"id": "stepfun-ai/step-3.5-flash",                "label": "StepFun Step 3.5 Flash",     "roles": ["fast"]},
    {"id": "nvidia/nv-embed-v2",                       "label": "NVIDIA NV-Embed v2",         "roles": ["embedding"]},
    {"id": "meta/llama-3.3-70b-instruct",              "label": "Llama 3.3 70B",              "roles": ["chat", "reasoning"]},
    {"id": "mistralai/mistral-7b-instruct-v0.3",       "label": "Mistral 7B Instruct v0.3",   "roles": ["fast", "utility"]},
    {"id": "nvidia/llama-3.2-11b-vision-instruct",     "label": "Llama 3.2 11B Vision",       "roles": ["browser"]},
    {"id": "nvidia/llama-3.2-90b-vision-instruct",     "label": "Llama 3.2 90B Vision",       "roles": ["browser"]},
    {"id": "nvidia/nemotron-4-340b-instruct",          "label": "Nemotron 4 340B",            "roles": ["reasoning"]},
    {"id": "nvidia/nemotron-mini-4b-instruct",         "label": "Nemotron Mini 4B",           "roles": ["fast", "utility"]},
]

class NvidiaRouter:
    _instance: Optional["NvidiaRouter"] = None
    _lock = threading.RLock()

    def __init__(self):
        self._roles: dict[NvidiaRole, NvidiaRoleConfig] = dict(NVIDIA_DEFAULTS)
        self._config_path = "/home/user/AgentZerov2/memory_config.json"

    @classmethod
    def instance(cls) -> "NvidiaRouter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance._load_from_config()
            return cls._instance

    def _load_from_config(self):
        try:
            with open(self._config_path) as f:
                cfg = json.load(f)
            roles_cfg = cfg.get("nvidia_roles", {})
            for role_str, data in roles_cfg.items():
                try:
                    role = NvidiaRole(role_str)
                    self._roles[role] = NvidiaRoleConfig(
                        role=role,
                        model=data.get("model", NVIDIA_DEFAULTS[role].model),
                        api_key_env=data.get("api_key_env", NVIDIA_DEFAULTS[role].api_key_env),
                    )
                except (ValueError, KeyError):
                    pass
        except Exception:
            pass  # Fall back to defaults

    def get_config(self, role: NvidiaRole) -> NvidiaRoleConfig:
        with self._lock:
            return self._roles.get(role, NVIDIA_DEFAULTS[role])

    def get_model(self, role: NvidiaRole) -> str:
        return self.get_config(role).model

    def get_api_key(self, role: NvidiaRole) -> str:
        cfg = self.get_config(role)
        # Try role-specific key first, then master NVIDIA key, then empty
        from python.helpers.dotenv import get_dotenv_value
        key = get_dotenv_value(cfg.api_key_env) or get_dotenv_value("NVIDIA_API_KEY") or ""
        return key

    def update_role(self, role: NvidiaRole, model: str, api_key_env: str):
        with self._lock:
            self._roles[role] = NvidiaRoleConfig(role=role, model=model, api_key_env=api_key_env)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                role.value: {
                    "model": cfg.model,
                    "api_key_env": cfg.api_key_env,
                    "api_base": cfg.api_base,
                }
                for role, cfg in self._roles.items()
            }

    def from_dict(self, data: dict):
        with self._lock:
            for role_str, cfg_data in data.items():
                try:
                    role = NvidiaRole(role_str)
                    self._roles[role] = NvidiaRoleConfig(
                        role=role,
                        model=cfg_data.get("model", ""),
                        api_key_env=cfg_data.get("api_key_env", ""),
                    )
                except ValueError:
                    pass

    def save_to_config(self):
        """Persist current assignments to memory_config.json."""
        try:
            with open(self._config_path) as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        cfg["nvidia_roles"] = {
            role.value: {"model": rc.model, "api_key_env": rc.api_key_env}
            for role, rc in self._roles.items()
        }
        with open(self._config_path, "w") as f:
            json.dump(cfg, f, indent=2)
