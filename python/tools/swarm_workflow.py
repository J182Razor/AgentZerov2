
"""
Swarm Workflow Tools for Agent Zero

Implements multi-agent workflow patterns including SequentialWorkflow
for executing agents in a chain with output passing, and ConcurrentWorkflow
for parallel agent execution with result aggregation.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Union
from enum import Enum

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
from python.helpers.subagents import load_agent_data

logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Strategies for aggregating results from concurrent agents."""
    CONCAT = "concat"
    BEST = "best"
    VOTE = "vote"
    SUMMARY = "summary"


class SequentialWorkflow(BaseWorkflow):
    """Executes agents sequentially, passing output from one agent to the next."""

    def __init__(
        self,
        parent_agent: Agent,
        workflow_id: str = "",
        timeout: float = 600.0,
        step_timeout: float = 300.0,
        fail_fast: bool = True,
    ):
        super().__init__(
            workflow_id=workflow_id or f"seq_{uuid.uuid4().hex[:8]}",
            timeout=timeout,
            fail_fast=fail_fast,
        )
        self.parent_agent = parent_agent
        self.step_timeout = step_timeout
        self._agents: list[Agent] = []
        self._current_step = 0

    def _parse_agent_config(self, agent_spec):
        if isinstance(agent_spec, AgentConfig):
            return agent_spec
        if isinstance(agent_spec, dict):
            return AgentConfig(
                name=agent_spec.get("name", ""),
                profile=agent_spec.get("profile", ""),
                prompt=agent_spec.get("prompt", ""),
                timeout=agent_spec.get("timeout", self.step_timeout),
                system_prompt=agent_spec.get("system_prompt", ""),
            )
        if isinstance(agent_spec, str):
            return AgentConfig(name=agent_spec, timeout=self.step_timeout)
        raise ValueError(f"Invalid agent specification: {type(agent_spec)}")

    async def _create_agent(self, config, agent_number):
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
        return agent

    async def _execute_step(self, agent, input_message, timeout):
        step_start = datetime.now(timezone.utc)
        try:
            agent.hist_add_user_message(UserMessage(message=input_message, attachments=[]))
            async def run_agent():
                return await agent.monologue()
            try:
                result = await asyncio.wait_for(run_agent(), timeout=timeout)
            except asyncio.TimeoutError:
                raise WorkflowTimeoutError(f"Agent {agent.agent_name} exceeded timeout of {timeout}s")
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
            logger.exception(f"Error in workflow step {agent.agent_name}")
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

    async def execute(self, initial_input, agents):
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._results = []
        self._agents = []
        current_input = initial_input
        final_output = ""
        try:
            async def run_workflow():
                nonlocal current_input, final_output
                for idx, agent_spec in enumerate(agents):
                    self._current_step = idx + 1
                    config = self._parse_agent_config(agent_spec)
                    logger.info(f"Workflow {self.workflow_id}: Step {idx + 1}/{len(agents)}")
                    agent = await self._create_agent(config, idx + 1)
                    self._agents.append(agent)
                    if config.prompt:
                        step_input = f"{config.prompt}\n\n---\nInput from previous step:\n{current_input}"
                    else:
                        step_input = current_input
                    step_result = await self._execute_step(agent, step_input, config.timeout)
                    self._results.append(step_result)
                    if not step_result.success:
                        if self.fail_fast:
                            return WorkflowStatus.FAILED
                        else:
                            current_input = f"[Step {idx + 1} failed: {step_result.error}]"
                    else:
                        current_input = step_result.output
                final_output = current_input
                return WorkflowStatus.COMPLETED
            try:
                status = await asyncio.wait_for(run_workflow(), timeout=self.timeout)
            except asyncio.TimeoutError:
                status = WorkflowStatus.TIMEOUT
                final_output = f"Workflow exceeded total timeout of {self.timeout}s"
            return self._create_workflow_result(
                status=status,
                final_output=final_output,
                metadata={
                    "total_steps": len(agents),
                    "completed_steps": len([r for r in self._results if r.success]),
                    "failed_steps": len([r for r in self._results if not r.success]),
                },
            )
        except Exception as e:
            logger.exception(f"Workflow {self.workflow_id} failed")
            return self._create_workflow_result(
                status=WorkflowStatus.FAILED,
                final_output="",
                metadata={"error": str(e)},
            )


