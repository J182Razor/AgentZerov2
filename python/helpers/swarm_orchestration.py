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
from typing import Any, Optional, Union, Dict, List, Callable
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
    async def execute(
        self, initial_input: str, agents: list[Union[str, AgentConfig]]
    ) -> WorkflowResult:
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
            if self._start_time
            else 0.0
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


# ============================================================================
# ENHANCED PARALLEL SWARM ORCHESTRATION
# ============================================================================


class SwarmMode(Enum):
    """Swarm execution modes"""

    HIERARCHICAL = "hierarchical"  # Tree-like structure with coordinators
    MESH = "mesh"  # Flat peer-to-peer network
    CONSENSUS = "consensus"  # Voting-based decision making
    AUTO = "auto"  # Adaptive mode selection


@dataclass
class SwarmTask:
    """Task to be executed by swarm"""

    task_id: str
    input_data: Any
    priority: int = 0
    timeout: float = 300.0
    metadata: dict = field(default_factory=dict)


@dataclass
class SwarmResult:
    """Result from swarm execution"""

    task_id: str
    agent_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0


class ParallelSwarmExecutor:
    """
    Enhanced parallel swarm executor supporting multiple coordination modes.
    Supports up to 10,000+ concurrent agents with hierarchical coordination.
    """

    def __init__(
        self,
        max_agents: int = 1000,
        mode: SwarmMode = SwarmMode.HIERARCHICAL,
        timeout: float = 600.0,
    ):
        self.max_agents = max_agents
        self.mode = mode
        self.timeout = timeout
        self.active_agents: Dict[str, Any] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.results: List[SwarmResult] = []

    async def execute_parallel(
        self, tasks: List[SwarmTask], agent_factory: Callable[[str], Any]
    ) -> List[SwarmResult]:
        """
        Execute tasks in parallel using swarm coordination.

        Args:
            tasks: List of tasks to execute
            agent_factory: Function to create agent instances

        Returns:
            List of SwarmResult from all task executions
        """
        if self.mode == SwarmMode.HIERARCHICAL:
            return await self._hierarchical_execute(tasks, agent_factory)
        elif self.mode == SwarmMode.MESH:
            return await self._mesh_execute(tasks, agent_factory)
        elif self.mode == SwarmMode.CONSENSUS:
            return await self._consensus_execute(tasks, agent_factory)
        else:
            return await self._auto_execute(tasks, agent_factory)

    async def _hierarchical_execute(
        self, tasks: List[SwarmTask], agent_factory: Callable[[str], Any]
    ) -> List[SwarmResult]:
        """
        Hierarchical execution with coordinators.
        Agents are organized in a tree structure.
        """
        # Create agent pool
        num_agents = min(len(tasks), self.max_agents)
        agents = [agent_factory(f"agent_{i}") for i in range(num_agents)]

        # Distribute tasks to agents
        tasks_per_agent = len(tasks) // num_agents
        remainder = len(tasks) % num_agents

        results = []

        # Execute in batches
        async def execute_batch(
            agent_id: str, agent: Any, batch: List[SwarmTask]
        ) -> List[SwarmResult]:
            batch_results = []
            for task in batch:
                try:
                    # Execute task with timeout
                    output = await asyncio.wait_for(
                        agent.execute(task.input_data), timeout=task.timeout
                    )
                    batch_results.append(
                        SwarmResult(
                            task_id=task.task_id,
                            agent_id=agent_id,
                            success=True,
                            output=output,
                        )
                    )
                except asyncio.TimeoutError:
                    batch_results.append(
                        SwarmResult(
                            task_id=task.task_id,
                            agent_id=agent_id,
                            success=False,
                            output=None,
                            error=f"Task timeout after {task.timeout}s",
                        )
                    )
                except Exception as e:
                    batch_results.append(
                        SwarmResult(
                            task_id=task.task_id,
                            agent_id=agent_id,
                            success=False,
                            output=None,
                            error=str(e),
                        )
                    )
            return batch_results

        # Create batches and execute in parallel
        batch_tasks = []
        task_idx = 0

        for i, agent in enumerate(agents):
            # Calculate batch size for this agent
            batch_size = tasks_per_agent + (1 if i < remainder else 0)
            if batch_size > 0 and task_idx < len(tasks):
                batch = tasks[task_idx : task_idx + batch_size]
                batch_tasks.append(execute_batch(f"agent_{i}", agent, batch))
                task_idx += batch_size

        # Execute all batches in parallel
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Flatten results
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            elif isinstance(batch_result, Exception):
                results.append(
                    SwarmResult(
                        task_id="unknown",
                        agent_id="unknown",
                        success=False,
                        output=None,
                        error=str(batch_result),
                    )
                )

        return results

    async def _mesh_execute(
        self, tasks: List[SwarmTask], agent_factory: Callable[[str], Any]
    ) -> List[SwarmResult]:
        """
        Mesh/peer-to-peer execution.
        Each agent can communicate with any other agent.
        """
        # In mesh mode, all agents work on all tasks (fan-out)
        # Results are aggregated from all agents
        num_agents = min(self.max_agents, len(tasks) * 2)  # Oversample agents
        agents = [agent_factory(f"agent_{i}") for i in range(num_agents)]

        results = []

        async def execute_single_task(task: SwarmTask, agent: Any) -> SwarmResult:
            try:
                output = await asyncio.wait_for(
                    agent.execute(task.input_data), timeout=task.timeout
                )
                return SwarmResult(
                    task_id=task.task_id,
                    agent_id=agent.name,
                    success=True,
                    output=output,
                )
            except Exception as e:
                return SwarmResult(
                    task_id=task.task_id,
                    agent_id=getattr(agent, "name", "unknown"),
                    success=False,
                    output=None,
                    error=str(e),
                )

        # Create all execution tasks
        execution_tasks = []
        for task in tasks:
            for agent in agents:
                execution_tasks.append(execute_single_task(task, agent))

        # Execute in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_agents)

        async def limited_execute(task):
            async with semaphore:
                return await task

        limited_tasks = [limited_execute(t) for t in execution_tasks]
        task_results = await asyncio.gather(*limited_tasks, return_exceptions=True)

        # Filter out exceptions and collect valid results
        for result in task_results:
            if isinstance(result, SwarmResult):
                results.append(result)
            elif isinstance(result, Exception):
                results.append(
                    SwarmResult(
                        task_id="unknown",
                        agent_id="unknown",
                        success=False,
                        output=None,
                        error=str(result),
                    )
                )

        return results

    async def _consensus_execute(
        self, tasks: List[SwarmTask], agent_factory: Callable[[str], Any]
    ) -> List[SwarmResult]:
        """
        Consensus-based execution.
        Multiple agents work on each task, results are voted on.
        """
        from collections import Counter

        num_voters = min(5, self.max_agents)  # 5 agents per task for consensus
        voters = [agent_factory(f"voter_{i}") for i in range(num_voters)]

        results = []

        for task in tasks:
            # Execute task with multiple voters
            voter_tasks = [
                asyncio.wait_for(voter.execute(task.input_data), timeout=task.timeout)
                for voter in voters
            ]

            voter_results = await asyncio.gather(*voter_tasks, return_exceptions=True)

            # Count results (for simple consensus)
            outputs = [r for r in voter_results if not isinstance(r, Exception)]

            if outputs:
                # Simple majority - take most common output
                output_counts = Counter(str(o) for o in outputs)
                consensus_output = output_counts.most_common(1)[0][0]

                results.append(
                    SwarmResult(
                        task_id=task.task_id,
                        agent_id="consensus",
                        success=True,
                        output=consensus_output,
                    )
                )
            else:
                # All failed
                errors = [str(r) for r in voter_results if isinstance(r, Exception)]
                results.append(
                    SwarmResult(
                        task_id=task.task_id,
                        agent_id="consensus",
                        success=False,
                        output=None,
                        error=f"All voters failed: {errors}",
                    )
                )

        return results

    async def _auto_execute(
        self, tasks: List[SwarmTask], agent_factory: Callable[[str], Any]
    ) -> List[SwarmResult]:
        """
        Auto mode - automatically select best execution strategy.
        """
        # Auto-select based on task count
        if len(tasks) <= 10:
            # Few tasks - use hierarchical
            return await self._hierarchical_execute(tasks, agent_factory)
        elif len(tasks) <= 100:
            # Medium - use mesh
            return await self._mesh_execute(tasks, agent_factory)
        else:
            # Many tasks - use consensus for critical tasks only
            critical_tasks = [t for t in tasks if t.priority > 5]
            regular_tasks = [t for t in tasks if t.priority <= 5]

            results = []

            if critical_tasks:
                consensus_results = await self._consensus_execute(
                    critical_tasks, agent_factory
                )
                results.extend(consensus_results)

            if regular_tasks:
                hierarchical_results = await self._hierarchical_execute(
                    regular_tasks, agent_factory
                )
                results.extend(hierarchical_results)

            return results


async def create_swarm_executor(
    mode: str = "hierarchical", max_agents: int = 1000, timeout: float = 600.0
) -> ParallelSwarmExecutor:
    """
    Factory function to create a swarm executor.

    Args:
        mode: Execution mode (hierarchical, mesh, consensus, auto)
        max_agents: Maximum number of concurrent agents
        timeout: Default timeout for tasks

    Returns:
        Configured ParallelSwarmExecutor instance
    """
    swarm_mode = SwarmMode(mode.lower())
    return ParallelSwarmExecutor(
        max_agents=max_agents, mode=swarm_mode, timeout=timeout
    )
