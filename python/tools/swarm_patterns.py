"""
Swarm Patterns for Agent Zero

Implements advanced multi-agent coordination patterns including StarSwarm
for hub-and-spoke orchestration where a central coordinator manages
parallel worker agents.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union, List, Dict

from agent import Agent, UserMessage
from python.helpers.tool import Tool, Response
from python.helpers.swarm_orchestration import (
    AgentConfig,
    BaseWorkflow,
    WorkflowResult,
    WorkflowStepResult,
    WorkflowStatus,
    WorkflowTimeoutError,
    WorkflowExecutionError,
)
from initialize import initialize_agent

logger = logging.getLogger(__name__)


# Default prompts for StarSwarm
DEFAULT_DECOMPOSITION_PROMPT = """You are a task decomposition specialist. Your job is to break down a complex task into independent subtasks that can be executed in parallel by specialized agents.

Given the main task, create {num_spokes} distinct subtasks. Each subtask should:
1. Be self-contained and executable independently
2. Have a clear objective and expected output
3. Contribute to solving the main task
4. Be assigned to a specific agent role

Format your response as:
---SUBTASK 1---
Role: [agent role/specialty]
Objective: [what this agent should accomplish]
Instructions: [specific instructions for this agent]
---SUBTASK 2---
...

Main Task:
{task}"""

DEFAULT_AGGREGATION_PROMPT = """You are a result synthesis specialist. Your job is to combine the outputs from multiple agents into a coherent, comprehensive final answer.

The original task was:
{original_task}

Agent Results:
{agent_results}

Synthesize these results into a unified response that:
1. Combines key insights from all agents
2. Resolves any contradictions or conflicts
3. Provides a complete answer to the original task
4. Highlights the most important findings

Provide your synthesized response:"""


class StarSwarmPhase(Enum):
    """Phases of StarSwarm execution."""
    DECOMPOSITION = "decomposition"
    EXECUTION = "execution"
    AGGREGATION = "aggregation"


@dataclass
class Subtask:
    """A decomposed subtask for a spoke agent."""
    index: int
    role: str
    objective: str
    instructions: str
    raw_content: str = ""

    def to_prompt(self) -> str:
        """Convert subtask to a prompt for the spoke agent."""
        return f"""You are a {self.role}.

Objective: {self.objective}

Instructions:
{self.instructions}

Please complete your assigned task and provide your results."""


@dataclass
class StarSwarmResult:
    """Complete result from a StarSwarm execution."""
    workflow_id: str
    status: WorkflowStatus
    hub_result: Optional[WorkflowStepResult]
    spoke_results: list[WorkflowStepResult]
    aggregation_result: Optional[WorkflowStepResult]
    final_output: str
    subtasks: list[Subtask]
    total_duration_seconds: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "hub_result": self.hub_result.to_dict() if self.hub_result else None,
            "spoke_results": [r.to_dict() for r in self.spoke_results],
            "aggregation_result": self.aggregation_result.to_dict() if self.aggregation_result else None,
            "final_output": self.final_output,
            "subtasks": [
                {"index": s.index, "role": s.role, "objective": s.objective}
                for s in self.subtasks
            ],
            "total_duration_seconds": self.total_duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
        }


class StarSwarm(BaseWorkflow):
    """
    Hub-and-spoke coordination pattern.
    
    A central hub agent decomposes tasks into subtasks for spoke agents,
    which execute in parallel. The hub then aggregates all results.
    """

    def __init__(
        self,
        parent_agent: Agent,
        workflow_id: str = "",
        timeout: float = 900.0,  # Longer default for 3 phases
        hub_timeout: float = 300.0,
        spoke_timeout: float = 300.0,
        decomposition_prompt: str = "",
        aggregation_prompt: str = "",
        max_concurrency: int = 10,
    ):
        super().__init__(
            workflow_id=workflow_id or f"star_{uuid.uuid4().hex[:8]}",
            timeout=timeout,
            fail_fast=False,
        )
        self.parent_agent = parent_agent
        self.hub_timeout = hub_timeout
        self.spoke_timeout = spoke_timeout
        self.decomposition_prompt = decomposition_prompt or DEFAULT_DECOMPOSITION_PROMPT
        self.aggregation_prompt = aggregation_prompt or DEFAULT_AGGREGATION_PROMPT
        self.max_concurrency = max_concurrency
        self._hub_agent: Optional[Agent] = None
        self._spoke_agents: list[Agent] = []
        self._subtasks: list[Subtask] = []

    def _parse_agent_config(self, agent_spec) -> AgentConfig:
        """Parse agent specification into AgentConfig."""
        if isinstance(agent_spec, AgentConfig):
            return agent_spec
        if isinstance(agent_spec, dict):
            return AgentConfig(
                name=agent_spec.get("name", ""),
                profile=agent_spec.get("profile", ""),
                prompt=agent_spec.get("prompt", ""),
                timeout=agent_spec.get("timeout", self.spoke_timeout),
                system_prompt=agent_spec.get("system_prompt", ""),
            )
        if isinstance(agent_spec, str):
            return AgentConfig(name=agent_spec, timeout=self.spoke_timeout)
        raise ValueError(f"Invalid agent specification: {type(agent_spec)}")

    async def _create_agent(
        self,
        config: AgentConfig,
        agent_number: int,
        is_hub: bool = False,
    ) -> Agent:
        """Create a subordinate agent with the given configuration."""
        base_config = initialize_agent()
        if config.profile:
            base_config.profile = config.profile

        agent = Agent(
            number=self.parent_agent.number + agent_number,
            config=base_config,
            context=self.parent_agent.context,
        )
        agent.set_data("_workflow_id", self.workflow_id)
        agent.set_data("_workflow_step", agent_number)
        agent.set_data(Agent.DATA_NAME_SUPERIOR, self.parent_agent)
        agent.set_data("_is_hub", is_hub)
        return agent

    async def _execute_agent(
        self,
        agent: Agent,
        input_message: str,
        timeout: float,
    ) -> WorkflowStepResult:
        """Execute a single agent and return its result."""
        step_start = datetime.now(timezone.utc)
        try:
            agent.hist_add_user_message(UserMessage(message=input_message, attachments=[]))

            async def run_agent():
                return await agent.monologue()

            try:
                result = await asyncio.wait_for(run_agent(), timeout=timeout)
            except asyncio.TimeoutError:
                raise WorkflowTimeoutError(
                    f"Agent {agent.agent_name} exceeded timeout of {timeout}s"
                )

            agent.history.new_topic()
            step_end = datetime.now(timezone.utc)
            duration = (step_end - step_start).total_seconds()

            return WorkflowStepResult(
                agent_name=agent.agent_name,
                agent_number=agent.number,
                success=True,
                output=result,
                error=None,
                start_time=step_start,
                end_time=step_end,
                duration_seconds=duration,
            )

        except WorkflowTimeoutError as e:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(
                agent_name=agent.agent_name,
                agent_number=agent.number,
                success=False,
                output="",
                error=str(e),
                start_time=step_start,
                end_time=step_end,
                duration_seconds=(step_end - step_start).total_seconds(),
            )

        except Exception as e:
            step_end = datetime.now(timezone.utc)
            logger.exception(f"Error in StarSwarm agent {agent.agent_name}")
            return WorkflowStepResult(
                agent_name=agent.agent_name,
                agent_number=agent.number,
                success=False,
                output="",
                error=f"{type(e).__name__}: {str(e)}",
                start_time=step_start,
                end_time=step_end,
                duration_seconds=(step_end - step_start).total_seconds(),
            )

    def _parse_subtasks(self, decomposition_output: str, num_expected: int) -> list[Subtask]:
        """Parse decomposition output into subtasks."""
        import re

        subtasks = []

        # Try to parse structured format
        pattern = r"---SUBTASK\s*(\d+)---\s*(.*?)(?=---SUBTASK\s*\d+---|$)"
        matches = re.findall(pattern, decomposition_output, re.DOTALL | re.IGNORECASE)

        for match in matches:
            index = int(match[0])
            content = match[1].strip()

            # Extract role
            role_match = re.search(r"Role:\s*(.+?)(?=\n|$)", content, re.IGNORECASE)
            role = role_match.group(1).strip() if role_match else f"Agent {index}"

            # Extract objective
            obj_match = re.search(r"Objective:\s*(.+?)(?=\n\w+:|$)", content, re.DOTALL | re.IGNORECASE)
            objective = obj_match.group(1).strip() if obj_match else "Complete assigned task"

            # Extract instructions
            instr_match = re.search(r"Instructions:\s*(.+?)$", content, re.DOTALL | re.IGNORECASE)
            instructions = instr_match.group(1).strip() if instr_match else content

            subtasks.append(Subtask(
                index=index,
                role=role,
                objective=objective,
                instructions=instructions,
                raw_content=content,
            ))

        # If parsing failed, create generic subtasks
        if not subtasks:
            for i in range(num_expected):
                subtasks.append(Subtask(
                    index=i + 1,
                    role=f"Agent {i + 1}",
                    objective=f"Complete subtask {i + 1}",
                    instructions=f"Process your assigned portion of the task.",
                    raw_content="",
                ))

        return subtasks

    async def _decompose_task(
        self,
        task: str,
        num_spokes: int,
        hub_agent: Agent,
    ) -> tuple[list[Subtask], WorkflowStepResult]:
        """Use hub agent to decompose task into subtasks."""
        decomposition_input = self.decomposition_prompt.format(
            num_spokes=num_spokes,
            task=task,
        )

        result = await self._execute_agent(
            hub_agent,
            decomposition_input,
            self.hub_timeout,
        )

        if result.success:
            subtasks = self._parse_subtasks(result.output, num_spokes)
        else:
            # Create fallback subtasks on failure
            subtasks = [
                Subtask(
                    index=i + 1,
                    role=f"Agent {i + 1}",
                    objective=f"Complete part {i + 1} of the task",
                    instructions=task,
                    raw_content="",
                )
                for i in range(num_spokes)
            ]

        return subtasks, result

    async def _execute_spokes(
        self,
        subtasks: list[Subtask],
        spoke_agents: list[Agent],
        spoke_configs: list[AgentConfig],
    ) -> list[WorkflowStepResult]:
        """Execute all spoke agents in parallel."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute_spoke(
            agent: Agent,
            subtask: Subtask,
            config: AgentConfig,
            idx: int,
        ) -> WorkflowStepResult:
            async with semaphore:
                logger.info(
                    f"StarSwarm {self.workflow_id}: "
                    f"Starting spoke {idx + 1} ({subtask.role})"
                )
                prompt = subtask.to_prompt()
                if config.prompt:
                    prompt = f"{config.prompt}\n\n---\n{prompt}"
                return await self._execute_agent(agent, prompt, config.timeout)

        # Match subtasks to agents (may have fewer agents than subtasks)
        tasks = []
        for i, (agent, config) in enumerate(zip(spoke_agents, spoke_configs)):
            subtask_idx = i % len(subtasks)
            tasks.append(
                execute_spoke(agent, subtasks[subtask_idx], config, i)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        step_results = []
        for result in results:
            if isinstance(result, Exception):
                step_results.append(WorkflowStepResult(
                    agent_name="unknown",
                    agent_number=0,
                    success=False,
                    output="",
                    error=f"{type(result).__name__}: {str(result)}",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    duration_seconds=0.0,
                ))
            elif isinstance(result, WorkflowStepResult):
                step_results.append(result)

        return step_results

    async def _aggregate_results(
        self,
        original_task: str,
        spoke_results: list[WorkflowStepResult],
        hub_agent: Agent,
    ) -> WorkflowStepResult:
        """Use hub agent to aggregate spoke results."""
        # Build agent results summary
        successful_results = [r for r in spoke_results if r.success]

        if not successful_results:
            return WorkflowStepResult(
                agent_name=hub_agent.agent_name,
                agent_number=hub_agent.number,
                success=False,
                output="",
                error="All spoke agents failed to produce results",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=0.0,
            )

        agent_results = "\n\n".join([
            f"--- RESULT FROM {r.agent_name} ---\n{r.output}"
            for r in successful_results
        ])

        aggregation_input = self.aggregation_prompt.format(
            original_task=original_task,
            agent_results=agent_results,
        )

        return await self._execute_agent(
            hub_agent,
            aggregation_input,
            self.hub_timeout,
        )

    async def execute(
        self,
        initial_input: str,
        agents: list,
    ) -> StarSwarmResult:
        """
        Execute the StarSwarm pattern.
        
        Args:
            initial_input: The main task to be decomposed and distributed
            agents: List of spoke agent specifications
            
        Returns:
            StarSwarmResult with all phase results
        """
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._results = []
        self._spoke_agents = []
        self._subtasks = []

        hub_result = None
        spoke_results = []
        aggregation_result = None
        final_output = ""

        try:
            # Parse spoke agent configurations
            spoke_configs = [self._parse_agent_config(spec) for spec in agents]
            num_spokes = len(spoke_configs)

            logger.info(
                f"StarSwarm {self.workflow_id}: "
                f"Starting with {num_spokes} spoke agents"
            )

            # Create hub agent (using parent agent's configuration as base)
            hub_config = AgentConfig(
                name="hub_coordinator",
                profile="",
                timeout=self.hub_timeout,
            )
            self._hub_agent = await self._create_agent(hub_config, 1, is_hub=True)

            # Phase 1: Decomposition
            logger.info(f"StarSwarm {self.workflow_id}: Phase 1 - Decomposition")
            self._subtasks, hub_result = await self._decompose_task(
                initial_input,
                num_spokes,
                self._hub_agent,
            )

            if not self._subtasks:
                return StarSwarmResult(
                    workflow_id=self.workflow_id,
                    status=WorkflowStatus.FAILED,
                    hub_result=hub_result,
                    spoke_results=[],
                    aggregation_result=None,
                    final_output="",
                    subtasks=[],
                    total_duration_seconds=(
                        datetime.now(timezone.utc) - self._start_time
                    ).total_seconds(),
                    start_time=self._start_time,
                    end_time=datetime.now(timezone.utc),
                    metadata={"error": "Task decomposition failed"},
                )

            # Create spoke agents
            for idx, config in enumerate(spoke_configs):
                agent = await self._create_agent(config, idx + 2)  # +2 because hub is 1
                self._spoke_agents.append(agent)

            # Phase 2: Parallel Execution
            logger.info(f"StarSwarm {self.workflow_id}: Phase 2 - Parallel Execution")
            spoke_results = await self._execute_spokes(
                self._subtasks,
                self._spoke_agents,
                spoke_configs,
            )

            # Phase 3: Aggregation
            logger.info(f"StarSwarm {self.workflow_id}: Phase 3 - Aggregation")
            aggregation_result = await self._aggregate_results(
                initial_input,
                spoke_results,
                self._hub_agent,
            )

            if aggregation_result.success:
                final_output = aggregation_result.output
                status = WorkflowStatus.COMPLETED
            else:
                # Fallback: concatenate successful spoke results
                successful = [r for r in spoke_results if r.success]
                if successful:
                    final_output = "\n\n---\n\n".join([r.output for r in successful])
                    status = WorkflowStatus.COMPLETED
                else:
                    final_output = "All phases failed to produce results"
                    status = WorkflowStatus.FAILED

            self._end_time = datetime.now(timezone.utc)
            total_duration = (self._end_time - self._start_time).total_seconds()

            return StarSwarmResult(
                workflow_id=self.workflow_id,
                status=status,
                hub_result=hub_result,
                spoke_results=spoke_results,
                aggregation_result=aggregation_result,
                final_output=final_output,
                subtasks=self._subtasks,
                total_duration_seconds=total_duration,
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={
                    "num_spokes": num_spokes,
                    "successful_spokes": len([r for r in spoke_results if r.success]),
                    "failed_spokes": len([r for r in spoke_results if not r.success]),
                    "decomposition_success": hub_result.success if hub_result else False,
                    "aggregation_success": aggregation_result.success if aggregation_result else False,
                },
            )

        except asyncio.TimeoutError:
            self._end_time = datetime.now(timezone.utc)
            return StarSwarmResult(
                workflow_id=self.workflow_id,
                status=WorkflowStatus.TIMEOUT,
                hub_result=hub_result,
                spoke_results=spoke_results,
                aggregation_result=aggregation_result,
                final_output=f"Workflow exceeded timeout of {self.timeout}s",
                subtasks=self._subtasks,
                total_duration_seconds=(
                    self._end_time - self._start_time
                ).total_seconds(),
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={"error": "Timeout"},
            )

        except Exception as e:
            logger.exception(f"StarSwarm {self.workflow_id} failed")
            self._end_time = datetime.now(timezone.utc)
            return StarSwarmResult(
                workflow_id=self.workflow_id,
                status=WorkflowStatus.FAILED,
                hub_result=hub_result,
                spoke_results=spoke_results,
                aggregation_result=aggregation_result,
                final_output="",
                subtasks=self._subtasks,
                total_duration_seconds=(
                    self._end_time - self._start_time
                ).total_seconds(),
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={"error": str(e)},
            )


class swarm_star(Tool):
    """Tool for executing StarSwarm hub-and-spoke coordination pattern."""

    async def execute(
        self,
        agents="",
        task="",
        workflow_id="",
        timeout="900",
        hub_timeout="300",
        spoke_timeout="300",
        decomposition_prompt="",
        aggregation_prompt="",
        max_concurrency="10",
        **kwargs,
    ):
        """
        Execute StarSwarm pattern.

        Args:
            agents: Comma-separated agent names or JSON array of spoke agent configs
            task: The main task to decompose and distribute
            workflow_id: Optional workflow identifier
            timeout: Total workflow timeout in seconds
            hub_timeout: Hub agent timeout for decomposition/aggregation
            spoke_timeout: Individual spoke agent timeout
            decomposition_prompt: Custom prompt for task decomposition
            aggregation_prompt: Custom prompt for result aggregation
            max_concurrency: Maximum concurrent spoke executions
        """
        import json

        try:
            # Parse agents
            agent_list = self._parse_agents_param(agents)
            if not agent_list:
                return Response(
                    message="Error: No spoke agents specified for StarSwarm",
                    break_loop=False,
                )

            if len(agent_list) < 2:
                return Response(
                    message="Error: At least 2 spoke agents recommended for StarSwarm",
                    break_loop=False,
                )

            # Parse numeric values
            try:
                timeout_val = float(timeout)
                hub_timeout_val = float(hub_timeout)
                spoke_timeout_val = float(spoke_timeout)
                max_concurrency_val = int(max_concurrency)
            except ValueError:
                return Response(
                    message="Error: Invalid numeric parameters",
                    break_loop=False,
                )

            # Create StarSwarm workflow
            workflow = StarSwarm(
                parent_agent=self.agent,
                workflow_id=workflow_id,
                timeout=timeout_val,
                hub_timeout=hub_timeout_val,
                spoke_timeout=spoke_timeout_val,
                decomposition_prompt=decomposition_prompt or DEFAULT_DECOMPOSITION_PROMPT,
                aggregation_prompt=aggregation_prompt or DEFAULT_AGGREGATION_PROMPT,
                max_concurrency=max_concurrency_val,
            )

            # Execute
            task_msg = task or self.message or "Complete this task using hub-and-spoke coordination."
            result = await workflow.execute(initial_input=task_msg, agents=agent_list)

            # Format response
            response_text = self._format_result(result)
            return Response(
                message=response_text,
                break_loop=False,
                additional={
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "num_spokes": len(result.spoke_results),
                    "successful_spokes": result.metadata.get("successful_spokes", 0),
                },
            )

        except Exception as e:
            logger.exception("StarSwarm execution failed")
            return Response(
                message=f"StarSwarm failed: {type(e).__name__}: {str(e)}",
                break_loop=False,
            )

    def _parse_agents_param(self, agents: str) -> list:
        """Parse agents parameter from string or JSON."""
        import json
        if not agents:
            return []
        agents = agents.strip()
        if agents.startswith("["):
            try:
                return json.loads(agents)
            except json.JSONDecodeError:
                pass
        return [name.strip() for name in agents.split(",") if name.strip()]

    def _format_result(self, result: StarSwarmResult) -> str:
        """Format the StarSwarm result for display."""
        lines = [
            f"# StarSwarm: {result.workflow_id}",
            f"**Status**: {result.status.value.upper()}",
            f"**Duration**: {result.total_duration_seconds:.2f}s",
            "",
        ]

        # Phase 1: Decomposition
        lines.append("## Phase 1: Task Decomposition")
        if result.hub_result:
            status = "SUCCESS" if result.hub_result.success else "FAILED"
            lines.append(f"**Hub Agent**: {result.hub_result.agent_name}")
            lines.append(f"**Status**: {status}")
            lines.append(f"**Duration**: {result.hub_result.duration_seconds:.2f}s")
            if result.hub_result.error:
                lines.append(f"**Error**: {result.hub_result.error}")
        lines.append("")

        # Subtasks
        if result.subtasks:
            lines.append("### Generated Subtasks")
            for st in result.subtasks:
                lines.append(f"{st.index}. **{st.role}**: {st.objective[:100]}{'...' if len(st.objective) > 100 else ''}")
            lines.append("")

        # Phase 2: Execution
        lines.append("## Phase 2: Parallel Execution")
        successful = [r for r in result.spoke_results if r.success]
        failed = [r for r in result.spoke_results if not r.success]
        lines.append(f"**Successful**: {len(successful)} | **Failed**: {len(failed)}")
        lines.append("")

        for i, step in enumerate(result.spoke_results, 1):
            status_icon = "OK" if step.success else "FAIL"
            lines.append(f"### Spoke {i}: {step.agent_name} [{status_icon}]")
            lines.append(f"**Duration**: {step.duration_seconds:.2f}s")
            if step.error:
                lines.append(f"**Error**: {step.error}")
            lines.append("")

        # Phase 3: Aggregation
        lines.append("## Phase 3: Result Aggregation")
        if result.aggregation_result:
            status = "SUCCESS" if result.aggregation_result.success else "FAILED"
            lines.append(f"**Status**: {status}")
            lines.append(f"**Duration**: {result.aggregation_result.duration_seconds:.2f}s")
            if result.aggregation_result.error:
                lines.append(f"**Error**: {result.aggregation_result.error}")
        lines.append("")

        # Final Output
        lines.append("---")
        lines.append("")
        lines.append("## Final Output")
        lines.append(result.final_output)

        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://project-diagram {self.agent.agent_name}: Executing StarSwarm Pattern",
            content="",
            kvps=self.args,
        )