class ConcurrentWorkflow(BaseWorkflow):
    """Executes agents in parallel and aggregates results."""

    def __init__(
        self,
        parent_agent: Agent,
        workflow_id: str = "",
        timeout: float = 600.0,
        agent_timeout: float = 300.0,
        aggregation: str = "concat",
        separator: str = "\n\n---\n\n",
        max_concurrency: int = 10,
    ):
        super().__init__(
            workflow_id=workflow_id or f"conc_{uuid.uuid4().hex[:8]}",
            timeout=timeout,
            fail_fast=False,  # Concurrent workflows continue on individual failures
        )
        self.parent_agent = parent_agent
        self.agent_timeout = agent_timeout
        self.aggregation = AggregationStrategy(aggregation.lower())
        self.separator = separator
        self.max_concurrency = max_concurrency
        self._agents: list[Agent] = []

    def _parse_agent_config(self, agent_spec) -> AgentConfig:
        """Parse agent specification into AgentConfig."""
        if isinstance(agent_spec, AgentConfig):
            return agent_spec
        if isinstance(agent_spec, dict):
            return AgentConfig(
                name=agent_spec.get("name", ""),
                profile=agent_spec.get("profile", ""),
                prompt=agent_spec.get("prompt", ""),
                timeout=agent_spec.get("timeout", self.agent_timeout),
                system_prompt=agent_spec.get("system_prompt", ""),
            )
        if isinstance(agent_spec, str):
            return AgentConfig(name=agent_spec, timeout=self.agent_timeout)
        raise ValueError(f"Invalid agent specification: {type(agent_spec)}")

    async def _create_agent(self, config: AgentConfig, agent_number: int) -> Agent:
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
            logger.exception(f"Error in concurrent agent {agent.agent_name}")
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

    async def _aggregate_results(
        self,
        results: list[WorkflowStepResult],
    ) -> str:
        """Aggregate results using the configured strategy."""
        successful_results = [r for r in results if r.success]

        if not successful_results:
            return "No agents completed successfully."

        outputs = [r.output for r in successful_results]
        agent_names = [r.agent_name for r in successful_results]

        if self.aggregation == AggregationStrategy.CONCAT:
            return self._aggregate_concat(outputs, agent_names)
        elif self.aggregation == AggregationStrategy.BEST:
            return await self._aggregate_best(outputs, agent_names)
        elif self.aggregation == AggregationStrategy.VOTE:
            return self._aggregate_vote(outputs, agent_names)
        elif self.aggregation == AggregationStrategy.SUMMARY:
            return await self._aggregate_summary(outputs, agent_names)
        else:
            return self._aggregate_concat(outputs, agent_names)

    def _aggregate_concat(
        self,
        outputs: list[str],
        agent_names: list[str],
    ) -> str:
        """Concatenate all results with separator."""
        combined = []
        for name, output in zip(agent_names, outputs):
            combined.append(f"### {name}\n{output}")
        return self.separator.join(combined)

    async def _aggregate_best(
        self,
        outputs: list[str],
        agent_names: list[str],
    ) -> str:
        """Use LLM to select the best result."""
        if len(outputs) == 1:
            return outputs[0]

        # Prepare the evaluation prompt
        candidates = "\n\n".join([
            f"--- CANDIDATE {i+1} ({name}) ---\n{output}"
            for i, (name, output) in enumerate(zip(agent_names, outputs))
        ])

        prompt = f"""You are a judge evaluating multiple AI responses. Select the SINGLE BEST response based on:
1. Completeness and accuracy
2. Clarity and coherence
3. Relevance to the task
4. Quality of reasoning

{candidates}

Respond with ONLY the letter of the best candidate (A, B, C, etc.) followed by a brief explanation.
Format: [LETTER] - [Brief explanation]"""

        try:
            # Use parent agent's LLM to evaluate
            response = await self.parent_agent.call_llm(prompt)

            # Parse the response to get the best candidate
            response = response.strip().upper()
            if response and response[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                idx = ord(response[0]) - ord("A")
                if 0 <= idx < len(outputs):
                    return f"**Selected: {agent_names[idx]}**\n\n{outputs[idx]}\n\n_Selection rationale: {response[1:].strip("- ")}_"

            # Fallback to first result if parsing fails
            return outputs[0]

        except Exception as e:
            logger.warning(f"LLM aggregation failed, falling back to concat: {e}")
            return self._aggregate_concat(outputs, agent_names)

    def _aggregate_vote(
        self,
        outputs: list[str],
        agent_names: list[str],
    ) -> str:
        """Perform majority voting on results."""
        if len(outputs) == 1:
            return outputs[0]

        # Simple voting based on output similarity/hashing
        from collections import Counter

        # Normalize outputs for comparison
        normalized = [self._normalize_for_vote(o) for o in outputs]

        # Count occurrences
        counts = Counter(normalized)
        most_common = counts.most_common(1)[0][0]

        # Find the original output that matches
        for name, output, norm in zip(agent_names, outputs, normalized):
            if norm == most_common:
                vote_count = counts[most_common]
                return f"**Majority decision ({vote_count}/{len(outputs)} votes): {name}**\n\n{output}"

        # Fallback
        return outputs[0]

    def _normalize_for_vote(self, text: str) -> str:
        """Normalize text for voting comparison."""
        import re
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text[:500]

    async def _aggregate_summary(
        self,
        outputs: list[str],
        agent_names: list[str],
    ) -> str:
        """Use LLM to summarize all results."""
        if len(outputs) == 1:
            return outputs[0]

        responses = "\n\n".join([
            f"--- RESPONSE FROM {name} ---\n{output}"
            for name, output in zip(agent_names, outputs)
        ])

        prompt = f"""You are a summarizer. Create a unified summary that:
1. Synthesizes the key points from all responses
2. Highlights any consensus or agreements
3. Notes important differences or unique insights
4. Provides a coherent, comprehensive answer

{responses}

Provide a well-structured summary that captures the essence of all responses."""

        try:
            summary = await self.parent_agent.call_llm(prompt)
            return f"**Synthesized Summary**\n\n{summary}\n\n_Synthesized from {len(outputs)} agent responses._"
        except Exception as e:
            logger.warning(f"LLM summarization failed, falling back to concat: {e}")
            return self._aggregate_concat(outputs, agent_names)

    async def execute(
        self,
        initial_input: str,
        agents: list,
    ) -> WorkflowResult:
        """Execute all agents in parallel and aggregate results."""
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._results = []
        self._agents = []

        try:
            # Parse all agent configurations
            configs = [self._parse_agent_config(spec) for spec in agents]

            logger.info(
                f"ConcurrentWorkflow {self.workflow_id}: "
                f"Starting {len(configs)} agents with max_concurrency={self.max_concurrency}"
            )

            # Create all agents first
            for idx, config in enumerate(configs):
                agent = await self._create_agent(config, idx + 1)
                self._agents.append(agent)

            # Build execution tasks with semaphore for concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrency)

            async def execute_with_semaphore(agent, config, idx):
                async with semaphore:
                    logger.info(
                        f"ConcurrentWorkflow {self.workflow_id}: "
                        f"Starting agent {idx + 1}/{len(configs)} ({config.name or agent.agent_name})"
                    )
                    input_msg = initial_input
                    if config.prompt:
                        input_msg = f"{config.prompt}\n\n---\nTask:\n{initial_input}"
                    return await self._execute_agent(agent, input_msg, config.timeout)

            # Execute all agents in parallel with concurrency limit
            async def run_all_agents():
                tasks = [
                    execute_with_semaphore(agent, config, idx)
                    for idx, (agent, config) in enumerate(zip(self._agents, configs))
                ]
                return await asyncio.gather(*tasks, return_exceptions=True)

            # Run with overall timeout
            try:
                raw_results = await asyncio.wait_for(run_all_agents(), timeout=self.timeout)
            except asyncio.TimeoutError:
                self._status = WorkflowStatus.TIMEOUT
                return self._create_workflow_result(
                    status=WorkflowStatus.TIMEOUT,
                    final_output=f"Workflow exceeded total timeout of {self.timeout}s",
                    metadata={
                        "total_agents": len(agents),
                        "completed_agents": 0,
                        "failed_agents": len(agents),
                        "aggregation": self.aggregation.value,
                    },
                )

            # Process results, handling any exceptions
            for result in raw_results:
                if isinstance(result, Exception):
                    self._results.append(WorkflowStepResult(
                        agent_name="unknown",
                        agent_number=0,
                        success=False,
                        output="",
                        error=f"{type(result).__name__}: {str(result)}",
                        start_time=self._start_time,
                        end_time=datetime.now(timezone.utc),
                        duration_seconds=0.0,
                    ))
                elif isinstance(result, WorkflowStepResult):
                    self._results.append(result)

            # Aggregate results
            aggregated = await self._aggregate_results(self._results)

            # Determine overall status
            successful_count = len([r for r in self._results if r.success])
            if successful_count == 0:
                status = WorkflowStatus.FAILED
            elif successful_count < len(self._results):
                status = WorkflowStatus.COMPLETED
            else:
                status = WorkflowStatus.COMPLETED

            return self._create_workflow_result(
                status=status,
                final_output=aggregated,
                metadata={
                    "total_agents": len(agents),
                    "completed_agents": successful_count,
                    "failed_agents": len(self._results) - successful_count,
                    "aggregation": self.aggregation.value,
                    "max_concurrency": self.max_concurrency,
                },
            )

        except Exception as e:
            logger.exception(f"ConcurrentWorkflow {self.workflow_id} failed")
            return self._create_workflow_result(
                status=WorkflowStatus.FAILED,
                final_output="",
                metadata={"error": str(e)},
            )


class swarm_sequential(Tool):
    """Tool for executing a sequential workflow of agents."""

    async def execute(self, agents="", initial_input="", workflow_id="", timeout="600", step_timeout="300", fail_fast="true", **kwargs):
        import json
        try:
            agent_list = self._parse_agents_param(agents)
            if not agent_list:
                return Response(message="Error: No agents specified", break_loop=False)

            try:
                timeout_val = float(timeout)
                step_timeout_val = float(step_timeout)
            except ValueError:
                return Response(message="Error: Invalid timeout values", break_loop=False)

            fail_fast_val = str(fail_fast).lower().strip() == "true"

            workflow = SequentialWorkflow(
                parent_agent=self.agent,
                workflow_id=workflow_id,
                timeout=timeout_val,
                step_timeout=step_timeout_val,
                fail_fast=fail_fast_val,
            )

            input_msg = initial_input or self.message or "Execute the sequential workflow."
            result = await workflow.execute(initial_input=input_msg, agents=agent_list)

            response_text = self._format_result(result)
            return Response(
                message=response_text,
                break_loop=False,
                additional={"workflow_id": result.workflow_id, "status": result.status.value},
            )

        except Exception as e:
            logger.exception("Sequential workflow execution failed")
            return Response(message=f"Workflow failed: {type(e).__name__}: {str(e)}", break_loop=False)

    def _parse_agents_param(self, agents):
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

    def _format_result(self, result):
        lines = [
            f"# Sequential Workflow: {result.workflow_id}",
            f"**Status**: {result.status.value.upper()}",
            f"**Duration**: {result.total_duration_seconds:.2f}s",
            f"**Steps**: {len(result.steps)}",
            "",
        ]
        for i, step in enumerate(result.steps, 1):
            status_icon = "OK" if step.success else "FAIL"
            lines.append(f"## Step {i}: {step.agent_name} [{status_icon}]")
            lines.append(f"**Duration**: {step.duration_seconds:.2f}s")
            if step.error:
                lines.append(f"**Error**: {step.error}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Final Output")
        lines.append(result.final_output)
        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://construction {self.agent.agent_name}: Executing Sequential Workflow",
            content="",
            kvps=self.args,
        )


