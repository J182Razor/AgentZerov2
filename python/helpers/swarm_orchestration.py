"""
Swarm Orchestration Base Classes for Agent Zero

Provides base classes for multi-agent orchestration patterns including
sequential, parallel, and conditional workflows.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for an agent in a workflow."""
    name: str
    profile: str = ""
    prompt: str = ""
    timeout: float = 300.0  # 5 minutes default
    system_prompt: str = ""


@dataclass
class WorkflowStepResult:
    """Result from a single workflow step (agent execution)."""
    agent_name: str
    agent_number: int
    success: bool
    output: str
    error: Optional[str] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "agent_number": self.agent_number,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class WorkflowResult:
    """Complete result from a workflow execution."""
    workflow_id: str
    workflow_type: str
    status: WorkflowStatus
    steps: list[WorkflowStepResult]
    final_output: str
    total_duration_seconds: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "final_output": self.final_output,
            "total_duration_seconds": self.total_duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
        }


class BaseWorkflow(ABC):
    """Abstract base class for all workflow implementations."""

    def __init__(
        self,
        workflow_id: str,
        timeout: float = 600.0,
        fail_fast: bool = True,
    ):
        self.workflow_id = workflow_id
        self.timeout = timeout
        self.fail_fast = fail_fast
        self._status = WorkflowStatus.PENDING
        self._results: list[WorkflowStepResult] = []
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    @property
    def status(self) -> WorkflowStatus:
        return self._status

    @property
    def results(self) -> list[WorkflowStepResult]:
        return self._results

    @abstractmethod
    async def execute(self, initial_input: str, agents: list[Union[str, AgentConfig]]) -> WorkflowResult:
        """
        Execute the workflow with the given agents and initial input.

        Args:
            initial_input: The starting input/message for the workflow
            agents: List of agent names (str) or AgentConfig objects

        Returns:
            WorkflowResult containing all step results and final output
        """
        pass

    def _create_step_result(
        self,
        agent_name: str,
        agent_number: int,
        success: bool,
        output: str,
        error: Optional[str] = None,
    ) -> WorkflowStepResult:
        """Create a WorkflowStepResult with timing information."""
        now = datetime.now(timezone.utc)
        return WorkflowStepResult(
            agent_name=agent_name,
            agent_number=agent_number,
            success=success,
            output=output,
            error=error,
            start_time=self._start_time or now,
            end_time=now,
            duration_seconds=(now - (self._start_time or now)).total_seconds(),
        )

    def _create_workflow_result(
        self,
        status: WorkflowStatus,
        final_output: str,
        metadata: Optional[dict] = None,
    ) -> WorkflowResult:
        """Create a WorkflowResult with complete timing information."""
        self._end_time = datetime.now(timezone.utc)
        total_duration = (
            (self._end_time - self._start_time).total_seconds()
            if self._start_time else 0.0
        )

        return WorkflowResult(
            workflow_id=self.workflow_id,
            workflow_type=self.__class__.__name__,
            status=status,
            steps=self._results,
            final_output=final_output,
            total_duration_seconds=total_duration,
            start_time=self._start_time or datetime.now(timezone.utc),
            end_time=self._end_time,
            metadata=metadata or {},
        )


class WorkflowTimeoutError(Exception):
    """Raised when a workflow or step exceeds its timeout."""
    pass


class WorkflowExecutionError(Exception):
    """Raised when a workflow execution fails."""
    pass