# =============================================================================


# =============================================================================
# HierarchicalSwarm Pattern
# =============================================================================

# Default prompts for HierarchicalSwarm
DEFAULT_ROOT_DECOMPOSITION_PROMPT = """You are a root coordinator in a hierarchical agent system. Your job is to decompose a complex task into {num_managers} major components, each to be handled by a manager agent.

Given the main task, create {num_managers} distinct manager-level subtasks. Each subtask should:
1. Be a substantial, self-contained component of the overall task
2. Be suitable for further decomposition by a manager
3. Have clear objectives and expected deliverables
4. Be assigned to a specific manager role

Format your response as:
---MANAGER TASK 1---
Role: [manager role/specialty]
Objective: [what this manager's team should accomplish]
Instructions: [high-level instructions for the manager]
---MANAGER TASK 2---
...

Main Task:
{task}"""

DEFAULT_MANAGER_DECOMPOSITION_PROMPT = """You are a manager agent in a hierarchical system. Your job is to decompose your assigned task into {num_workers} specific subtasks for your worker agents.

Your assigned task:
{manager_task}

Create {num_workers} worker-level subtasks. Each should:
1. Be specific and executable by a specialized worker
2. Have clear inputs, outputs, and success criteria
3. Contribute to completing your manager-level objective

Format your response as:
---WORKER TASK 1---
Role: [worker role/specialty]
Objective: [specific objective]
Instructions: [detailed instructions]
---WORKER TASK 2---
...
"""

DEFAULT_MANAGER_AGGREGATION_PROMPT = """You are a manager agent aggregating results from your workers.

Your original task was:
{manager_task}

Worker Results:
{worker_results}

Synthesize these results into a coherent response that fulfills your manager-level objective.
Provide your aggregated response:"""

DEFAULT_ROOT_AGGREGATION_PROMPT = """You are the root coordinator synthesizing final results from all managers.

The original task was:
{original_task}

Manager Results:
{manager_results}

Synthesize these results into a comprehensive final answer that:
1. Combines insights from all manager teams
2. Resolves any contradictions or overlaps
3. Provides a complete solution to the original task
4. Highlights the most important findings

Provide your final synthesized response:"""


class HierarchicalPhase(Enum):
    """Phases of HierarchicalSwarm execution."""
    ROOT_DECOMPOSITION = "root_decomposition"
    MANAGER_DECOMPOSITION = "manager_decomposition"
    WORKER_EXECUTION = "worker_execution"
    MANAGER_AGGREGATION = "manager_aggregation"
    ROOT_AGGREGATION = "root_aggregation"


@dataclass
class WorkerTask:
    """A task assigned to a worker agent."""
    index: int
    manager_name: str
    role: str
    objective: str
    instructions: str
    raw_content: str = ""

    def to_prompt(self) -> str:
        return f"""You are a {self.role}.

Objective: {self.objective}

Instructions:
{self.instructions}

Complete your assigned task and provide your results."""


@dataclass
class ManagerTask:
    """A task assigned to a manager agent."""
    index: int
    role: str
    objective: str
    instructions: str
    worker_tasks: list[WorkerTask] = field(default_factory=list)
    raw_content: str = ""

    def to_prompt(self) -> str:
        return f"""You are a {self.role}.

Objective: {self.objective}

Instructions:
{self.instructions}

Manage your team to complete this task."""


@dataclass
class HierarchicalSwarmResult:
    """Complete result from a HierarchicalSwarm execution."""
    workflow_id: str
    status: WorkflowStatus
    root_result: Optional[WorkflowStepResult] = None
    manager_results: list[WorkflowStepResult] = field(default_factory=list)
    worker_results: list[WorkflowStepResult] = field(default_factory=list)
    final_output: str = ""
    manager_tasks: list[ManagerTask] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "root_result": self.root_result.to_dict() if self.root_result else None,
            "manager_results": [r.to_dict() for r in self.manager_results],
            "worker_results": [r.to_dict() for r in self.worker_results],
            "final_output": self.final_output,
            "manager_tasks": [
                {
                    "index": mt.index,
                    "role": mt.role,
                    "objective": mt.objective,
                    "num_workers": len(mt.worker_tasks),
                }
                for mt in self.manager_tasks
            ],
            "total_duration_seconds": self.total_duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
        }