class swarm_concurrent(Tool):
    """Tool for executing a concurrent workflow of agents in parallel."""

    async def execute(
        self,
        agents="",
        initial_input="",
        workflow_id="",
        timeout="600",
        agent_timeout="300",
        aggregation="concat",
        separator="\n\n---\n\n",
        max_concurrency="10",
        **kwargs,
    ):
        import json
        try:
            agent_list = self._parse_agents_param(agents)
            if not agent_list:
                return Response(message="Error: No agents specified", break_loop=False)

            valid_aggregations = ["concat", "best", "vote", "summary"]
            aggregation = aggregation.lower().strip()
            if aggregation not in valid_aggregations:
                return Response(
                    message=f"Error: Invalid aggregation strategy. Must be one of: {', '.join(valid_aggregations)}",
                    break_loop=False,
                )

            try:
                timeout_val = float(timeout)
                agent_timeout_val = float(agent_timeout)
                max_concurrency_val = int(max_concurrency)
                if max_concurrency_val < 1:
                    max_concurrency_val = 10
            except ValueError:
                return Response(message="Error: Invalid numeric parameters", break_loop=False)

            workflow = ConcurrentWorkflow(
                parent_agent=self.agent,
                workflow_id=workflow_id,
                timeout=timeout_val,
                agent_timeout=agent_timeout_val,
                aggregation=aggregation,
                separator=separator,
                max_concurrency=max_concurrency_val,
            )

            input_msg = initial_input or self.message or "Execute the concurrent workflow."
            result = await workflow.execute(initial_input=input_msg, agents=agent_list)

            response_text = self._format_result(result)
            return Response(
                message=response_text,
                break_loop=False,
                additional={
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "aggregation": aggregation,
                },
            )

        except Exception as e:
            logger.exception("Concurrent workflow execution failed")
            return Response(message=f"Workflow failed: {type(e).__name__}: {str(e)}", break_loop=False)

    def _parse_agents_param(self, agents):
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

    def _format_result(self, result: WorkflowResult) -> str:
        """Format the workflow result for display."""
        lines = [
            f"# Concurrent Workflow: {result.workflow_id}",
            f"**Status**: {result.status.value.upper()}",
            f"**Duration**: {result.total_duration_seconds:.2f}s",
            f"**Agents Executed**: {len(result.steps)}",
            f"**Aggregation**: {result.metadata.get('aggregation', 'concat')}",
            "",
        ]

        successful = [s for s in result.steps if s.success]
        failed = [s for s in result.steps if not s.success]

        lines.append(f"**Successful**: {len(successful)} | **Failed**: {len(failed)}")
        lines.append("")

        lines.append("## Agent Results")
        lines.append("")
        for i, step in enumerate(result.steps, 1):
            status_icon = "OK" if step.success else "FAIL"
            lines.append(f"### Agent {i}: {step.agent_name} [{status_icon}]")
            lines.append(f"**Duration**: {step.duration_seconds:.2f}s")
            if step.error:
                lines.append(f"**Error**: {step.error}")
            if step.success and step.output:
                output_preview = step.output[:500] + "..." if len(step.output) > 500 else step.output
                lines.append(f"**Output Preview**: {output_preview}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Aggregated Result")
        lines.append(result.final_output)

        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://construction {self.agent.agent_name}: Executing Concurrent Workflow",
            content="",
            kvps=self.args,
        )


