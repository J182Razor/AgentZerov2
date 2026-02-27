"""
NVIDIA Multi-Model Ensemble Coordinator for Agent Zero
Coordinates diverse NVIDIA model perspectives for richer consensus.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any

try:
    from python.helpers.nvidia_router import NvidiaRouter, NvidiaRole
    _ROUTER_OK = True
except ImportError:
    _ROUTER_OK = False


@dataclass
class EnsembleMember:
    role: str
    model: str
    api_key: str
    weight: float = 1.0


@dataclass
class EnsembleResult:
    members: list[EnsembleMember]
    responses: list[str]
    synthesized: str
    model_diversity_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class NvidiaEnsemble:
    """
    Coordinates 3-agent ensemble calls across diverse NVIDIA models.
    Each agent uses a different model for maximum perspective diversity.
    """

    DEFAULT_ROLES = [NvidiaRole.REASONING, NvidiaRole.CHAT, NvidiaRole.FAST]

    def __init__(self, roles: list | None = None):
        self.roles = roles or (self.DEFAULT_ROLES if _ROUTER_OK else [])

    def get_members(self) -> list[EnsembleMember]:
        if not _ROUTER_OK:
            return []
        router = NvidiaRouter.instance()
        members = []
        for role in self.roles:
            members.append(EnsembleMember(
                role=role.value,
                model=router.get_model(role),
                api_key=router.get_api_key(role),
            ))
        return members

    async def call_member(
        self,
        member: EnsembleMember,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> str:
        """Call a single ensemble member and return its response text."""
        try:
            import litellm
            response = await litellm.acompletion(
                model=f"openai/{member.model}",
                messages=messages,
                max_tokens=max_tokens,
                api_key=member.api_key,
                api_base="https://integrate.api.nvidia.com/v1",
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[Error from {member.model}: {e}]"

    async def run(
        self,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> EnsembleResult:
        """Run all ensemble members in parallel and return their responses."""
        members = self.get_members()
        if not members:
            return EnsembleResult(members=[], responses=[], synthesized="")

        tasks = [self.call_member(m, messages, max_tokens) for m in members]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        clean_responses = [
            r if isinstance(r, str) else f"[Error: {r}]"
            for r in responses
        ]

        # Simple diversity score: ratio of unique non-error responses
        unique = len(set(r[:50] for r in clean_responses if not r.startswith("[Error")))
        diversity = unique / max(len(clean_responses), 1)

        # Synthesized = join with model labels for downstream processing
        synthesized_parts = [
            f"[{m.model}]: {r}"
            for m, r in zip(members, clean_responses)
        ]
        synthesized = "\n\n".join(synthesized_parts)

        return EnsembleResult(
            members=members,
            responses=clean_responses,
            synthesized=synthesized,
            model_diversity_score=diversity,
            metadata={"models": [m.model for m in members]},
        )