class HierarchicalSwarm(BaseWorkflow):
    """
    Tree-structured hierarchical coordination pattern.

    Root agent decomposes tasks to managers, managers decompose to workers,
    workers execute, results bubble up through aggregation at each level.

    Structure:
        Root (1)
       / | \
    Managers (N)
       / | \
    Workers (M per manager)
    """

    def __init__(
        self,
        parent_agent: Agent,
        workflow_id: str = "",
        timeout: float = 1800.0,  # Longer for 5 phases
        root_timeout: float = 300.0,
        manager_timeout: float = 300.0,
        worker_timeout: float = 300.0,
        root_decomposition_prompt: str = "",
        manager_decomposition_prompt: str = "",
        manager_aggregation_prompt: str = "",
        root_aggregation_prompt: str = "",
        max_concurrency: int = 10,
    ):
        super().__init__(
            workflow_id=workflow_id or f"hier_{uuid.uuid4().hex[:8]}",
            timeout=timeout,
            fail_fast=False,
        )
        self.parent_agent = parent_agent
        self.root_timeout = root_timeout
        self.manager_timeout = manager_timeout
        self.worker_timeout = worker_timeout
        self.root_decomposition_prompt = root_decomposition_prompt or DEFAULT_ROOT_DECOMPOSITION_PROMPT
        self.manager_decomposition_prompt = manager_decomposition_prompt or DEFAULT_MANAGER_DECOMPOSITION_PROMPT
        self.manager_aggregation_prompt = manager_aggregation_prompt or DEFAULT_MANAGER_AGGREGATION_PROMPT
        self.root_aggregation_prompt = root_aggregation_prompt or DEFAULT_ROOT_AGGREGATION_PROMPT
        self.max_concurrency = max_concurrency

        # Agent storage
        self._root_agent: Optional[Agent] = None
        self._manager_agents: dict[str, Agent] = {}
        self._worker_agents: dict[str, list[Agent]] = {}
        self._manager_tasks: list[ManagerTask] = []

    def _parse_agent_config(self, agent_spec) -> AgentConfig:
        """Parse agent specification into AgentConfig."""
        if isinstance(agent_spec, AgentConfig):
            return agent_spec
        if isinstance(agent_spec, dict):
            return AgentConfig(
                name=agent_spec.get("name", ""),
                profile=agent_spec.get("profile", ""),
                prompt=agent_spec.get("prompt", ""),
                timeout=agent_spec.get("timeout", self.worker_timeout),
                system_prompt=agent_spec.get("system_prompt", ""),
            )
        if isinstance(agent_spec, str):
            return AgentConfig(name=agent_spec, timeout=self.worker_timeout)
        raise ValueError(f"Invalid agent specification: {type(agent_spec)}")

    async def _create_agent(
        self,
        config: AgentConfig,
        agent_number: int,
        role: str = "worker",
    ) -> Agent:
        """Create a subordinate agent."""
        base_config = initialize_agent()
        if config.profile:
            base_config.profile = config.profile

        agent = Agent(
            number=self.parent_agent.number + agent_number,
            config=base_config,
            context=self.parent_agent.context,
        )
        agent.set_data("_workflow_id", self.workflow_id)
        agent.set_data("_workflow_step", agent_number)
        agent.set_data(Agent.DATA_NAME_SUPERIOR, self.parent_agent)
        agent.set_data("_hierarchy_role", role)
        return agent

    async def _execute_agent(
        self,
        agent: Agent,
        input_message: str,
        timeout: float,
    ) -> WorkflowStepResult:
        """Execute a single agent and return its result."""
        step_start = datetime.now(timezone.utc)
        try:
            agent.hist_add_user_message(UserMessage(message=input_message, attachments=[]))

            async def run_agent():
                return await agent.monologue()

            try:
                result = await asyncio.wait_for(run_agent(), timeout=timeout)
            except asyncio.TimeoutError:
                raise WorkflowTimeoutError(
                    f"Agent {agent.agent_name} exceeded timeout of {timeout}s"
                )

            agent.history.new_topic()
            step_end = datetime.now(timezone.utc)
            duration = (step_end - step_start).total_seconds()

            return WorkflowStepResult(
                agent_name=agent.agent_name,
                agent_number=agent.number,
                success=True,
                output=result,
                error=None,
                start_time=step_start,
                end_time=step_end,
                duration_seconds=duration,
            )

        except WorkflowTimeoutError as e:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(
                agent_name=agent.agent_name,
                agent_number=agent.number,
                success=False,
                output="",
                error=str(e),
                start_time=step_start,
                end_time=step_end,
                duration_seconds=(step_end - step_start).total_seconds(),
            )

        except Exception as e:
            step_end = datetime.now(timezone.utc)
            logger.exception(f"Error in HierarchicalSwarm agent {agent.agent_name}")
            return WorkflowStepResult(
                agent_name=agent.agent_name,
                agent_number=agent.number,
                success=False,
                output="",
                error=f"{type(e).__name__}: {str(e)}",
                start_time=step_start,
                end_time=step_end,
                duration_seconds=(step_end - step_start).total_seconds(),
            )

    def _parse_manager_tasks(self, decomposition_output: str, num_expected: int) -> list[ManagerTask]:
        """Parse root decomposition output into manager tasks."""
        import re

        tasks = []
        pattern = r"---MANAGER\s*TASK\s*(\d+)---\s*(.*?)(?=---MANAGER\s*TASK\s*\d+---|$)"
        matches = re.findall(pattern, decomposition_output, re.DOTALL | re.IGNORECASE)

        for match in matches:
            index = int(match[0])
            content = match[1].strip()

            role_match = re.search(r"Role:\s*(.+?)(?=\n|$)", content, re.IGNORECASE)
            role = role_match.group(1).strip() if role_match else f"Manager {index}"

            obj_match = re.search(r"Objective:\s*(.+?)(?=\n\w+:|$)", content, re.DOTALL | re.IGNORECASE)
            objective = obj_match.group(1).strip() if obj_match else "Complete assigned objective"

            instr_match = re.search(r"Instructions:\s*(.+?)$", content, re.DOTALL | re.IGNORECASE)
            instructions = instr_match.group(1).strip() if instr_match else content

            tasks.append(ManagerTask(
                index=index,
                role=role,
                objective=objective,
                instructions=instructions,
                raw_content=content,
            ))

        if not tasks:
            for i in range(num_expected):
                tasks.append(ManagerTask(
                    index=i + 1,
                    role=f"Manager {i + 1}",
                    objective=f"Complete component {i + 1}",
                    instructions="Handle your portion of the task.",
                    raw_content="",
                ))

        return tasks

    def _parse_worker_tasks(self, decomposition_output: str, manager_name: str, num_expected: int) -> list[WorkerTask]:
        """Parse manager decomposition output into worker tasks."""
        import re

        tasks = []
        pattern = r"---WORKER\s*TASK\s*(\d+)---\s*(.*?)(?=---WORKER\s*TASK\s*\d+---|$)"
        matches = re.findall(pattern, decomposition_output, re.DOTALL | re.IGNORECASE)

        for match in matches:
            index = int(match[0])
            content = match[1].strip()

            role_match = re.search(r"Role:\s*(.+?)(?=\n|$)", content, re.IGNORECASE)
            role = role_match.group(1).strip() if role_match else f"Worker {index}"

            obj_match = re.search(r"Objective:\s*(.+?)(?=\n\w+:|$)", content, re.DOTALL | re.IGNORECASE)
            objective = obj_match.group(1).strip() if obj_match else "Complete assigned task"

            instr_match = re.search(r"Instructions:\s*(.+?)$", content, re.DOTALL | re.IGNORECASE)
            instructions = instr_match.group(1).strip() if instr_match else content

            tasks.append(WorkerTask(
                index=index,
                manager_name=manager_name,
                role=role,
                objective=objective,
                instructions=instructions,
                raw_content=content,
            ))

        if not tasks:
            for i in range(num_expected):
                tasks.append(WorkerTask(
                    index=i + 1,
                    manager_name=manager_name,
                    role=f"Worker {i + 1}",
                    objective=f"Complete subtask {i + 1}",
                    instructions="Process your assigned portion.",
                    raw_content="",
                ))

        return tasks

    async def _root_decompose(
        self,
        task: str,
        num_managers: int,
    ) -> tuple[list[ManagerTask], WorkflowStepResult]:
        """Root agent decomposes task into manager tasks."""
        decomposition_input = self.root_decomposition_prompt.format(
            num_managers=num_managers,
            task=task,
        )

        root_config = AgentConfig(name="root_coordinator", timeout=self.root_timeout)
        self._root_agent = await self._create_agent(root_config, 1, role="root")

        result = await self._execute_agent(
            self._root_agent,
            decomposition_input,
            self.root_timeout,
        )

        if result.success:
            tasks = self._parse_manager_tasks(result.output, num_managers)
        else:
            tasks = [
                ManagerTask(
                    index=i + 1,
                    role=f"Manager {i + 1}",
                    objective=f"Handle component {i + 1}",
                    instructions=task,
                    raw_content="",
                )
                for i in range(num_managers)
            ]

        return tasks, result

    async def _manager_decompose(
        self,
        manager_task: ManagerTask,
        manager_agent: Agent,
        num_workers: int,
    ) -> list[WorkerTask]:
        """Manager agent decomposes its task into worker tasks."""
        manager_prompt = self.manager_decomposition_prompt.format(
            num_workers=num_workers,
            manager_task=f"Role: {manager_task.role}\nObjective: {manager_task.objective}\nInstructions: {manager_task.instructions}",
        )

        result = await self._execute_agent(
            manager_agent,
            manager_prompt,
            self.manager_timeout,
        )

        if result.success:
            return self._parse_worker_tasks(result.output, manager_task.role, num_workers)
        else:
            return [
                WorkerTask(
                    index=i + 1,
                    manager_name=manager_task.role,
                    role=f"Worker {i + 1}",
                    objective=f"Complete subtask {i + 1}",
                    instructions=manager_task.instructions,
                    raw_content="",
                )
                for i in range(num_workers)
            ]

    async def _execute_workers(
        self,
        worker_tasks: list[WorkerTask],
        worker_agents: list[Agent],
    ) -> list[WorkflowStepResult]:
        """Execute all worker agents in parallel."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute_worker(
            agent: Agent,
            task: WorkerTask,
            idx: int,
        ) -> WorkflowStepResult:
            async with semaphore:
                logger.info(
                    f"HierarchicalSwarm {self.workflow_id}: "
                    f"Starting worker {idx + 1} ({task.role}) for {task.manager_name}"
                )
                prompt = task.to_prompt()
                return await self._execute_agent(agent, prompt, self.worker_timeout)

        tasks = []
        for i, (agent, task) in enumerate(zip(worker_agents, worker_tasks)):
            tasks.append(execute_worker(agent, task, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        step_results = []
        for result in results:
            if isinstance(result, Exception):
                step_results.append(WorkflowStepResult(
                    agent_name="unknown",
                    agent_number=0,
                    success=False,
                    output="",
                    error=f"{type(result).__name__}: {str(result)}",
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    duration_seconds=0.0,
                ))
            elif isinstance(result, WorkflowStepResult):
                step_results.append(result)

        return step_results

    async def _manager_aggregate(
        self,
        manager_task: ManagerTask,
        manager_agent: Agent,
        worker_results: list[WorkflowStepResult],
    ) -> WorkflowStepResult:
        """Manager aggregates worker results."""
        successful_results = [r for r in worker_results if r.success]

        if not successful_results:
            return WorkflowStepResult(
                agent_name=manager_agent.agent_name,
                agent_number=manager_agent.number,
                success=False,
                output="",
                error="All workers failed",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=0.0,
            )

        worker_summary = "\n\n".join([
            f"--- RESULT FROM {r.agent_name} ---\n{r.output}"
            for r in successful_results
        ])

        aggregation_input = self.manager_aggregation_prompt.format(
            manager_task=f"Role: {manager_task.role}\nObjective: {manager_task.objective}\nInstructions: {manager_task.instructions}",
            worker_results=worker_summary,
        )

        return await self._execute_agent(
            manager_agent,
            aggregation_input,
            self.manager_timeout,
        )

    async def _root_aggregate(
        self,
        original_task: str,
        manager_results: list[WorkflowStepResult],
    ) -> WorkflowStepResult:
        """Root synthesizes final answer from all manager results."""
        successful_results = [r for r in manager_results if r.success]

        if not successful_results:
            return WorkflowStepResult(
                agent_name=self._root_agent.agent_name if self._root_agent else "root",
                agent_number=self._root_agent.number if self._root_agent else 1,
                success=False,
                output="",
                error="All managers failed",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=0.0,
            )

        manager_summary = "\n\n".join([
            f"--- RESULT FROM {r.agent_name} ---\n{r.output}"
            for r in successful_results
        ])

        aggregation_input = self.root_aggregation_prompt.format(
            original_task=original_task,
            manager_results=manager_summary,
        )

        return await self._execute_agent(
            self._root_agent,
            aggregation_input,
            self.root_timeout,
        )

    async def execute(
        self,
        initial_input: str,
        root: str = "",
        managers: list = None,
        workers: dict = None,
    ) -> HierarchicalSwarmResult:
        """
        Execute the HierarchicalSwarm pattern.

        Args:
            initial_input: The main task to be processed
            root: Root agent name/config
            managers: List of manager agent names/configs
            workers: Dict mapping manager name -> list of worker agent names

        Returns:
            HierarchicalSwarmResult with all phase results
        """
        managers = managers or []
        workers = workers or {}

        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._manager_tasks = []

        root_result = None
        all_manager_results = []
        all_worker_results = []
        final_output = ""

        try:
            # Parse configurations
            manager_configs = [self._parse_agent_config(m) for m in managers]
            num_managers = len(manager_configs)

            logger.info(
                f"HierarchicalSwarm {self.workflow_id}: "
                f"Starting with {num_managers} managers"
            )

            # Phase 1: Root Decomposition
            logger.info(f"HierarchicalSwarm {self.workflow_id}: Phase 1 - Root Decomposition")
            self._manager_tasks, root_result = await self._root_decompose(
                initial_input,
                num_managers,
            )

            if not self._manager_tasks:
                return HierarchicalSwarmResult(
                    workflow_id=self.workflow_id,
                    status=WorkflowStatus.FAILED,
                    root_result=root_result,
                    final_output="",
                    total_duration_seconds=(
                        datetime.now(timezone.utc) - self._start_time
                    ).total_seconds(),
                    start_time=self._start_time,
                    end_time=datetime.now(timezone.utc),
                    metadata={"error": "Root decomposition failed"},
                )

            # Create manager agents
            agent_counter = 2  # Root is 1
            for i, (config, mtask) in enumerate(zip(manager_configs, self._manager_tasks)):
                agent = await self._create_agent(config, agent_counter, role="manager")
                self._manager_agents[config.name or f"manager_{i}"] = agent
                agent_counter += 1

            # Phase 2: Manager Decomposition (parallel)
            logger.info(f"HierarchicalSwarm {self.workflow_id}: Phase 2 - Manager Decomposition")

            async def decompose_manager(manager_name, manager_agent, manager_task):
                worker_names = workers.get(manager_name, [])
                num_workers = len(worker_names) if worker_names else 2
                return await self._manager_decompose(manager_task, manager_agent, num_workers)

            decompose_tasks = []
            for i, ((name, agent), mtask) in enumerate(
                zip(self._manager_agents.items(), self._manager_tasks)
            ):
                decompose_tasks.append(decompose_manager(name, agent, mtask))

            worker_task_lists = await asyncio.gather(*decompose_tasks, return_exceptions=True)

            # Store worker tasks in manager tasks
            for mtask, wtasks in zip(self._manager_tasks, worker_task_lists):
                if isinstance(wtasks, list):
                    mtask.worker_tasks = wtasks
                else:
                    mtask.worker_tasks = []

            # Create worker agents
            for (manager_name, agent), mtask in zip(
                self._manager_agents.items(), self._manager_tasks
            ):
                worker_names = workers.get(manager_name, [])
                worker_list = []
                for j, wname in enumerate(worker_names[:len(mtask.worker_tasks)]):
                    wconfig = self._parse_agent_config(wname)
                    wagent = await self._create_agent(wconfig, agent_counter, role="worker")
                    worker_list.append(wagent)
                    agent_counter += 1
                self._worker_agents[manager_name] = worker_list

            # Phase 3: Worker Execution (all workers in parallel)
            logger.info(f"HierarchicalSwarm {self.workflow_id}: Phase 3 - Worker Execution")

            all_worker_tasks = []
            all_worker_agents = []
            for manager_name, mtask in zip(self._manager_agents.keys(), self._manager_tasks):
                wagents = self._worker_agents.get(manager_name, [])
                wtasks = mtask.worker_tasks
                for agent, task in zip(wagents, wtasks):
                    all_worker_agents.append(agent)
                    all_worker_tasks.append(task)

            if all_worker_agents:
                all_worker_results = await self._execute_workers(
                    all_worker_tasks,
                    all_worker_agents,
                )

            # Phase 4: Manager Aggregation (parallel)
            logger.info(f"HierarchicalSwarm {self.workflow_id}: Phase 4 - Manager Aggregation")

            # Group worker results by manager
            worker_results_by_manager = {}
            idx = 0
            for manager_name, mtask in zip(self._manager_agents.keys(), self._manager_tasks):
                num_workers = len(mtask.worker_tasks)
                worker_results_by_manager[manager_name] = all_worker_results[idx:idx + num_workers]
                idx += num_workers

            async def aggregate_manager(manager_name, manager_agent, mtask):
                wresults = worker_results_by_manager.get(manager_name, [])
                return await self._manager_aggregate(mtask, manager_agent, wresults)

            aggregate_tasks = []
            for manager_name, (mname, agent) in enumerate(self._manager_agents.items()):
                mtask = self._manager_tasks[manager_name]
                aggregate_tasks.append(aggregate_manager(mname, agent, mtask))

            all_manager_results = await asyncio.gather(*aggregate_tasks, return_exceptions=True)

            manager_step_results = []
            for result in all_manager_results:
                if isinstance(result, WorkflowStepResult):
                    manager_step_results.append(result)
                else:
                    manager_step_results.append(WorkflowStepResult(
                        agent_name="unknown",
                        agent_number=0,
                        success=False,
                        output="",
                        error=str(result),
                        start_time=datetime.now(timezone.utc),
                        end_time=datetime.now(timezone.utc),
                        duration_seconds=0.0,
                    ))
            all_manager_results = manager_step_results

            # Phase 5: Root Aggregation
            logger.info(f"HierarchicalSwarm {self.workflow_id}: Phase 5 - Root Aggregation")
            final_aggregation = await self._root_aggregate(
                initial_input,
                all_manager_results,
            )

            if final_aggregation.success:
                final_output = final_aggregation.output
                status = WorkflowStatus.COMPLETED
            else:
                # Fallback: concatenate successful manager results
                successful = [r for r in all_manager_results if r.success]
                if successful:
                    final_output = "\n\n---\n\n".join([r.output for r in successful])
                    status = WorkflowStatus.COMPLETED
                else:
                    final_output = "All phases failed to produce results"
                    status = WorkflowStatus.FAILED

            self._end_time = datetime.now(timezone.utc)
            total_duration = (self._end_time - self._start_time).total_seconds()

            return HierarchicalSwarmResult(
                workflow_id=self.workflow_id,
                status=status,
                root_result=root_result,
                manager_results=all_manager_results,
                worker_results=all_worker_results,
                final_output=final_output,
                manager_tasks=self._manager_tasks,
                total_duration_seconds=total_duration,
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={
                    "num_managers": num_managers,
                    "num_workers": len(all_worker_results),
                    "successful_managers": len([r for r in all_manager_results if r.success]),
                    "successful_workers": len([r for r in all_worker_results if r.success]),
                },
            )

        except asyncio.TimeoutError:
            self._end_time = datetime.now(timezone.utc)
            return HierarchicalSwarmResult(
                workflow_id=self.workflow_id,
                status=WorkflowStatus.TIMEOUT,
                root_result=root_result,
                manager_results=all_manager_results,
                worker_results=all_worker_results,
                final_output=f"Workflow exceeded timeout of {self.timeout}s",
                total_duration_seconds=(
                    self._end_time - self._start_time
                ).total_seconds(),
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={"error": "Timeout"},
            )

        except Exception as e:
            logger.exception(f"HierarchicalSwarm {self.workflow_id} failed")
            self._end_time = datetime.now(timezone.utc)
            return HierarchicalSwarmResult(
                workflow_id=self.workflow_id,
                status=WorkflowStatus.FAILED,
                root_result=root_result,
                manager_results=all_manager_results,
                worker_results=all_worker_results,
                final_output="",
                total_duration_seconds=(
                    self._end_time - self._start_time
                ).total_seconds(),
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={"error": str(e)},
            )


class swarm_hierarchical(Tool):
    """Tool for executing HierarchicalSwarm tree-structured coordination pattern."""

    async def execute(
        self,
        root="",
        managers="",
        workers="",
        task="",
        workflow_id="",
        timeout="1800",
        root_timeout="300",
        manager_timeout="300",
        worker_timeout="300",
        root_decomposition_prompt="",
        manager_decomposition_prompt="",
        manager_aggregation_prompt="",
        root_aggregation_prompt="",
        max_concurrency="10",
        **kwargs,
    ):
        """
        Execute HierarchicalSwarm pattern.

        Args:
            root: Root agent name/config
            managers: Comma-separated or JSON array of manager agent names/configs
            workers: JSON object mapping manager name to list of worker names
            task: The main task to process through the hierarchy
            workflow_id: Optional workflow identifier
            timeout: Total workflow timeout in seconds
            root_timeout: Root agent timeout
            manager_timeout: Manager agent timeout
            worker_timeout: Worker agent timeout
            root_decomposition_prompt: Custom prompt for root decomposition
            manager_decomposition_prompt: Custom prompt for manager decomposition
            manager_aggregation_prompt: Custom prompt for manager aggregation
            root_aggregation_prompt: Custom prompt for root aggregation
            max_concurrency: Maximum concurrent worker executions
        """
        import json

        try:
            # Parse managers
            manager_list = self._parse_agents_param(managers)
            if not manager_list:
                return Response(
                    message="Error: No managers specified for HierarchicalSwarm",
                    break_loop=False,
                )

            # Parse workers mapping
            workers_dict = {}
            if workers:
                try:
                    workers_dict = json.loads(workers) if isinstance(workers, str) else workers
                except json.JSONDecodeError:
                    return Response(
                        message="Error: Invalid workers mapping format. Expected JSON object.",
                        break_loop=False,
                    )

            # Parse numeric values
            try:
                timeout_val = float(timeout)
                root_timeout_val = float(root_timeout)
                manager_timeout_val = float(manager_timeout)
                worker_timeout_val = float(worker_timeout)
                max_concurrency_val = int(max_concurrency)
            except ValueError:
                return Response(
                    message="Error: Invalid numeric parameters",
                    break_loop=False,
                )

            # Create HierarchicalSwarm workflow
            workflow = HierarchicalSwarm(
                parent_agent=self.agent,
                workflow_id=workflow_id,
                timeout=timeout_val,
                root_timeout=root_timeout_val,
                manager_timeout=manager_timeout_val,
                worker_timeout=worker_timeout_val,
                root_decomposition_prompt=root_decomposition_prompt or DEFAULT_ROOT_DECOMPOSITION_PROMPT,
                manager_decomposition_prompt=manager_decomposition_prompt or DEFAULT_MANAGER_DECOMPOSITION_PROMPT,
                manager_aggregation_prompt=manager_aggregation_prompt or DEFAULT_MANAGER_AGGREGATION_PROMPT,
                root_aggregation_prompt=root_aggregation_prompt or DEFAULT_ROOT_AGGREGATION_PROMPT,
                max_concurrency=max_concurrency_val,
            )

            # Execute
            task_msg = task or self.message or "Complete this task using hierarchical coordination."
            result = await workflow.execute(
                initial_input=task_msg,
                root=root,
                managers=manager_list,
                workers=workers_dict,
            )

            # Format response
            response_text = self._format_result(result)
            return Response(
                message=response_text,
                break_loop=False,
                additional={
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "num_managers": len(result.manager_results),
                    "num_workers": len(result.worker_results),
                },
            )

        except Exception as e:
            logger.exception("HierarchicalSwarm execution failed")
            return Response(
                message=f"HierarchicalSwarm failed: {type(e).__name__}: {str(e)}",
                break_loop=False,
            )

    def _parse_agents_param(self, agents: str) -> list:
        """Parse agents parameter from string or JSON."""
        import json
        if not agents:
            return []
        agents = agents.strip()
        if agents.startswith("["):
            try:
                return json.loads(agents)
            except json.JSONDecodeError:
                pass
        return [name.strip() for name in agents.split(",") if name.strip()]

    def _format_result(self, result: HierarchicalSwarmResult) -> str:
        """Format the HierarchicalSwarm result for display."""
        lines = [
            f"# HierarchicalSwarm: {result.workflow_id}",
            f"**Status**: {result.status.value.upper()}",
            f"**Duration**: {result.total_duration_seconds:.2f}s",
            "",
        ]

        # Phase 1: Root Decomposition
        lines.append("## Phase 1: Root Decomposition")
        if result.root_result:
            status = "SUCCESS" if result.root_result.success else "FAILED"
            lines.append(f"**Root Agent**: {result.root_result.agent_name}")
            lines.append(f"**Status**: {status}")
            lines.append(f"**Duration**: {result.root_result.duration_seconds:.2f}s")
            if result.root_result.error:
                lines.append(f"**Error**: {result.root_result.error}")
            lines.append("")

        # Manager Tasks
        if result.manager_tasks:
            lines.append("### Generated Manager Tasks")
            for mt in result.manager_tasks:
                obj_preview = mt.objective[:80] + "..." if len(mt.objective) > 80 else mt.objective
                lines.append(f"{mt.index}. **{mt.role}**: {obj_preview}")
                lines.append(f"   Workers: {len(mt.worker_tasks)}")
            lines.append("")

        # Phase 2-4: Manager Teams
        lines.append("## Phases 2-4: Manager Teams Execution")
        for i, (mt, mr) in enumerate(zip(result.manager_tasks, result.manager_results)):
            status_icon = "OK" if mr.success else "FAIL"
            lines.append(f"### Manager {i + 1}: {mt.role} [{status_icon}]")
            lines.append(f"**Duration**: {mr.duration_seconds:.2f}s")
            if mr.error:
                lines.append(f"**Error**: {mr.error}")
            lines.append("")

        # Worker Results
        worker_success = len([r for r in result.worker_results if r.success])
        worker_failed = len([r for r in result.worker_results if not r.success])
        lines.append(f"**Workers**: {worker_success} successful, {worker_failed} failed")
        lines.append("")

        # Phase 5: Root Aggregation
        lines.append("## Phase 5: Root Aggregation")
        successful_managers = len([r for r in result.manager_results if r.success])
        lines.append(f"**Managers Completed**: {successful_managers}/{len(result.manager_results)}")
        lines.append("")

        # Final Output
        lines.append("---")
        lines.append("")
        lines.append("## Final Output")
        lines.append(result.final_output)

        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://sitemap {self.agent.agent_name}: Executing HierarchicalSwarm Pattern",
            content="",
            kvps=self.args,
        )



# =============================================================================
# CircularSwarm Pattern
# =============================================================================

DEFAULT_CIRCULAR_ITERATION_PROMPT = """You are agent {position} of {total} in a circular refinement process.