class GraphWorkflow(BaseWorkflow):
    """Executes agents as a directed graph with conditional branching and parallel paths."""

    def __init__(
        self,
        parent_agent: Agent,
        workflow_id: str = "",
        timeout: float = 600.0,
        node_timeout: float = 300.0,
        max_iterations: int = 100,
        fail_fast: bool = True,
    ):
        super().__init__(
            workflow_id=workflow_id or f"graph_{uuid.uuid4().hex[:8]}",
            timeout=timeout,
            fail_fast=fail_fast,
        )
        self.parent_agent = parent_agent
        self.node_timeout = node_timeout
        self.max_iterations = max_iterations
        self._nodes: dict[str, dict] = {}
        self._edges: list[dict] = []
        self._node_outputs: dict[str, str] = {}
        self._executed_nodes: set[str] = set()
        self._iteration_count: int = 0

    def _parse_nodes(self, nodes_spec) -> dict[str, dict]:
        """Parse nodes specification into a dictionary keyed by node ID."""
        nodes = {}
        if isinstance(nodes_spec, str):
            try:
                nodes_spec = json.loads(nodes_spec)
            except json.JSONDecodeError:
                raise ValueError("Invalid nodes JSON specification")

        for node in nodes_spec:
            if isinstance(node, dict):
                node_id = node.get("id") or node.get("node_id")
                if not node_id:
                    raise ValueError("Node missing required 'id' field")
                nodes[str(node_id)] = {
                    "id": str(node_id),
                    "agent": node.get("agent", "developer"),
                    "profile": node.get("profile", ""),
                    "prompt": node.get("prompt", ""),
                    "timeout": node.get("timeout", self.node_timeout),
                    "system_prompt": node.get("system_prompt", ""),
                }
        return nodes

    def _parse_edges(self, edges_spec) -> list[dict]:
        """Parse edges specification into a list of edge definitions."""
        edges = []
        if isinstance(edges_spec, str):
            try:
                edges_spec = json.loads(edges_spec)
            except json.JSONDecodeError:
                raise ValueError("Invalid edges JSON specification")

        for edge in edges_spec:
            if isinstance(edge, dict):
                from_node = edge.get("from") or edge.get("from_node")
                to_node = edge.get("to") or edge.get("to_node")
                if not from_node or not to_node:
                    raise ValueError(f"Edge missing required 'from' or 'to' field: {edge}")
                edges.append({
                    "from": str(from_node),
                    "to": str(to_node),
                    "condition": edge.get("condition", ""),
                })
        return edges

    def _get_outgoing_edges(self, node_id: str) -> list[dict]:
        """Get all outgoing edges from a node."""
        return [e for e in self._edges if e["from"] == node_id]

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """Evaluate a condition expression in the given context."""
        if not condition or not condition.strip():
            return True

        try:
            # Create a safe evaluation context
            eval_context = {
                "output": context.get("output", ""),
                "success": context.get("success", True),
                "error": context.get("error"),
                "node_outputs": context.get("node_outputs", {}),
                "iteration": context.get("iteration", 0),
                "True": True,
                "False": False,
                "None": None,
            }
            result = eval(condition, {"__builtins__": {}}, eval_context)
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition} -> {e}")
            return False

    async def _create_agent(self, node_config: dict, agent_number: int) -> Agent:
        """Create a subordinate agent for a graph node."""
        base_config = initialize_agent()
        if node_config.get("profile"):
            base_config.profile = node_config["profile"]
        agent = Agent(
            number=self.parent_agent.number + agent_number,
            config=base_config,
            context=self.parent_agent.context,
        )
        agent.set_data("_workflow_id", self.workflow_id)
        agent.set_data("_workflow_node", node_config["id"])
        agent.set_data(Agent.DATA_NAME_SUPERIOR, self.parent_agent)
        return agent

    async def _execute_node(
        self,
        node_id: str,
        input_message: str,
    ) -> WorkflowStepResult:
        """Execute a single node in the graph."""
        node_config = self._nodes.get(node_id)
        if not node_config:
            return WorkflowStepResult(
                agent_name="unknown",
                agent_number=0,
                success=False,
                output="",
                error=f"Node not found: {node_id}",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                duration_seconds=0.0,
            )

        step_start = datetime.now(timezone.utc)
        agent_name = node_config.get("agent", "developer")

        try:
            # Create and execute agent
            agent = await self._create_agent(node_config, len(self._executed_nodes) + 1)

            # Build input message with prompt template if provided
            if node_config.get("prompt"):
                formatted_input = self._format_prompt(
                    node_config["prompt"],
                    input_message,
                )
            else:
                formatted_input = input_message

            agent.hist_add_user_message(UserMessage(message=formatted_input, attachments=[]))

            async def run_agent():
                return await agent.monologue()

            try:
                result = await asyncio.wait_for(
                    run_agent(),
                    timeout=node_config.get("timeout", self.node_timeout),
                )
            except asyncio.TimeoutError:
                raise WorkflowTimeoutError(
                    f"Node {node_id} exceeded timeout of {node_config.get('timeout', self.node_timeout)}s"
                )

            agent.history.new_topic()
            step_end = datetime.now(timezone.utc)

            return WorkflowStepResult(
                agent_name=f"{node_id}:{agent.agent_name}",
                agent_number=agent.number,
                success=True,
                output=result,
                error=None,
                start_time=step_start,
                end_time=step_end,
                duration_seconds=(step_end - step_start).total_seconds(),
            )

        except WorkflowTimeoutError as e:
            step_end = datetime.now(timezone.utc)
            return WorkflowStepResult(
                agent_name=f"{node_id}:{agent_name}",
                agent_number=0,
                success=False,
                output="",
                error=str(e),
                start_time=step_start,
                end_time=step_end,
                duration_seconds=(step_end - step_start).total_seconds(),
            )

        except Exception as e:
            step_end = datetime.now(timezone.utc)
            logger.exception(f"Error executing graph node {node_id}")
            return WorkflowStepResult(
                agent_name=f"{node_id}:{agent_name}",
                agent_number=0,
                success=False,
                output="",
                error=f"{type(e).__name__}: {str(e)}",
                start_time=step_start,
                end_time=step_end,
                duration_seconds=(step_end - step_start).total_seconds(),
            )

    def _format_prompt(self, template: str, input_text: str) -> str:
        """Format a prompt template with input text."""
        # Support basic template variables
        try:
            return template.replace("{input}", input_text).replace(
                "{INPUT}", input_text
            )
        except Exception:
            return f"{template}\n\n---\n{input_text}"

    async def execute(
        self,
        initial_input: str,
        nodes: list,
        edges: list,
        entry: str,
    ) -> WorkflowResult:
        """
        Execute the graph workflow.

        Args:
            initial_input: Initial input for the entry node
            nodes: List of node definitions
            edges: List of edge definitions
            entry: ID of the entry node

        Returns:
            WorkflowResult with execution details
        """
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._results = []
        self._node_outputs = {}
        self._executed_nodes = set()
        self._iteration_count = 0

        try:
            # Parse graph structure
            self._nodes = self._parse_nodes(nodes)
            self._edges = self._parse_edges(edges)

            if entry not in self._nodes:
                raise WorkflowExecutionError(f"Entry node '{entry}' not found in nodes")

            # Track nodes to execute (supports parallel execution)
            pending_nodes: list[tuple[str, str]] = [(entry, initial_input)]
            final_output = ""

            logger.info(
                f"GraphWorkflow {self.workflow_id}: Starting with entry node '{entry}'"
            )

            async def run_graph():
                nonlocal final_output
                nonlocal pending_nodes

                while pending_nodes and self._iteration_count < self.max_iterations:
                    self._iteration_count += 1

                    # Get next batch of nodes to execute
                    current_batch = pending_nodes[:]
                    pending_nodes = []

                    # Execute batch in parallel (fan-out)
                    if len(current_batch) > 1:
                        tasks = [
                            self._execute_node(node_id, node_input)
                            for node_id, node_input in current_batch
                        ]
                        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                        for (node_id, _), result in zip(current_batch, batch_results):
                            if isinstance(result, Exception):
                                self._results.append(WorkflowStepResult(
                                    agent_name=node_id,
                                    agent_number=0,
                                    success=False,
                                    output="",
                                    error=f"{type(result).__name__}: {str(result)}",
                                    start_time=datetime.now(timezone.utc),
                                    end_time=datetime.now(timezone.utc),
                                    duration_seconds=0.0,
                                ))
                            elif isinstance(result, WorkflowStepResult):
                                self._results.append(result)
                                if result.success:
                                    self._node_outputs[node_id] = result.output
                                    self._executed_nodes.add(node_id)
                                elif self.fail_fast:
                                    return WorkflowStatus.FAILED
                    else:
                        # Single node execution
                        node_id, node_input = current_batch[0]
                        if node_id in self._executed_nodes:
                            # Skip already executed nodes (prevents loops without conditions)
                            continue

                        result = await self._execute_node(node_id, node_input)
                        self._results.append(result)

                        if result.success:
                            self._node_outputs[node_id] = result.output
                            self._executed_nodes.add(node_id)
                        elif self.fail_fast:
                            return WorkflowStatus.FAILED

                    # Find next nodes for each completed node in batch
                    for node_id, _ in current_batch:
                        if node_id not in self._node_outputs:
                            continue

                        node_output = self._node_outputs[node_id]
                        outgoing_edges = self._get_outgoing_edges(node_id)

                        for edge in outgoing_edges:
                            to_node = edge["to"]

                            # Skip if already executed (simple loop prevention)
                            if to_node in self._executed_nodes and not edge.get("condition"):
                                continue

                            # Evaluate condition if present
                            if edge.get("condition"):
                                context = {
                                    "output": node_output,
                                    "success": True,
                                    "node_outputs": self._node_outputs.copy(),
                                    "iteration": self._iteration_count,
                                }
                                if not self._evaluate_condition(edge["condition"], context):
                                    continue

                            # Queue next node
                            pending_nodes.append((to_node, node_output))
                            final_output = node_output

                # Check for max iterations
                if self._iteration_count >= self.max_iterations:
                    logger.warning(
                        f"GraphWorkflow {self.workflow_id}: Reached max iterations ({self.max_iterations})"
                    )

                return WorkflowStatus.COMPLETED

            try:
                status = await asyncio.wait_for(run_graph(), timeout=self.timeout)
            except asyncio.TimeoutError:
                status = WorkflowStatus.TIMEOUT
                final_output = f"Graph workflow exceeded total timeout of {self.timeout}s"

            # Determine final output from last successful node
            if self._node_outputs and status == WorkflowStatus.COMPLETED:
                final_output = list(self._node_outputs.values())[-1]

            return self._create_workflow_result(
                status=status,
                final_output=final_output,
                metadata={
                    "total_nodes": len(self._nodes),
                    "executed_nodes": len(self._executed_nodes),
                    "total_iterations": self._iteration_count,
                    "node_outputs": self._node_outputs,
                    "entry_node": entry,
                },
            )

        except Exception as e:
            logger.exception(f"GraphWorkflow {self.workflow_id} failed")
            return self._create_workflow_result(
                status=WorkflowStatus.FAILED,
                final_output="",
                metadata={"error": str(e)},
            )