Your task is to process and refine the following input:
{input}

Previous agent's output:
{previous_output}

Improve, refine, or build upon the previous output."""

DEFAULT_CIRCULAR_SYNTHESIS_PROMPT = """You are a synthesis agent in a circular refinement process.

After {iterations} complete cycles through {num_agents} agents, synthesize the final result.

Cycle outputs:
{cycle_outputs}

Provide a final, polished synthesis of all the iterative refinements:"""


class CircularPhase(Enum):
    """Phases of CircularSwarm execution."""
    ITERATION = "iteration"
    SYNTHESIS = "synthesis"


@dataclass
class CircularIterationResult:
    """Result from a single circular iteration."""
    iteration: int
    agent_results: list[WorkflowStepResult]
    combined_output: str


class CircularSwarmResult:
    """Complete result from a CircularSwarm execution."""

    def __init__(self, workflow_id: str, status: WorkflowStatus, iterations: list, final_output: str, total_duration_seconds: float = 0.0, start_time: datetime = None, end_time: datetime = None, metadata: dict = None):
        self.workflow_id = workflow_id
        self.status = status
        self.iterations = iterations
        self.final_output = final_output
        self.total_duration_seconds = total_duration_seconds
        self.start_time = start_time or datetime.now(timezone.utc)
        self.end_time = end_time
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "iterations": [{"iteration": i.iteration, "num_agents": len(i.agent_results)} for i in self.iterations],
            "final_output": self.final_output,
            "total_duration_seconds": self.total_duration_seconds,
            "metadata": self.metadata,
        }


class CircularSwarm(BaseWorkflow):
    """Circular coordination pattern - agents arranged in a circle, each passing output to the next."""

    def __init__(self, parent_agent: Agent, workflow_id: str = "", timeout: float = 1200.0, agent_timeout: float = 300.0, iterations: int = 2, iteration_prompt: str = "", synthesis_prompt: str = ""):
        super().__init__(workflow_id=workflow_id or f"circular_{uuid.uuid4().hex[:8]}", timeout=timeout, fail_fast=False)
        self.parent_agent = parent_agent
        self.agent_timeout = agent_timeout
        self.iterations = iterations
        self.iteration_prompt = iteration_prompt or DEFAULT_CIRCULAR_ITERATION_PROMPT
        self.synthesis_prompt = synthesis_prompt or DEFAULT_CIRCULAR_SYNTHESIS_PROMPT
        self._agents: list[Agent] = []
        self._iteration_results: list = []

    def _parse_agent_config(self, agent_spec) -> AgentConfig:
        if isinstance(agent_spec, AgentConfig):
            return agent_spec
        if isinstance(agent_spec, dict):
            return AgentConfig(name=agent_spec.get("name", ""), profile=agent_spec.get("profile", ""), prompt=agent_spec.get("prompt", ""), timeout=agent_spec.get("timeout", self.agent_timeout), system_prompt=agent_spec.get("system_prompt", ""))
        if isinstance(agent_spec, str):
            return AgentConfig(name=agent_spec, timeout=self.agent_timeout)
        raise ValueError(f"Invalid agent specification: {type(agent_spec)}")

    async def _create_agent(self, config: AgentConfig, agent_number: int, position: int, total: int) -> Agent:
        base_config = initialize_agent()
        if config.profile:
            base_config.profile = config.profile
        agent = Agent(number=self.parent_agent.number + agent_number, config=base_config, context=self.parent_agent.context)
        agent.set_data("_workflow_id", self.workflow_id)
        agent.set_data("_workflow_step", agent_number)
        agent.set_data(Agent.DATA_NAME_SUPERIOR, self.parent_agent)
        return agent

    async def _execute_agent(self, agent: Agent, input_message: str, timeout: float) -> WorkflowStepResult:
        step_start = datetime.now(timezone.utc)
        try:
            agent.hist_add_user_message(UserMessage(message=input_message, attachments=[]))
            result = await asyncio.wait_for(agent.monologue(), timeout=timeout)
            agent.history.new_topic()
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=True, output=result, error=None, start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())
        except asyncio.TimeoutError:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=False, output="", error=f"Timeout after {timeout}s", start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())
        except Exception as e:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=False, output="", error=str(e), start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())

    async def _run_iteration(self, agents: list, previous_output: str, initial_input: str) -> CircularIterationResult:
        current_output = previous_output
        agent_results = []
        for i, agent in enumerate(agents):
            iteration_input = self.iteration_prompt.format(position=i + 1, total=len(agents), input=initial_input, previous_output=current_output)
            result = await self._execute_agent(agent, iteration_input, self.agent_timeout)
            agent_results.append(result)
            if result.success:
                current_output = result.output
        return CircularIterationResult(iteration=len(self._iteration_results) + 1, agent_results=agent_results, combined_output=current_output)

    async def execute(self, initial_input: str, agents: list) -> CircularSwarmResult:
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._iteration_results = []
        try:
            agent_configs = [self._parse_agent_config(spec) for spec in agents]
            num_agents = len(agent_configs)
            self._agents = [await self._create_agent(config, i + 1, i + 1, num_agents) for i, config in enumerate(agent_configs)]
            current_output = initial_input
            for iteration in range(self.iterations):
                iteration_result = await self._run_iteration(self._agents, current_output, initial_input)
                self._iteration_results.append(iteration_result)
                current_output = iteration_result.combined_output
            final_output = self._iteration_results[-1].combined_output if self._iteration_results else ""
            self._end_time = datetime.now(timezone.utc)
            return CircularSwarmResult(workflow_id=self.workflow_id, status=WorkflowStatus.COMPLETED, iterations=self._iteration_results, final_output=final_output, total_duration_seconds=(self._end_time - self._start_time).total_seconds(), start_time=self._start_time, end_time=self._end_time, metadata={"num_agents": num_agents, "iterations": self.iterations})
        except Exception as e:
            self._end_time = datetime.now(timezone.utc)
            return CircularSwarmResult(workflow_id=self.workflow_id, status=WorkflowStatus.FAILED, iterations=self._iteration_results, final_output="", total_duration_seconds=(self._end_time - self._start_time).total_seconds(), start_time=self._start_time, end_time=self._end_time, metadata={"error": str(e)})


class swarm_circular(Tool):
    """Tool for executing CircularSwarm iterative refinement pattern."""

    async def execute(self, agents="", task="", iterations="2", workflow_id="", timeout="1200", agent_timeout="300", iteration_prompt="", synthesis_prompt="", **kwargs):
        import json
        try:
            agent_list = self._parse_agents_param(agents)
            if not agent_list:
                return Response(message="Error: No agents specified for CircularSwarm", break_loop=False)
            workflow = CircularSwarm(parent_agent=self.agent, workflow_id=workflow_id, timeout=float(timeout), agent_timeout=float(agent_timeout), iterations=int(iterations), iteration_prompt=iteration_prompt or DEFAULT_CIRCULAR_ITERATION_PROMPT, synthesis_prompt=synthesis_prompt or DEFAULT_CIRCULAR_SYNTHESIS_PROMPT)
            result = await workflow.execute(initial_input=task or self.message or "Process and refine this input.", agents=agent_list)
            return Response(message=self._format_result(result), break_loop=False, additional={"workflow_id": result.workflow_id, "status": result.status.value})
        except Exception as e:
            return Response(message=f"CircularSwarm failed: {e}", break_loop=False)

    def _parse_agents_param(self, agents: str) -> list:
        import json
        if not agents:
            return []
        agents = agents.strip()
        if agents.startswith("["):
            try:
                return json.loads(agents)
            except json.JSONDecodeError:
                pass
        return [name.strip() for name in agents.split(",") if name.strip()]

    def _format_result(self, result) -> str:
        lines = [f"# CircularSwarm: {result.workflow_id}", f"**Status**: {result.status.value.upper()}", f"**Duration**: {result.total_duration_seconds:.2f}s", f"**Iterations**: {len(result.iterations)}", ""]
        for i, iteration in enumerate(result.iterations, 1):
            successful = len([r for r in iteration.agent_results if r.success])
            lines.append(f"## Iteration {i}: {successful}/{len(iteration.agent_results)} agents succeeded")
        lines.extend(["", "---", "", "## Final Output", result.final_output])
        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(type="tool", heading=f"icon://sync {self.agent.agent_name}: Executing CircularSwarm Pattern", content="", kvps=self.args)


# =============================================================================
# MeshSwarm Pattern
# =============================================================================

DEFAULT_MESH_DELIBERATION_PROMPT = """You are {agent_name} in a fully-connected mesh deliberation.

The original task is:
{task}

Other agents' current positions:
{other_positions}

Your current position:
{your_position}

Refine your position based on other agents' perspectives."""

DEFAULT_MESH_CONSENSUS_PROMPT = """You are a consensus agent synthesizing positions from a mesh deliberation.

The original task was:
{task}

Final positions from all agents:
{final_positions}

Provide a consensus result."""


class MeshRoundResult:
    """Result from a single mesh deliberation round."""

    def __init__(self, round_num: int, agent_results: list):
        self.round_num = round_num
        self.agent_results = agent_results

    def get_positions(self) -> dict:
        return {r.agent_name: r.output if r.success else f"[ERROR: {r.error}]" for r in self.agent_results}


class MeshSwarmResult:
    """Complete result from a MeshSwarm execution."""

    def __init__(self, workflow_id: str, status: WorkflowStatus, rounds: list, consensus_result, final_output: str, total_duration_seconds: float = 0.0, start_time: datetime = None, end_time: datetime = None, metadata: dict = None):
        self.workflow_id = workflow_id
        self.status = status
        self.rounds = rounds
        self.consensus_result = consensus_result
        self.final_output = final_output
        self.total_duration_seconds = total_duration_seconds
        self.start_time = start_time or datetime.now(timezone.utc)
        self.end_time = end_time
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {"workflow_id": self.workflow_id, "status": self.status.value, "rounds": len(self.rounds), "final_output": self.final_output, "total_duration_seconds": self.total_duration_seconds, "metadata": self.metadata}


class MeshSwarm(BaseWorkflow):
    """Fully connected mesh coordination pattern - each agent communicates with all others."""

    def __init__(self, parent_agent: Agent, workflow_id: str = "", timeout: float = 1500.0, agent_timeout: float = 300.0, max_rounds: int = 3, deliberation_prompt: str = "", consensus_prompt: str = "", max_concurrency: int = 10):
        super().__init__(workflow_id=workflow_id or f"mesh_{uuid.uuid4().hex[:8]}", timeout=timeout, fail_fast=False)
        self.parent_agent = parent_agent
        self.agent_timeout = agent_timeout
        self.max_rounds = max_rounds
        self.deliberation_prompt = deliberation_prompt or DEFAULT_MESH_DELIBERATION_PROMPT
        self.consensus_prompt = consensus_prompt or DEFAULT_MESH_CONSENSUS_PROMPT
        self.max_concurrency = max_concurrency
        self._agents: list[Agent] = []
        self._agent_names: list[str] = []
        self._round_results: list = []

    def _parse_agent_config(self, agent_spec) -> AgentConfig:
        if isinstance(agent_spec, AgentConfig):
            return agent_spec
        if isinstance(agent_spec, dict):
            return AgentConfig(name=agent_spec.get("name", ""), profile=agent_spec.get("profile", ""), prompt=agent_spec.get("prompt", ""), timeout=agent_spec.get("timeout", self.agent_timeout), system_prompt=agent_spec.get("system_prompt", ""))
        if isinstance(agent_spec, str):
            return AgentConfig(name=agent_spec, timeout=self.agent_timeout)
        raise ValueError(f"Invalid agent specification: {type(agent_spec)}")

    async def _create_agent(self, config: AgentConfig, agent_number: int) -> Agent:
        base_config = initialize_agent()
        if config.profile:
            base_config.profile = config.profile
        agent = Agent(number=self.parent_agent.number + agent_number, config=base_config, context=self.parent_agent.context)
        agent.set_data("_workflow_id", self.workflow_id)
        agent.set_data("_workflow_step", agent_number)
        agent.set_data(Agent.DATA_NAME_SUPERIOR, self.parent_agent)
        return agent

    async def _execute_agent(self, agent: Agent, input_message: str, timeout: float) -> WorkflowStepResult:
        step_start = datetime.now(timezone.utc)
        try:
            agent.hist_add_user_message(UserMessage(message=input_message, attachments=[]))
            result = await asyncio.wait_for(agent.monologue(), timeout=timeout)
            agent.history.new_topic()
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=True, output=result, error=None, start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())
        except asyncio.TimeoutError:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=False, output="", error=f"Timeout after {timeout}s", start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())
        except Exception as e:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=False, output="", error=str(e), start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())

    async def _run_round(self, task: str, previous_positions: dict) -> MeshRoundResult:
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_agent_deliberation(agent: Agent, agent_name: str):
            async with semaphore:
                other_positions = "\n".join([f"**{n}**: {p}" for n, p in previous_positions.items() if n != agent_name])
                your_position = previous_positions.get(agent_name, "No initial position yet.")
                deliberation_input = self.deliberation_prompt.format(agent_name=agent_name, task=task, other_positions=other_positions, your_position=your_position)
                return await self._execute_agent(agent, deliberation_input, self.agent_timeout)

        results = await asyncio.gather(*[run_agent_deliberation(a, n) for a, n in zip(self._agents, self._agent_names)], return_exceptions=True)
        agent_results = [r if isinstance(r, WorkflowStepResult) else WorkflowStepResult(agent_name="unknown", agent_number=0, success=False, output="", error=str(r), start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc), duration_seconds=0.0) for r in results]
        return MeshRoundResult(round_num=len(self._round_results) + 1, agent_results=agent_results)

    async def execute(self, initial_input: str, agents: list) -> MeshSwarmResult:
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._round_results = []
        try:
            agent_configs = [self._parse_agent_config(spec) for spec in agents]
            num_agents = len(agent_configs)
            self._agents = []
            self._agent_names = []
            for i, config in enumerate(agent_configs):
                agent = await self._create_agent(config, i + 1)
                self._agents.append(agent)
                self._agent_names.append(config.name or f"agent_{i + 1}")
            current_positions = {name: "Initial position to be developed." for name in self._agent_names}
            for round_num in range(self.max_rounds):
                round_result = await self._run_round(initial_input, current_positions)
                self._round_results.append(round_result)
                current_positions = round_result.get_positions()
            final_positions_str = "\n".join([f"**{n}**: {p}" for n, p in current_positions.items()])
            consensus_input = self.consensus_prompt.format(task=initial_input, final_positions=final_positions_str)
            consensus_config = AgentConfig(name="consensus_agent", timeout=self.agent_timeout)
            consensus_agent = await self._create_agent(consensus_config, num_agents + 1)
            consensus_result = await self._execute_agent(consensus_agent, consensus_input, self.agent_timeout)
            final_output = consensus_result.output if consensus_result.success else current_positions.get(self._agent_names[0], "")
            self._end_time = datetime.now(timezone.utc)
            return MeshSwarmResult(workflow_id=self.workflow_id, status=WorkflowStatus.COMPLETED, rounds=self._round_results, consensus_result=consensus_result, final_output=final_output, total_duration_seconds=(self._end_time - self._start_time).total_seconds(), start_time=self._start_time, end_time=self._end_time, metadata={"num_agents": num_agents, "max_rounds": self.max_rounds})
        except Exception as e:
            self._end_time = datetime.now(timezone.utc)
            return MeshSwarmResult(workflow_id=self.workflow_id, status=WorkflowStatus.FAILED, rounds=self._round_results, consensus_result=None, final_output="", total_duration_seconds=(self._end_time - self._start_time).total_seconds(), start_time=self._start_time, end_time=self._end_time, metadata={"error": str(e)})


class swarm_mesh(Tool):
    """Tool for executing MeshSwarm fully-connected deliberation pattern."""

    async def execute(self, agents="", task="", max_rounds="3", workflow_id="", timeout="1500", agent_timeout="300", deliberation_prompt="", consensus_prompt="", max_concurrency="10", **kwargs):
        import json
        try:
            agent_list = self._parse_agents_param(agents)
            if not agent_list:
                return Response(message="Error: No agents specified for MeshSwarm", break_loop=False)
            workflow = MeshSwarm(parent_agent=self.agent, workflow_id=workflow_id, timeout=float(timeout), agent_timeout=float(agent_timeout), max_rounds=int(max_rounds), deliberation_prompt=deliberation_prompt or DEFAULT_MESH_DELIBERATION_PROMPT, consensus_prompt=consensus_prompt or DEFAULT_MESH_CONSENSUS_PROMPT, max_concurrency=int(max_concurrency))
            result = await workflow.execute(initial_input=task or self.message or "Deliberate on this topic.", agents=agent_list)
            return Response(message=self._format_result(result), break_loop=False, additional={"workflow_id": result.workflow_id, "status": result.status.value})
        except Exception as e:
            return Response(message=f"MeshSwarm failed: {e}", break_loop=False)

    def _parse_agents_param(self, agents: str) -> list:
        import json
        if not agents:
            return []
        agents = agents.strip()
        if agents.startswith("["):
            try:
                return json.loads(agents)
            except json.JSONDecodeError:
                pass
        return [name.strip() for name in agents.split(",") if name.strip()]

    def _format_result(self, result) -> str:
        lines = [f"# MeshSwarm: {result.workflow_id}", f"**Status**: {result.status.value.upper()}", f"**Duration**: {result.total_duration_seconds:.2f}s", f"**Rounds**: {len(result.rounds)}", ""]
        for r in result.rounds:
            lines.append(f"## Round {r.round_num}: {len([x for x in r.agent_results if x.success])}/{len(r.agent_results)} succeeded")
        lines.extend(["", "---", "", "## Final Output", result.final_output])
        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(type="tool", heading=f"icon://project-diagram {self.agent.agent_name}: Executing MeshSwarm Pattern", content="", kvps=self.args)


# =============================================================================
# GridSwarm Pattern
# =============================================================================

DEFAULT_GRID_CELL_PROMPT = """You are agent at grid position ({row}, {col}) in a {rows}x{cols} grid.
Grid execution mode: {mode}
Your assigned task: {task}
Context from previous cells: {context}
Provide your result:"""

DEFAULT_GRID_AGGREGATION_PROMPT = """You are a grid aggregation agent combining results from a {rows}x{cols} grid.
Results from all cells: {cell_results}
Provide the aggregated result:"""


class GridExecutionMode(Enum):
    """Execution mode for GridSwarm."""
    ROW_BY_ROW = "row_by_row"
    COLUMN_BY_COLUMN = "column_by_column"
    ALL_PARALLEL = "all_parallel"


@dataclass
class GridCellResult:
    """Result from a single grid cell execution."""
    row: int
    col: int
    agent_result: WorkflowStepResult

    @property
    def position(self) -> str:
        return f"({self.row}, {self.col})"


class GridSwarmResult:
    """Complete result from a GridSwarm execution."""

    def __init__(self, workflow_id: str, status: WorkflowStatus, rows: int, cols: int, mode: GridExecutionMode, cell_results: list, aggregation_result, final_output: str, total_duration_seconds: float = 0.0, start_time: datetime = None, end_time: datetime = None, metadata: dict = None):
        self.workflow_id = workflow_id
        self.status = status
        self.rows = rows
        self.cols = cols
        self.mode = mode
        self.cell_results = cell_results
        self.aggregation_result = aggregation_result
        self.final_output = final_output
        self.total_duration_seconds = total_duration_seconds
        self.start_time = start_time or datetime.now(timezone.utc)
        self.end_time = end_time
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {"workflow_id": self.workflow_id, "status": self.status.value, "grid_size": f"{self.rows}x{self.cols}", "mode": self.mode.value, "final_output": self.final_output, "total_duration_seconds": self.total_duration_seconds, "metadata": self.metadata}


class GridSwarm(BaseWorkflow):
    """Grid-based coordination pattern - agents arranged in a grid with configurable execution order."""

    def __init__(self, parent_agent: Agent, workflow_id: str = "", timeout: float = 1800.0, agent_timeout: float = 300.0, mode: GridExecutionMode = GridExecutionMode.ROW_BY_ROW, cell_prompt: str = "", aggregation_prompt: str = "", max_concurrency: int = 10):
        super().__init__(workflow_id=workflow_id or f"grid_{uuid.uuid4().hex[:8]}", timeout=timeout, fail_fast=False)
        self.parent_agent = parent_agent
        self.agent_timeout = agent_timeout
        self.mode = mode
        self.cell_prompt = cell_prompt or DEFAULT_GRID_CELL_PROMPT
        self.aggregation_prompt = aggregation_prompt or DEFAULT_GRID_AGGREGATION_PROMPT
        self.max_concurrency = max_concurrency
        self._agent_grid: dict = {}
        self._cell_results: list = []

    def _parse_agent_config(self, agent_spec) -> AgentConfig:
        if isinstance(agent_spec, AgentConfig):
            return agent_spec
        if isinstance(agent_spec, dict):
            return AgentConfig(name=agent_spec.get("name", ""), profile=agent_spec.get("profile", ""), prompt=agent_spec.get("prompt", ""), timeout=agent_spec.get("timeout", self.agent_timeout), system_prompt=agent_spec.get("system_prompt", ""))
        if isinstance(agent_spec, str):
            return AgentConfig(name=agent_spec, timeout=self.agent_timeout)
        raise ValueError(f"Invalid agent specification: {type(agent_spec)}")

    async def _create_agent(self, config: AgentConfig, agent_number: int, row: int, col: int) -> Agent:
        base_config = initialize_agent()
        if config.profile:
            base_config.profile = config.profile
        agent = Agent(number=self.parent_agent.number + agent_number, config=base_config, context=self.parent_agent.context)
        agent.set_data("_workflow_id", self.workflow_id)
        agent.set_data("_workflow_step", agent_number)
        agent.set_data(Agent.DATA_NAME_SUPERIOR, self.parent_agent)
        return agent

    async def _execute_agent(self, agent: Agent, input_message: str, timeout: float) -> WorkflowStepResult:
        step_start = datetime.now(timezone.utc)
        try:
            agent.hist_add_user_message(UserMessage(message=input_message, attachments=[]))
            result = await asyncio.wait_for(agent.monologue(), timeout=timeout)
            agent.history.new_topic()
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=True, output=result, error=None, start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())
        except asyncio.TimeoutError:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=False, output="", error=f"Timeout after {timeout}s", start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())
        except Exception as e:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(agent_name=agent.agent_name, agent_number=agent.number, success=False, output="", error=str(e), start_time=step_start, end_time=step_end, duration_seconds=(step_end - step_start).total_seconds())

    def _get_execution_order(self, rows: int, cols: int) -> list:
        if self.mode == GridExecutionMode.ROW_BY_ROW:
            return [(r, c) for r in range(rows) for c in range(cols)]
        elif self.mode == GridExecutionMode.COLUMN_BY_COLUMN:
            return [(r, c) for c in range(cols) for r in range(rows)]
        else:
            return [(r, c) for r in range(rows) for c in range(cols)]

    def _parse_grid_size(self, grid_size: str, num_agents: int) -> tuple:
        if grid_size:
            try:
                parts = grid_size.lower().split("x")
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
            except (ValueError, AttributeError):
                pass
        import math
        cols = int(math.ceil(math.sqrt(num_agents)))
        rows = int(math.ceil(num_agents / cols))
        return rows, cols

    async def _execute_cell(self, row: int, col: int, task: str, rows: int, cols: int, context: str) -> GridCellResult:
        agent = self._agent_grid.get((row, col))
        if not agent:
            return GridCellResult(row=row, col=col, agent_result=WorkflowStepResult(agent_name="unknown", agent_number=0, success=False, output="", error="Agent not found", start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc), duration_seconds=0.0))
        cell_input = self.cell_prompt.format(row=row + 1, col=col + 1, rows=rows, cols=cols, mode=self.mode.value, task=task, context=context)
        result = await self._execute_agent(agent, cell_input, self.agent_timeout)
        return GridCellResult(row=row, col=col, agent_result=result)

    async def execute(self, initial_input: str, agents: list, grid_size: str = "") -> GridSwarmResult:
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._cell_results = []
        self._agent_grid = {}
        try:
            agent_configs = [self._parse_agent_config(spec) for spec in agents]
            num_agents = len(agent_configs)
            rows, cols = self._parse_grid_size(grid_size, num_agents)
            agent_idx = 0
            for r in range(rows):
                for c in range(cols):
                    config = agent_configs[agent_idx % len(agent_configs)]
                    agent = await self._create_agent(config, agent_idx + 1, r, c)
                    self._agent_grid[(r, c)] = agent
                    agent_idx += 1
            execution_order = self._get_execution_order(rows, cols)
            context = ""
            for pos in execution_order:
                result = await self._execute_cell(pos[0], pos[1], initial_input, rows, cols, context)
                self._cell_results.append(result)
                if result.agent_result.success:
                    context += f"\nCell {result.position}: {result.agent_result.output}"
            cell_results_str = "\n".join([f"Cell {cr.position}: {cr.agent_result.output if cr.agent_result.success else '[ERROR]'}" for cr in self._cell_results])
            aggregation_input = self.aggregation_prompt.format(rows=rows, cols=cols, mode=self.mode.value, cell_results=cell_results_str)
            aggregation_config = AgentConfig(name="grid_aggregator", timeout=self.agent_timeout)
            aggregation_agent = await self._create_agent(aggregation_config, num_agents + 1, -1, -1)
            aggregation_result = await self._execute_agent(aggregation_agent, aggregation_input, self.agent_timeout)
            final_output = aggregation_result.output if aggregation_result.success else "\n".join([cr.agent_result.output for cr in self._cell_results if cr.agent_result.success])
            self._end_time = datetime.now(timezone.utc)
            return GridSwarmResult(workflow_id=self.workflow_id, status=WorkflowStatus.COMPLETED, rows=rows, cols=cols, mode=self.mode, cell_results=self._cell_results, aggregation_result=aggregation_result, final_output=final_output, total_duration_seconds=(self._end_time - self._start_time).total_seconds(), start_time=self._start_time, end_time=self._end_time, metadata={"grid_size": f"{rows}x{cols}", "mode": self.mode.value, "total_cells": len(self._cell_results)})
        except Exception as e:
            self._end_time = datetime.now(timezone.utc)
            return GridSwarmResult(workflow_id=self.workflow_id, status=WorkflowStatus.FAILED, rows=0, cols=0, mode=self.mode, cell_results=self._cell_results, aggregation_result=None, final_output="", total_duration_seconds=(self._end_time - self._start_time).total_seconds(), start_time=self._start_time, end_time=self._end_time, metadata={"error": str(e)})


class swarm_grid(Tool):
    """Tool for executing GridSwarm grid-based coordination pattern."""

    async def execute(self, agents="", task="", grid_size="", mode="row_by_row", workflow_id="", timeout="1800", agent_timeout="300", cell_prompt="", aggregation_prompt="", max_concurrency="10", **kwargs):
        import json
        try:
            agent_list = self._parse_agents_param(agents)
            if not agent_list:
                return Response(message="Error: No agents specified for GridSwarm", break_loop=False)
            mode_map = {"row_by_row": GridExecutionMode.ROW_BY_ROW, "column_by_column": GridExecutionMode.COLUMN_BY_COLUMN, "all_parallel": GridExecutionMode.ALL_PARALLEL}
            execution_mode = mode_map.get(mode.lower(), GridExecutionMode.ROW_BY_ROW)
            workflow = GridSwarm(parent_agent=self.agent, workflow_id=workflow_id, timeout=float(timeout), agent_timeout=float(agent_timeout), mode=execution_mode, cell_prompt=cell_prompt or DEFAULT_GRID_CELL_PROMPT, aggregation_prompt=aggregation_prompt or DEFAULT_GRID_AGGREGATION_PROMPT, max_concurrency=int(max_concurrency))
            result = await workflow.execute(initial_input=task or self.message or "Process this task using grid execution.", agents=agent_list, grid_size=grid_size)
            return Response(message=self._format_result(result), break_loop=False, additional={"workflow_id": result.workflow_id, "status": result.status.value, "grid_size": f"{result.rows}x{result.cols}"})
        except Exception as e:
            return Response(message=f"GridSwarm failed: {e}", break_loop=False)

    def _parse_agents_param(self, agents: str) -> list:
        import json
        if not agents:
            return []
        agents = agents.strip()
        if agents.startswith("["):
            try:
                return json.loads(agents)
            except json.JSONDecodeError:
                pass
        return [name.strip() for name in agents.split(",") if name.strip()]

    def _format_result(self, result) -> str:
        lines = [f"# GridSwarm: {result.workflow_id}", f"**Status**: {result.status.value.upper()}", f"**Duration**: {result.total_duration_seconds:.2f}s", f"**Grid**: {result.rows}x{result.cols} ({result.mode.value})", ""]
        successful = len([cr for cr in result.cell_results if cr.agent_result.success])
        lines.append(f"**Cells**: {successful}/{len(result.cell_results)} succeeded")
        lines.extend(["", "---", "", "## Final Output", result.final_output])
        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(type="tool", heading=f"icon://th {self.agent.agent_name}: Executing GridSwarm Pattern", content="", kvps=self.args)