class swarm_graph(Tool):
    """Tool for executing a graph-based workflow with conditional branching."""

    async def execute(
        self,
        nodes="",
        edges="",
        entry="",
        initial_input="",
        workflow_id="",
        timeout="600",
        node_timeout="300",
        max_iterations="100",
        fail_fast="true",
        **kwargs,
    ):
        try:
            # Parse nodes and edges
            if not nodes:
                return Response(
                    message="Error: No nodes specified. Provide nodes as JSON array.",
                    break_loop=False,
                )

            if not entry:
                return Response(
                    message="Error: No entry node specified. Provide 'entry' parameter.",
                    break_loop=False,
                )

            try:
                timeout_val = float(timeout)
                node_timeout_val = float(node_timeout)
                max_iterations_val = int(max_iterations)
            except ValueError:
                return Response(
                    message="Error: Invalid numeric parameters",
                    break_loop=False,
                )

            fail_fast_val = str(fail_fast).lower().strip() == "true"

            workflow = GraphWorkflow(
                parent_agent=self.agent,
                workflow_id=workflow_id,
                timeout=timeout_val,
                node_timeout=node_timeout_val,
                max_iterations=max_iterations_val,
                fail_fast=fail_fast_val,
            )

            input_msg = initial_input or self.message or "Execute the graph workflow."

            result = await workflow.execute(
                initial_input=input_msg,
                nodes=nodes,
                edges=edges,
                entry=entry,
            )

            response_text = self._format_result(result)
            return Response(
                message=response_text,
                break_loop=False,
                additional={
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "executed_nodes": list(workflow._executed_nodes),
                },
            )

        except Exception as e:
            logger.exception("Graph workflow execution failed")
            return Response(
                message=f"Graph workflow failed: {type(e).__name__}: {str(e)}",
                break_loop=False,
            )

    def _format_result(self, result: WorkflowResult) -> str:
        """Format the graph workflow result for display."""
        lines = [
            f"# Graph Workflow: {result.workflow_id}",
            f"**Status**: {result.status.value.upper()}",
            f"**Duration**: {result.total_duration_seconds:.2f}s",
            f"**Total Iterations**: {result.metadata.get('total_iterations', 0)}",
            "",
        ]

        executed = result.metadata.get("executed_nodes", 0)
        total = result.metadata.get("total_nodes", 0)
        lines.append(f"**Nodes Executed**: {executed}/{total}")
        lines.append("")

        lines.append("## Execution Path")
        lines.append("")

        for i, step in enumerate(result.steps, 1):
            status_icon = "OK" if step.success else "FAIL"
            lines.append(f"### Step {i}: {step.agent_name} [{status_icon}]")
            lines.append(f"**Duration**: {step.duration_seconds:.2f}s")
            if step.error:
                lines.append(f"**Error**: {step.error}")
            if step.success and step.output:
                output_preview = step.output[:300] + "..." if len(step.output) > 300 else step.output
                lines.append(f"**Output Preview**: {output_preview}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Final Output")
        lines.append(result.final_output)

        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://construction {self.agent.agent_name}: Executing Graph Workflow",
            content="",
            kvps=self.args,
        )