# ===== Swarm Router Pattern =====

from typing import Dict, Any
import hashlib

@dataclass
class RoutingDecision:
    selected_agent: str
    reason: str
    confidence: float

@dataclass
class RouterResult(WorkflowResult):
    routing_decisions: List[RoutingDecision] = None
    
    def __post_init__(self):
        if self.routing_decisions is None:
            self.routing_decisions = []


class SwarmRouter(BaseWorkflow):
    """
    Route tasks to the most appropriate agent based on task characteristics.
    Uses an LLM to analyze the task and select the best agent.
    """
    
    def __init__(
        self,
        agents: List[AgentConfig],
        router_agent: AgentConfig,
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 600,
        agent_timeout: int = 300
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.agents = agents
        self.router_agent = router_agent
        self.agent_timeout = agent_timeout
    
    async def execute(self, task: str) -> RouterResult:
        """Route the task to the most appropriate agent."""
        start_time = asyncio.get_event_loop().time()
        result = RouterResult(
            workflow_id=self.workflow_id,
            workflow_type="swarm_router",
            status=WorkflowStatus.RUNNING,
            steps=[],
            routing_decisions=[],
            final_output="",
            timing={}
        )
        
        try:
            # Create router agent
            router = await self._create_agent(self.router_agent)
            
            # Build agent descriptions
            agent_descriptions = []
            for agent in self.agents:
                desc = f"- {agent.name}: {agent.system_prompt or 'No description'}"
                agent_descriptions.append(desc)
            
            # Ask router to select the best agent
            routing_prompt = (
                f"You are a task routing expert. Select the best agent to handle this task.\n\n"
                f"Available Agents:\n{chr(10).join(agent_descriptions)}\n\n"
                f"Task: {task}\n\n"
                f"Respond ONLY with JSON in this exact format:\n"
                f"{{\n"
                f"  \"selected_agent\": \"agent_name\",\n"
                f"  \"reason\": \"explanation\",\n"
                f"  \"confidence\": 0.95\n"
                f"}}"
            )
            
            routing_start = asyncio.get_event_loop().time()
            routing_response = await asyncio.wait_for(
                router.run(routing_prompt),
                timeout=self.agent_timeout
            )
            routing_duration = asyncio.get_event_loop().time() - routing_start
            
            # Parse routing decision
            try:
                routing_json = json.loads(routing_response)
                selected_agent_name = routing_json["selected_agent"]
                reason = routing_json["reason"]
                confidence = routing_json["confidence"]
            except:
                # Fallback to first agent if parsing fails
                selected_agent_name = self.agents[0].name
                reason = "Fallback selection due to parsing error"
                confidence = 0.5
            
            routing_decision = RoutingDecision(
                selected_agent=selected_agent_name,
                reason=reason,
                confidence=confidence
            )
            result.routing_decisions.append(routing_decision)
            
            result.steps.append(WorkflowStepResult(
                agent_name=self.router_agent.name,
                agent_number=router.number,
                success=True,
                output=json.dumps(routing_json, indent=2),
                error=None,
                timing={"duration": routing_duration}
            ))
            
            # Find and execute the selected agent
            selected_agent_config = None
            for agent in self.agents:
                if agent.name == selected_agent_name:
                    selected_agent_config = agent
                    break
            
            if selected_agent_config:
                selected_agent = await self._create_agent(selected_agent_config)
                
                execution_start = asyncio.get_event_loop().time()
                final_output = await asyncio.wait_for(
                    selected_agent.run(task),
                    timeout=self.agent_timeout
                )
                execution_duration = asyncio.get_event_loop().time() - execution_start
                
                result.final_output = final_output
                result.steps.append(WorkflowStepResult(
                    agent_name=selected_agent_config.name,
                    agent_number=selected_agent.number,
                    success=True,
                    output=final_output,
                    error=None,
                    timing={"duration": execution_duration}
                ))
            else:
                error_msg = f"Selected agent '{selected_agent_name}' not found in agent list"
                result.status = WorkflowStatus.FAILED
                result.error = error_msg
                return result
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"Router workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result


class swarm_router(Tool):
    """Route tasks to the most appropriate agent using intelligent routing."""
    
    async def execute(
        self,
        agents: str,
        router: str,
        task: str,
        timeout: str = "600",
        agent_timeout: str = "300",
        **kwargs
    ) -> Response:
        """Execute intelligent task routing."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 600
            agent_timeout_int = int(agent_timeout) if agent_timeout.isdigit() else 300
            
            # Parse agents
            agent_configs = []
            if isinstance(agents, str):
                try:
                    agents_list = json.loads(agents)
                    if not isinstance(agents_list, list):
                        raise ValueError()
                except:
                    agents_list = [a.strip() for a in agents.split(",") if a.strip()]
                
                for agent_spec in agents_list:
                    agent_configs.append(self._parse_agent_spec(agent_spec))
            
            # Parse router agent
            router_config = self._parse_agent_spec(router)
            
            # Create and execute workflow
            workflow = SwarmRouter(
                agents=agent_configs,
                router_agent=router_config,
                parent_agent=self.agent,
                timeout=timeout_int,
                agent_timeout=agent_timeout_int
            )
            
            result = await workflow.execute(task)
            
            # Format response
            response_parts = [
                f"# 🔄 Swarm Router Decision",
                f"**Task**: {task}",
                f"**Status**: {result.status.value}",
                "",
                f"## Routing Decisions",
            ]
            
            for decision in result.routing_decisions:
                response_parts.extend([
                    f"### Selected Agent: {decision.selected_agent}",
                    f"**Reason**: {decision.reason}",
                    f"**Confidence**: {decision.confidence:.2f}",
                    ""
                ])
            
            response_parts.extend([
                "## Final Output",
                f"> {result.final_output}",
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "swarm_router"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing swarm router: {str(e)}",
                break_loop=False
            )

# ===== RoundRobinSwarm Pattern =====

@dataclass
class RoundRobinResult(WorkflowResult):
    rounds: List[List[WorkflowStepResult]] = None
    
    def __post_init__(self):
        if self.rounds is None:
            self.rounds = []


class RoundRobinSwarm(BaseWorkflow):
    """
    Agents take turns in a round-robin fashion to contribute to a task.
    Each agent gets a chance to respond in sequence for multiple rounds.
    """
    
    def __init__(
        self,
        agents: List[AgentConfig],
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 600,
        agent_timeout: int = 300,
        rounds: int = 3
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.agents = agents
        self.agent_timeout = agent_timeout
        self.rounds = rounds
    
    async def execute(self, task: str) -> RoundRobinResult:
        """Execute the round-robin workflow."""
        start_time = asyncio.get_event_loop().time()
        result = RoundRobinResult(
            workflow_id=self.workflow_id,
            workflow_type="round_robin_swarm",
            status=WorkflowStatus.RUNNING,
            steps=[],
            rounds=[],
            final_output="",
            timing={}
        )
        
        try:
            # Create all agents
            agent_instances = []
            for agent_config in self.agents:
                agent_instance = await self._create_agent(agent_config)
                agent_instances.append(agent_instance)
            
            # Execute rounds
            current_context = task
            all_responses = []
            
            for round_num in range(self.rounds):
                round_steps = []
                round_responses = []
                
                for i, (agent_config, agent_instance) in enumerate(zip(self.agents, agent_instances)):
                    # Prepare prompt with context from previous responses
                    context_summary = "\n\nPrevious contributions:\n" + "\n".join(all_responses) if all_responses else ""
                    prompt = (
                        f"Round {round_num + 1}, Turn {i + 1}\n"
                        f"Task: {task}\n"
                        f"Current context:{context_summary}\n\n"
                        f"Please contribute to this task based on your expertise."
                    )
                    
                    step_start = asyncio.get_event_loop().time()
                    try:
                        response = await asyncio.wait_for(
                            agent_instance.run(prompt),
                            timeout=self.agent_timeout
                        )
                        step_duration = asyncio.get_event_loop().time() - step_start
                        
                        step_result = WorkflowStepResult(
                            agent_name=agent_config.name,
                            agent_number=agent_instance.number,
                            success=True,
                            output=response,
                            error=None,
                            timing={"duration": step_duration}
                        )
                        
                        round_steps.append(step_result)
                        round_responses.append(f"{agent_config.name}: {response}")
                        all_responses.append(f"{agent_config.name}: {response}")
                        
                    except Exception as e:
                        step_duration = asyncio.get_event_loop().time() - step_start
                        step_result = WorkflowStepResult(
                            agent_name=agent_config.name,
                            agent_number=agent_instance.number,
                            success=False,
                            output="",
                            error=str(e),
                            timing={"duration": step_duration}
                        )
                        round_steps.append(step_result)
                
                result.rounds.append(round_steps)
                result.steps.extend(round_steps)
                
                # Update context for next round
                current_context = "\n".join(round_responses)
            
            # Synthesize final output
            synthesis_prompt = (
                f"Synthesize these contributions into a coherent final response:\n\n"
                f"Task: {task}\n\n"
                f"Contributions:\n{chr(10).join(all_responses)}\n\n"
                f"Provide the best synthesized answer to the original task."
            )
            
            # Use the first agent for synthesis
            synthesis_agent = agent_instances[0]
            synthesis_start = asyncio.get_event_loop().time()
            final_output = await asyncio.wait_for(
                synthesis_agent.run(synthesis_prompt),
                timeout=self.agent_timeout
            )
            synthesis_duration = asyncio.get_event_loop().time() - synthesis_start
            
            result.final_output = final_output
            result.steps.append(WorkflowStepResult(
                agent_name=self.agents[0].name,
                agent_number=synthesis_agent.number,
                success=True,
                output=final_output,
                error=None,
                timing={"duration": synthesis_duration}
            ))
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"RoundRobin workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result


class swarm_round_robin(Tool):
    """Execute a round-robin workflow where agents take turns contributing."""
    
    async def execute(
        self,
        agents: str,
        task: str,
        timeout: str = "600",
        agent_timeout: str = "300",
        rounds: str = "3",
        **kwargs
    ) -> Response:
        """Execute round-robin workflow."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 600
            agent_timeout_int = int(agent_timeout) if agent_timeout.isdigit() else 300
            rounds_int = int(rounds) if rounds.isdigit() else 3
            
            # Parse agents
            agent_configs = []
            if isinstance(agents, str):
                try:
                    agents_list = json.loads(agents)
                    if not isinstance(agents_list, list):
                        raise ValueError()
                except:
                    agents_list = [a.strip() for a in agents.split(",") if a.strip()]
                
                for agent_spec in agents_list:
                    agent_configs.append(self._parse_agent_spec(agent_spec))
            
            # Create and execute workflow
            workflow = RoundRobinSwarm(
                agents=agent_configs,
                parent_agent=self.agent,
                timeout=timeout_int,
                agent_timeout=agent_timeout_int,
                rounds=rounds_int
            )
            
            result = await workflow.execute(task)
            
            # Format response
            response_parts = [
                f"# 🔁 Round-Robin Swarm",
                f"**Task**: {task}",
                f"**Status**: {result.status.value}",
                f"**Rounds**: {rounds_int}",
                "",
                f"## Round Details",
            ]
            
            for i, round_steps in enumerate(result.rounds):
                response_parts.append(f"### Round {i + 1}")
                for step in round_steps:
                    if step.success:
                        response_parts.extend([
                            f"**{step.agent_name}**: {step.output}",
                            ""
                        ])
                    else:
                        response_parts.extend([
                            f"**{step.agent_name}**: ⚠️ Error - {step.error}",
                            ""
                        ])
            
            response_parts.extend([
                "## Final Synthesized Output",
                f"> {result.final_output}",
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "round_robin_swarm"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing round-robin swarm: {str(e)}",
                break_loop=False
            )

# ===== GroupChat Pattern =====

@dataclass
class GroupMessage:
    sender: str
    content: str
    timestamp: float

@dataclass
class GroupChatResult(WorkflowResult):
    messages: List[GroupMessage] = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []


class GroupChat(BaseWorkflow):
    """
    Multi-agent conversation where agents can freely exchange messages.
    Agents decide when to contribute or when the conversation is complete.
    """
    
    def __init__(
        self,
        agents: List[AgentConfig],
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 600,
        agent_timeout: int = 300,
        max_rounds: int = 10
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.agents = agents
        self.agent_timeout = agent_timeout
        self.max_rounds = max_rounds
    
    async def execute(self, task: str) -> GroupChatResult:
        """Execute the group chat conversation."""
        start_time = asyncio.get_event_loop().time()
        result = GroupChatResult(
            workflow_id=self.workflow_id,
            workflow_type="group_chat",
            status=WorkflowStatus.RUNNING,
            steps=[],
            messages=[],
            final_output="",
            timing={}
        )
        
        try:
            # Create all agents
            agent_instances = {}
            for agent_config in self.agents:
                agent_instance = await self._create_agent(agent_config)
                agent_instances[agent_config.name] = agent_instance
            
            # Initialize conversation with task
            conversation_history = [
                GroupMessage(sender="SYSTEM", content=f"Task to discuss: {task}", timestamp=time.time())
            ]
            result.messages.append(conversation_history[0])
            
            # Execute conversation rounds
            for round_num in range(self.max_rounds):
                round_messages = []
                
                # Each agent gets a chance to speak
                for agent_config in self.agents:
                    agent_instance = agent_instances[agent_config.name]
                    
                    # Build conversation context
                    context_lines = [f"[{msg.timestamp}] {msg.sender}: {msg.content}" for msg in conversation_history]
                    context = "\n".join(context_lines)
                    
                    # Prompt agent to contribute or conclude
                    prompt = (
                        f"Group Chat - Round {round_num + 1}\n"
                        f"Current conversation:\n{context}\n\n"
                        f"You are {agent_config.name}. Either contribute meaningfully to the discussion "
                        f"or if you believe the task is complete, respond with exactly: CONCLUDE: <final_answer>"
                    )
                    
                    step_start = asyncio.get_event_loop().time()
                    try:
                        response = await asyncio.wait_for(
                            agent_instance.run(prompt),
                            timeout=self.agent_timeout
                        )
                        step_duration = asyncio.get_event_loop().time() - step_start
                        
                        # Check if agent wants to conclude
                        if response.strip().startswith("CONCLUDE:"):
                            final_answer = response.strip()[9:].strip()  # Remove "CONCLUDE: " prefix
                            
                            result.final_output = final_answer
                            result.status = WorkflowStatus.COMPLETED
                            
                            # Add concluding message
                            conclude_msg = GroupMessage(
                                sender=agent_config.name,
                                content=f"CONCLUDE: {final_answer}",
                                timestamp=time.time()
                            )
                            conversation_history.append(conclude_msg)
                            result.messages.append(conclude_msg)
                            
                            step_result = WorkflowStepResult(
                                agent_name=agent_config.name,
                                agent_number=agent_instance.number,
                                success=True,
                                output=response,
                                error=None,
                                timing={"duration": step_duration}
                            )
                            result.steps.append(step_result)
                            
                            return result
                        
                        # Regular contribution
                        message = GroupMessage(
                            sender=agent_config.name,
                            content=response,
                            timestamp=time.time()
                        )
                        conversation_history.append(message)
                        result.messages.append(message)
                        
                        step_result = WorkflowStepResult(
                            agent_name=agent_config.name,
                            agent_number=agent_instance.number,
                            success=True,
                            output=response,
                            error=None,
                            timing={"duration": step_duration}
                        )
                        result.steps.append(step_result)
                        round_messages.append(message)
                        
                    except Exception as e:
                        step_duration = asyncio.get_event_loop().time() - step_start
                        step_result = WorkflowStepResult(
                            agent_name=agent_config.name,
                            agent_number=agent_instance.number,
                            success=False,
                            output="",
                            error=str(e),
                            timing={"duration": step_duration}
                        )
                        result.steps.append(step_result)
                
                # If no one concluded and we've reached max rounds, synthesize final output
                if round_num == self.max_rounds - 1:
                    synthesis_prompt = (
                        f"The group chat has reached its maximum rounds. Synthesize the discussion "
                        f"into a coherent final response to the original task:\n\n"
                        f"Task: {task}\n\n"
                        f"Discussion:\n{context}\n\n"
                        f"Provide the best synthesized answer to the original task."
                    )
                    
                    # Use the first agent for synthesis
                    synthesis_agent = agent_instances[self.agents[0].name]
                    synthesis_start = asyncio.get_event_loop().time()
                    final_output = await asyncio.wait_for(
                        synthesis_agent.run(synthesis_prompt),
                        timeout=self.agent_timeout
                    )
                    synthesis_duration = asyncio.get_event_loop().time() - synthesis_start
                    
                    result.final_output = final_output
                    result.status = WorkflowStatus.COMPLETED
                    
                    synthesis_msg = GroupMessage(
                        sender="SYNTHESIS",
                        content=final_output,
                        timestamp=time.time()
                    )
                    result.messages.append(synthesis_msg)
                    
                    result.steps.append(WorkflowStepResult(
                        agent_name=self.agents[0].name,
                        agent_number=synthesis_agent.number,
                        success=True,
                        output=final_output,
                        error=None,
                        timing={"duration": synthesis_duration}
                    ))
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"GroupChat workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result


class swarm_group_chat(Tool):
    """Execute a group chat conversation among multiple agents."""
    
    async def execute(
        self,
        agents: str,
        task: str,
        timeout: str = "600",
        agent_timeout: str = "300",
        max_rounds: str = "10",
        **kwargs
    ) -> Response:
        """Execute group chat workflow."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 600
            agent_timeout_int = int(agent_timeout) if agent_timeout.isdigit() else 300
            max_rounds_int = int(max_rounds) if max_rounds.isdigit() else 10
            
            # Parse agents
            agent_configs = []
            if isinstance(agents, str):
                try:
                    agents_list = json.loads(agents)
                    if not isinstance(agents_list, list):
                        raise ValueError()
                except:
                    agents_list = [a.strip() for a in agents.split(",") if a.strip()]
                
                for agent_spec in agents_list:
                    agent_configs.append(self._parse_agent_spec(agent_spec))
            
            # Create and execute workflow
            workflow = GroupChat(
                agents=agent_configs,
                parent_agent=self.agent,
                timeout=timeout_int,
                agent_timeout=agent_timeout_int,
                max_rounds=max_rounds_int
            )
            
            result = await workflow.execute(task)
            
            # Format response
            response_parts = [
                f"# 💬 Group Chat Conversation",
                f"**Task**: {task}",
                f"**Status**: {result.status.value}",
                f"**Messages**: {len(result.messages)}",
                "",
                f"## Conversation Transcript",
            ]
            
            for message in result.messages:
                timestamp = datetime.fromtimestamp(message.timestamp).strftime('%H:%M:%S')
                response_parts.append(f"**[{timestamp}] {message.sender}**: {message.content}")
            
            response_parts.extend([
                "",
                f"## Final Output",
                f"> {result.final_output}",
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "group_chat"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing group chat: {str(e)}",
                break_loop=False
            )

# ===== ForestSwarm Pattern =====

@dataclass
class TreeNode:
    id: str
    agent_config: AgentConfig
    children: List[str] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

@dataclass
class ForestResult(WorkflowResult):
    tree_structures: List[Dict[str, TreeNode]] = None
    node_results: Dict[str, WorkflowStepResult] = None
    
    def __post_init__(self):
        if self.tree_structures is None:
            self.tree_structures = []
        if self.node_results is None:
            self.node_results = {}


class ForestSwarm(BaseWorkflow):
    """
    Tree-structured agent organization with multiple independent trees.
    Each tree has a root node with child nodes forming a hierarchy.
    """
    
    def __init__(
        self,
        trees: List[Dict[str, dict]],  # List of tree definitions
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 900,
        agent_timeout: int = 300
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.trees = trees
        self.agent_timeout = agent_timeout
    
    async def execute(self, task: str) -> ForestResult:
        """Execute the forest swarm workflow."""
        start_time = asyncio.get_event_loop().time()
        result = ForestResult(
            workflow_id=self.workflow_id,
            workflow_type="forest_swarm",
            status=WorkflowStatus.RUNNING,
            steps=[],
            tree_structures=[],
            node_results={},
            final_output="",
            timing={}
        )
        
        try:
            # Parse tree structures
            parsed_trees = []
            for tree_def in self.trees:
                parsed_tree = {}
                for node_id, node_data in tree_def.items():
                    agent_config = self._parse_agent_config(node_data.get("agent"))
                    children = node_data.get("children", [])
                    parsed_tree[node_id] = TreeNode(
                        id=node_id,
                        agent_config=agent_config,
                        children=children
                    )
                parsed_trees.append(parsed_tree)
            
            result.tree_structures = parsed_trees
            
            # Execute each tree
            tree_outputs = []
            for i, tree in enumerate(parsed_trees):
                tree_output = await self._execute_tree(tree, task, result)
                tree_outputs.append({
                    "tree_index": i,
                    "output": tree_output
                })
            
            # Synthesize final output from all trees
            synthesis_prompt = (
                f"Synthesize these tree outputs into a coherent final response:\n\n"
                f"Task: {task}\n\n"
                f"Tree Outputs:\n{json.dumps(tree_outputs, indent=2)}\n\n"
                f"Provide the best synthesized answer to the original task."
            )
            
            # Use the first agent for synthesis
            first_tree = parsed_trees[0]
            first_node_id = list(first_tree.keys())[0]
            synthesis_agent = await self._create_agent(first_tree[first_node_id].agent_config)
            
            synthesis_start = asyncio.get_event_loop().time()
            final_output = await asyncio.wait_for(
                synthesis_agent.run(synthesis_prompt),
                timeout=self.agent_timeout
            )
            synthesis_duration = asyncio.get_event_loop().time() - synthesis_start
            
            result.final_output = final_output
            result.steps.append(WorkflowStepResult(
                agent_name=first_tree[first_node_id].agent_config.name,
                agent_number=synthesis_agent.number,
                success=True,
                output=final_output,
                error=None,
                timing={"duration": synthesis_duration}
            ))
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"ForestSwarm workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result
    
    async def _execute_tree(
        self, 
        tree: Dict[str, TreeNode], 
        task: str, 
        result: ForestResult
    ) -> str:
        """Execute a single tree in the forest."""
        # Find root nodes (nodes not referenced as children)
        all_children = set()
        for node in tree.values():
            all_children.update(node.children)
        
        root_nodes = [node_id for node_id in tree.keys() if node_id not in all_children]
        
        # Execute tree starting from root nodes
        node_outputs = {}
        execution_queue = asyncio.Queue()
        
        # Add root nodes to queue
        for root_id in root_nodes:
            await execution_queue.put((root_id, task))
        
        # Process nodes in queue
        while not execution_queue.empty():
            node_id, input_data = await execution_queue.get()
            node = tree[node_id]
            
            # Skip if already executed
            if node_id in node_outputs:
                continue
            
            # Collect inputs from parent nodes
            parent_outputs = []
            for potential_parent_id, potential_parent in tree.items():
                if node_id in potential_parent.children:
                    if potential_parent_id in node_outputs:
                        parent_outputs.append(node_outputs[potential_parent_id])
            
            # Build prompt with task and parent outputs
            if parent_outputs:
                context = "\n\nContext from parent nodes:\n" + "\n".join(parent_outputs)
            else:
                context = f"\n\nOriginal task: {task}"
            
            prompt = f"Node {node_id}{context}\n\nPlease process this task based on your role."
            
            # Execute node
            step_start = asyncio.get_event_loop().time()
            try:
                agent = await self._create_agent(node.agent_config)
                output = await asyncio.wait_for(
                    agent.run(prompt),
                    timeout=self.agent_timeout
                )
                step_duration = asyncio.get_event_loop().time() - step_start
                
                node_outputs[node_id] = output
                
                step_result = WorkflowStepResult(
                    agent_name=node.agent_config.name,
                    agent_number=agent.number,
                    success=True,
                    output=output,
                    error=None,
                    timing={"duration": step_duration}
                )
                result.steps.append(step_result)
                result.node_results[node_id] = step_result
                
                # Add children to queue
                for child_id in node.children:
                    if child_id in tree:
                        await execution_queue.put((child_id, output))
                        
            except Exception as e:
                step_duration = asyncio.get_event_loop().time() - step_start
                step_result = WorkflowStepResult(
                    agent_name=node.agent_config.name,
                    agent_number=-1,
                    success=False,
                    output="",
                    error=str(e),
                    timing={"duration": step_duration}
                )
                result.steps.append(step_result)
                result.node_results[node_id] = step_result
        
        # Return output from leaf nodes or root if no children
        leaf_outputs = []
        for node_id, node in tree.items():
            if not node.children:  # Leaf node
                if node_id in node_outputs:
                    leaf_outputs.append(node_outputs[node_id])
        
        if leaf_outputs:
            return "\n".join(leaf_outputs)
        elif root_nodes and root_nodes[0] in node_outputs:
            return node_outputs[root_nodes[0]]
        else:
            return "No output generated"


class swarm_forest(Tool):
    """Execute a forest swarm workflow with multiple tree structures."""
    
    async def execute(
        self,
        trees: str,
        task: str,
        timeout: str = "900",
        agent_timeout: str = "300",
        **kwargs
    ) -> Response:
        """Execute forest swarm workflow."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 900
            agent_timeout_int = int(agent_timeout) if agent_timeout.isdigit() else 300
            
            # Parse trees
            trees_data = []
            if isinstance(trees, str):
                try:
                    trees_data = json.loads(trees)
                    if not isinstance(trees_data, list):
                        raise ValueError()
                except Exception as e:
                    return Response(
                        message=f"Error parsing trees JSON: {str(e)}",
                        break_loop=False
                    )
            
            # Create and execute workflow
            workflow = ForestSwarm(
                trees=trees_data,
                parent_agent=self.agent,
                timeout=timeout_int,
                agent_timeout=agent_timeout_int
            )
            
            result = await workflow.execute(task)
            
            # Format response
            response_parts = [
                f"# 🌲 Forest Swarm",
                f"**Task**: {task}",
                f"**Status**: {result.status.value}",
                f"**Trees**: {len(result.tree_structures)}",
                "",
                f"## Tree Structures",
            ]
            
            for i, tree in enumerate(result.tree_structures):
                response_parts.append(f"### Tree {i + 1}")
                for node_id, node in tree.items():
                    children_str = ", ".join(node.children) if node.children else "None"
                    response_parts.append(f"- **{node_id}** ({node.agent_config.name}) → Children: {children_str}")
                response_parts.append("")
            
            response_parts.append("## Node Execution Results")
            for node_id, step_result in result.node_results.items():
                if step_result.success:
                    response_parts.append(f"- **{node_id}** ({step_result.agent_name}): {step_result.output[:100]}...")
                else:
                    response_parts.append(f"- **{node_id}** ({step_result.agent_name}): ⚠️ Error - {step_result.error}")
            
            response_parts.extend([
                "",
                "## Final Synthesized Output",
                f"> {result.final_output}",
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "forest_swarm"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing forest swarm: {str(e)}",
                break_loop=False
            )

# ===== SpreadSheetSwarm Pattern =====

@dataclass
class CellResult:
    row: int
    col: int
    agent_name: str
    output: str
    success: bool
    error: str = None

@dataclass
class SpreadSheetResult(WorkflowResult):
    grid_size: dict = None
    cell_results: List[CellResult] = None
    
    def __post_init__(self):
        if self.grid_size is None:
            self.grid_size = {"rows": 0, "cols": 0}
        if self.cell_results is None:
            self.cell_results = []


class SpreadSheetSwarm(BaseWorkflow):
    """
    Agents arranged in a grid/spreadsheet pattern.
    Each cell contains an agent that processes data.
    Supports row-wise, column-wise, or parallel execution.
    """
    
    def __init__(
        self,
        agents: List[AgentConfig],
        rows: int,
        cols: int,
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 900,
        agent_timeout: int = 300,
        execution_mode: str = "parallel"  # row_by_row, column_by_column, parallel
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.agents = agents
        self.rows = rows
        self.cols = cols
        self.agent_timeout = agent_timeout
        self.execution_mode = execution_mode
        
        # Validate grid size
        if len(agents) < rows * cols:
            raise ValueError(f"Not enough agents ({len(agents)}) for grid size ({rows}x{cols}={rows*cols})")
    
    async def execute(self, task: str) -> SpreadSheetResult:
        """Execute the spreadsheet swarm workflow."""
        start_time = asyncio.get_event_loop().time()
        result = SpreadSheetResult(
            workflow_id=self.workflow_id,
            workflow_type="spreadsheet_swarm",
            status=WorkflowStatus.RUNNING,
            steps=[],
            grid_size={"rows": self.rows, "cols": self.cols},
            cell_results=[],
            final_output="",
            timing={}
        )
        
        try:
            # Create all agents
            agent_instances = []
            for agent_config in self.agents:
                agent_instance = await self._create_agent(agent_config)
                agent_instances.append(agent_instance)
            
            # Execute based on mode
            if self.execution_mode == "row_by_row":
                await self._execute_row_by_row(agent_instances, task, result)
            elif self.execution_mode == "column_by_column":
                await self._execute_column_by_column(agent_instances, task, result)
            else:  # parallel
                await self._execute_parallel(agent_instances, task, result)
            
            # Synthesize final output
            synthesis_prompt = (
                f"Synthesize these cell results into a coherent final response:\n\n"
                f"Task: {task}\n\n"
                f"Cell Results:\n{json.dumps([{'row': cr.row, 'col': cr.col, 'agent': cr.agent_name, 'output': cr.output} for cr in result.cell_results], indent=2)}\n\n"
                f"Provide the best synthesized answer to the original task."
            )
            
            # Use the first agent for synthesis
            synthesis_agent = agent_instances[0]
            synthesis_start = asyncio.get_event_loop().time()
            final_output = await asyncio.wait_for(
                synthesis_agent.run(synthesis_prompt),
                timeout=self.agent_timeout
            )
            synthesis_duration = asyncio.get_event_loop().time() - synthesis_start
            
            result.final_output = final_output
            result.steps.append(WorkflowStepResult(
                agent_name=self.agents[0].name,
                agent_number=synthesis_agent.number,
                success=True,
                output=final_output,
                error=None,
                timing={"duration": synthesis_duration}
            ))
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"SpreadSheetSwarm workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result
    
    async def _execute_row_by_row(
        self, 
        agent_instances: List["Agent"], 
        task: str, 
        result: SpreadSheetResult
    ):
        """Execute agents row by row."""
        for row in range(self.rows):
            row_results = []
            for col in range(self.cols):
                idx = row * self.cols + col
                agent_config = self.agents[idx]
                agent_instance = agent_instances[idx]
                
                # Build context from previous row if exists
                context = f"\n\nOriginal task: {task}"
                if row > 0:
                    prev_row_results = [cr for cr in result.cell_results if cr.row == row - 1]
                    if prev_row_results:
                        context += "\n\nResults from previous row:\n" + "\n".join([f"Col {cr.col}: {cr.output}" for cr in prev_row_results])
                
                prompt = f"Spreadsheet Cell [{row},{col}]{context}\n\nPlease process this task based on your role."
                
                step_start = asyncio.get_event_loop().time()
                try:
                    output = await asyncio.wait_for(
                        agent_instance.run(prompt),
                        timeout=self.agent_timeout
                    )
                    step_duration = asyncio.get_event_loop().time() - step_start
                    
                    cell_result = CellResult(
                        row=row,
                        col=col,
                        agent_name=agent_config.name,
                        output=output,
                        success=True
                    )
                    result.cell_results.append(cell_result)
                    
                    step_result = WorkflowStepResult(
                        agent_name=agent_config.name,
                        agent_number=agent_instance.number,
                        success=True,
                        output=output,
                        error=None,
                        timing={"duration": step_duration}
                    )
                    result.steps.append(step_result)
                    
                except Exception as e:
                    step_duration = asyncio.get_event_loop().time() - step_start
                    cell_result = CellResult(
                        row=row,
                        col=col,
                        agent_name=agent_config.name,
                        output="",
                        success=False,
                        error=str(e)
                    )
                    result.cell_results.append(cell_result)
                    
                    step_result = WorkflowStepResult(
                        agent_name=agent_config.name,
                        agent_number=agent_instance.number,
                        success=False,
                        output="",
                        error=str(e),
                        timing={"duration": step_duration}
                    )
                    result.steps.append(step_result)
    
    async def _execute_column_by_column(
        self, 
        agent_instances: List["Agent"], 
        task: str, 
        result: SpreadSheetResult
    ):
        """Execute agents column by column."""
        for col in range(self.cols):
            col_results = []
            for row in range(self.rows):
                idx = row * self.cols + col
                agent_config = self.agents[idx]
                agent_instance = agent_instances[idx]
                
                # Build context from previous column if exists
                context = f"\n\nOriginal task: {task}"
                if col > 0:
                    prev_col_results = [cr for cr in result.cell_results if cr.col == col - 1]
                    if prev_col_results:
                        context += "\n\nResults from previous column:\n" + "\n".join([f"Row {cr.row}: {cr.output}" for cr in prev_col_results])
                
                prompt = f"Spreadsheet Cell [{row},{col}]{context}\n\nPlease process this task based on your role."
                
                step_start = asyncio.get_event_loop().time()
                try:
                    output = await asyncio.wait_for(
                        agent_instance.run(prompt),
                        timeout=self.agent_timeout
                    )
                    step_duration = asyncio.get_event_loop().time() - step_start
                    
                    cell_result = CellResult(
                        row=row,
                        col=col,
                        agent_name=agent_config.name,
                        output=output,
                        success=True
                    )
                    result.cell_results.append(cell_result)
                    
                    step_result = WorkflowStepResult(
                        agent_name=agent_config.name,
                        agent_number=agent_instance.number,
                        success=True,
                        output=output,
                        error=None,
                        timing={"duration": step_duration}
                    )
                    result.steps.append(step_result)
                    
                except Exception as e:
                    step_duration = asyncio.get_event_loop().time() - step_start
                    cell_result = CellResult(
                        row=row,
                        col=col,
                        agent_name=agent_config.name,
                        output="",
                        success=False,
                        error=str(e)
                    )
                    result.cell_results.append(cell_result)
                    
                    step_result = WorkflowStepResult(
                        agent_name=agent_config.name,
                        agent_number=agent_instance.number,
                        success=False,
                        output="",
                        error=str(e),
                        timing={"duration": step_duration}
                    )
                    result.steps.append(step_result)
    
    async def _execute_parallel(
        self, 
        agent_instances: List["Agent"], 
        task: str, 
        result: SpreadSheetResult
    ):
        """Execute all agents in parallel."""
        tasks = []
        for row in range(self.rows):
            for col in range(self.cols):
                idx = row * self.cols + col
                tasks.append(self._execute_cell_parallel(
                    agent_instances[idx], self.agents[idx], row, col, task, result
                ))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_cell_parallel(
        self, 
        agent_instance: "Agent", 
        agent_config: AgentConfig, 
        row: int, 
        col: int, 
        task: str, 
        result: SpreadSheetResult
    ):
        """Execute a single cell in parallel mode."""
        prompt = f"Spreadsheet Cell [{row},{col}]\n\nTask: {task}\n\nPlease process this task based on your role."
        
        step_start = asyncio.get_event_loop().time()
        try:
            output = await asyncio.wait_for(
                agent_instance.run(prompt),
                timeout=self.agent_timeout
            )
            step_duration = asyncio.get_event_loop().time() - step_start
            
            cell_result = CellResult(
                row=row,
                col=col,
                agent_name=agent_config.name,
                output=output,
                success=True
            )
            result.cell_results.append(cell_result)
            
            step_result = WorkflowStepResult(
                agent_name=agent_config.name,
                agent_number=agent_instance.number,
                success=True,
                output=output,
                error=None,
                timing={"duration": step_duration}
            )
            result.steps.append(step_result)
            
        except Exception as e:
            step_duration = asyncio.get_event_loop().time() - step_start
            cell_result = CellResult(
                row=row,
                col=col,
                agent_name=agent_config.name,
                output="",
                success=False,
                error=str(e)
            )
            result.cell_results.append(cell_result)
            
            step_result = WorkflowStepResult(
                agent_name=agent_config.name,
                agent_number=agent_instance.number,
                success=False,
                output="",
                error=str(e),
                timing={"duration": step_duration}
            )
            result.steps.append(step_result)


class swarm_spreadsheet(Tool):
    """Execute a spreadsheet swarm workflow with agents arranged in a grid."""
    
    async def execute(
        self,
        agents: str,
        task: str,
        rows: str,
        cols: str,
        timeout: str = "900",
        agent_timeout: str = "300",
        execution_mode: str = "parallel",
        **kwargs
    ) -> Response:
        """Execute spreadsheet swarm workflow."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 900
            agent_timeout_int = int(agent_timeout) if agent_timeout.isdigit() else 300
            rows_int = int(rows) if rows.isdigit() else 1
            cols_int = int(cols) if cols.isdigit() else 1
            
            # Parse agents
            agent_configs = []
            if isinstance(agents, str):
                try:
                    agents_list = json.loads(agents)
                    if not isinstance(agents_list, list):
                        raise ValueError()
                except:
                    agents_list = [a.strip() for a in agents.split(",") if a.strip()]
                
                for agent_spec in agents_list:
                    agent_configs.append(self._parse_agent_spec(agent_spec))
            
            # Validate grid size
            if len(agent_configs) < rows_int * cols_int:
                return Response(
                    message=f"Error: Not enough agents ({len(agent_configs)}) for grid size ({rows_int}x{cols_int}={rows_int*cols_int})",
                    break_loop=False
                )
            
            # Create and execute workflow
            workflow = SpreadSheetSwarm(
                agents=agent_configs,
                rows=rows_int,
                cols=cols_int,
                parent_agent=self.agent,
                timeout=timeout_int,
                agent_timeout=agent_timeout_int,
                execution_mode=execution_mode
            )
            
            result = await workflow.execute(task)
            
            # Format response
            response_parts = [
                f"# 📊 SpreadSheet Swarm",
                f"**Task**: {task}",
                f"**Status**: {result.status.value}",
                f"**Grid Size**: {result.grid_size['rows']}x{result.grid_size['cols']}",
                f"**Execution Mode**: {execution_mode}",
                "",
                f"## Cell Results",
            ]
            
            # Create grid visualization
            grid = [[None for _ in range(result.grid_size['cols'])] for _ in range(result.grid_size['rows'])]
            for cell_result in result.cell_results:
                grid[cell_result.row][cell_result.col] = cell_result
            
            for row_idx, row in enumerate(grid):
                row_parts = []
                for col_idx, cell in enumerate(row):
                    if cell:
                        if cell.success:
                            row_parts.append(f"[{cell.agent_name}: {cell.output[:50]}...]" if len(cell.output) > 50 else f"[{cell.agent_name}: {cell.output}]")
                        else:
                            row_parts.append(f"[{cell.agent_name}: ⚠️ Error]")
                    else:
                        row_parts.append("[Empty]")
                response_parts.append(" | ".join(row_parts))
            
            response_parts.extend([
                "",
                "## Final Synthesized Output",
                f"> {result.final_output}",
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "spreadsheet_swarm"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing spreadsheet swarm: {str(e)}",
                break_loop=False
            )

# ===== AutoSwarmBuilder Pattern =====

@dataclass
class AutoSwarmPlan:
    pattern: str
    agents: List[AgentConfig]
    parameters: dict
    rationale: str

@dataclass
class AutoSwarmResult(WorkflowResult):
    plan: AutoSwarmPlan = None
    execution_result: dict = None
    
    def __post_init__(self):
        if self.execution_result is None:
            self.execution_result = {}


class AutoSwarmBuilder(BaseWorkflow):
    """
    Automatically selects and configures the best swarm pattern for a given task.
    Analyzes the task requirements and builds an appropriate swarm configuration.
    """
    
    def __init__(
        self,
        builder_agent: AgentConfig,
        agent_pool: List[AgentConfig],
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 900,
        agent_timeout: int = 300
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.builder_agent = builder_agent
        self.agent_pool = agent_pool
        self.agent_timeout = agent_timeout
    
    async def execute(self, task: str) -> AutoSwarmResult:
        """Automatically build and execute the best swarm for the task."""
        start_time = asyncio.get_event_loop().time()
        result = AutoSwarmResult(
            workflow_id=self.workflow_id,
            workflow_type="auto_swarm_builder",
            status=WorkflowStatus.RUNNING,
            steps=[],
            plan=None,
            execution_result={},
            final_output="",
            timing={}
        )
        
        try:
            # Create builder agent
            builder = await self._create_agent(self.builder_agent)
            
            # Build agent pool descriptions
            agent_descriptions = []
            for agent in self.agent_pool:
                desc = f"- {agent.name}: {agent.system_prompt or 'No description'}"
                agent_descriptions.append(desc)
            
            # Ask builder to create a plan
            planning_prompt = (
                f"You are an expert in swarm intelligence and multi-agent orchestration.\n"
                f"Analyze this task and design the optimal swarm configuration to solve it.\n\n"
                f"Available Agents:\n{chr(10).join(agent_descriptions)}\n\n"
                f"Task: {task}\n\n"
                f"Select the best swarm pattern and configure it appropriately.\n"
                f"Respond ONLY with JSON in this exact format:\n"
                f"{{\n"
                f"  \"pattern\": \"pattern_name\",\n"
                f"  \"agents\": [\"agent1\", \"agent2\", ...],\n"
                f"  \"parameters\": {{\"param1\": \"value1\", ...}},\n"
                f"  \"rationale\": \"explanation of choices\"\n"
                f"}}\n\n"
                f"Available patterns: sequential, concurrent, graph, star, hierarchical, round_robin, group_chat, forest, spreadsheet"
            )
            
            planning_start = asyncio.get_event_loop().time()
            planning_response = await asyncio.wait_for(
                builder.run(planning_prompt),
                timeout=self.agent_timeout
            )
            planning_duration = asyncio.get_event_loop().time() - planning_start
            
            # Parse the plan
            try:
                plan_json = json.loads(planning_response)
                plan = AutoSwarmPlan(
                    pattern=plan_json["pattern"],
                    agents=[],
                    parameters=plan_json["parameters"],
                    rationale=plan_json["rationale"]
                )
                
                # Resolve agent names to configs
                for agent_name in plan_json["agents"]:
                    for agent_config in self.agent_pool:
                        if agent_config.name == agent_name:
                            plan.agents.append(agent_config)
                            break
                
                result.plan = plan
                
            except Exception as e:
                result.status = WorkflowStatus.FAILED
                result.error = f"Failed to parse swarm plan: {str(e)}"
                return result
            
            result.steps.append(WorkflowStepResult(
                agent_name=self.builder_agent.name,
                agent_number=builder.number,
                success=True,
                output=json.dumps(plan_json, indent=2),
                error=None,
                timing={"duration": planning_duration}
            ))
            
            # Execute the planned swarm
            execution_result = await self._execute_planned_swarm(plan, task, result)
            result.execution_result = execution_result
            result.final_output = execution_result.get("final_output", "")
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"AutoSwarmBuilder workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result
    
    async def _execute_planned_swarm(
        self, 
        plan: AutoSwarmPlan, 
        task: str, 
        result: AutoSwarmResult
    ) -> dict:
        """Execute the swarm according to the auto-generated plan."""
        # Import swarm pattern classes
        from python.tools.swarm_workflow import SequentialWorkflow, ConcurrentWorkflow, GraphWorkflow
        from python.tools.swarm_patterns import StarSwarm, HierarchicalSwarm, RoundRobinSwarm, GroupChat, ForestSwarm, SpreadSheetSwarm
        
        # Execute based on pattern
        if plan.pattern == "sequential":
            workflow = SequentialWorkflow(
                agents=plan.agents,
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "concurrent":
            # Default aggregation function
            def concat_aggregation(outputs):
                return "\n\n---\n\n".join(outputs)
            
            workflow = ConcurrentWorkflow(
                agents=plan.agents,
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout,
                aggregation=concat_aggregation
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "graph":
            # For simplicity, we'll create a linear graph
            nodes = []
            edges = []
            
            for i, agent_config in enumerate(plan.agents):
                nodes.append({
                    "id": f"node_{i}",
                    "agent": agent_config
                })
                
                if i > 0:
                    edges.append({
                        "from": f"node_{i-1}",
                        "to": f"node_{i}",
                        "condition": "success == True"
                    })
            
            workflow = GraphWorkflow(
                nodes=nodes,
                edges=edges,
                entry="node_0",
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                node_timeout=self.agent_timeout
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "star":
            if len(plan.agents) < 2:
                raise ValueError("StarSwarm requires at least 2 agents (1 hub + 1+ workers)")
            
            workflow = StarSwarm(
                hub=plan.agents[0],
                workers=plan.agents[1:],
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "hierarchical":
            if len(plan.agents) < 3:
                raise ValueError("HierarchicalSwarm requires at least 3 agents (1 root + 1+ managers + 1+ workers)")
            
            # Simple hierarchy: first agent is root, second is manager, rest are workers
            workflow = HierarchicalSwarm(
                root=plan.agents[0],
                managers=[plan.agents[1]],
                workers={plan.agents[1].name: plan.agents[2:]},
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "round_robin":
            rounds = plan.parameters.get("rounds", 3)
            workflow = RoundRobinSwarm(
                agents=plan.agents,
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout,
                rounds=rounds
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "group_chat":
            max_rounds = plan.parameters.get("max_rounds", 10)
            workflow = GroupChat(
                agents=plan.agents,
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout,
                max_rounds=max_rounds
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "forest":
            # Create a simple forest with one tree
            tree_def = {}
            for i, agent_config in enumerate(plan.agents):
                node_id = f"node_{i}"
                children = [f"node_{j}" for j in range(i+1, min(i+3, len(plan.agents)))]
                tree_def[node_id] = {
                    "agent": agent_config,
                    "children": children
                }
            
            workflow = ForestSwarm(
                trees=[tree_def],
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout
            )
            return await workflow.execute(task)
        
        elif plan.pattern == "spreadsheet":
            rows = plan.parameters.get("rows", 2)
            cols = plan.parameters.get("cols", 2)
            execution_mode = plan.parameters.get("execution_mode", "parallel")
            
            workflow = SpreadSheetSwarm(
                agents=plan.agents,
                rows=rows,
                cols=cols,
                parent_agent=self.parent_agent,
                timeout=self.timeout,
                agent_timeout=self.agent_timeout,
                execution_mode=execution_mode
            )
            return await workflow.execute(task)
        
        else:
            raise ValueError(f"Unknown swarm pattern: {plan.pattern}")


class swarm_auto_builder(Tool):
    """Automatically build and execute the best swarm for a given task."""
    
    async def execute(
        self,
        builder: str,
        agent_pool: str,
        task: str,
        timeout: str = "900",
        agent_timeout: str = "300",
        **kwargs
    ) -> Response:
        """Execute auto swarm builder."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 900
            agent_timeout_int = int(agent_timeout) if agent_timeout.isdigit() else 300
            
            # Parse builder agent
            builder_config = self._parse_agent_spec(builder)
            
            # Parse agent pool
            agent_configs = []
            if isinstance(agent_pool, str):
                try:
                    pool_list = json.loads(agent_pool)
                    if not isinstance(pool_list, list):
                        raise ValueError()
                except:
                    pool_list = [a.strip() for a in agent_pool.split(",") if a.strip()]
                
                for agent_spec in pool_list:
                    agent_configs.append(self._parse_agent_spec(agent_spec))
            
            # Create and execute workflow
            workflow = AutoSwarmBuilder(
                builder_agent=builder_config,
                agent_pool=agent_configs,
                parent_agent=self.agent,
                timeout=timeout_int,
                agent_timeout=agent_timeout_int
            )
            
            result = await workflow.execute(task)
            
            # Format response
            response_parts = [
                f"# 🤖 Auto Swarm Builder",
                f"**Task**: {task}",
                f"**Status**: {result.status.value}",
                "",
                f"## Swarm Plan",
                f"**Pattern**: {result.plan.pattern if result.plan else 'N/A'}",
                f"**Rationale**: {result.plan.rationale if result.plan else 'N/A'}",
                f"**Parameters**: {json.dumps(result.plan.parameters if result.plan else {}, indent=2)}",
                "",
                f"**Selected Agents**: {', '.join([a.name for a in result.plan.agents]) if result.plan else 'N/A'}",
                "",
                f"## Execution Result",
            ]
            
            # Add execution result details based on pattern
            if result.execution_result:
                response_parts.append(f"> {result.execution_result.get('final_output', 'N/A')}")
            
            response_parts.extend([
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "auto_swarm_builder"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing auto swarm builder: {str(e)}",
                break_loop=False
            )
