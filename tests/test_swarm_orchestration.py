"""
Integration Tests for Swarm Orchestration System

Tests all workflow patterns: Sequential, Concurrent, Graph, MajorityVoting,
StarSwarm, HierarchicalSwarm, and MixtureOfAgents.

Uses heavy mocking to isolate tests from Agent Zero framework dependencies.
"""

import asyncio
import json
import pytest
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# =============================================================================
# MOCK DEPENDENCIES BEFORE IMPORTS
# =============================================================================

# Mock agent module
mock_agent_module = MagicMock()
mock_agent_class = MagicMock()
mock_agent_module.Agent = mock_agent_class
mock_agent_module.UserMessage = MagicMock
sys.modules["agent"] = mock_agent_module

# Mock initialize module
mock_initialize = MagicMock()
mock_initialize.initialize_agent = MagicMock()
sys.modules["initialize"] = mock_initialize

# Mock python.helpers modules
mock_tool_module = MagicMock()
mock_tool_module.Tool = MagicMock()
mock_tool_module.Response = MagicMock
sys.modules["python.helpers.tool"] = mock_tool_module

mock_subagents = MagicMock()
mock_subagents.load_agent_data = MagicMock()
sys.modules["python.helpers.subagents"] = mock_subagents

mock_files = MagicMock()
sys.modules["python.helpers.files"] = mock_files

mock_embeddings = MagicMock()
mock_embeddings.get_embeddings_model = MagicMock()
sys.modules["python.helpers.embeddings"] = mock_embeddings

# Now import the actual modules we want to test
from python.helpers.swarm_orchestration import (
    AgentConfig,
    WorkflowStatus,
    WorkflowStepResult,
    WorkflowResult,
    WorkflowTimeoutError,
    WorkflowExecutionError,
    BaseWorkflow,
)

from python.tools.swarm_consensus import (MajorityVoting, MixtureOfAgents, VoteResult, LLMCouncil, DebateWithJudge)

from python.tools.swarm_patterns import (StarSwarm, HierarchicalSwarm, SwarmRouter, RoundRobinSwarm, GroupChat, ForestSwarm, SpreadSheetSwarm, AutoSwarmBuilder)

from python.tools.swarm_consensus import (MajorityVoting, MixtureOfAgents, VoteResult, LLMCouncil, DebateWithJudge)

from python.tools.swarm_patterns import (StarSwarm, HierarchicalSwarm, SwarmRouter, RoundRobinSwarm, GroupChat, ForestSwarm, SpreadSheetSwarm, AutoSwarmBuilder)

from python.tools.swarm_workflow import (SequentialWorkflow, ConcurrentWorkflow, GraphWorkflow)

    agent.history = MagicMock()
    agent.history.new_topic = MagicMock()
    agent.set_data = MagicMock()
    agent.monologue = AsyncMock(return_value="Test agent response")
    agent.call_llm = AsyncMock(return_value="LLM response")
    return agent


@pytest.fixture
def agent_configs():
    """Sample agent configurations for testing."""
    return [
        AgentConfig(name="agent1", profile="developer", timeout=60.0),
        AgentConfig(name="agent2", profile="researcher", timeout=60.0),
        AgentConfig(name="agent3", profile="coder", timeout=60.0),
    ]


# =============================================================================
# SEQUENTIAL WORKFLOW TESTS
# =============================================================================

class TestSequentialWorkflow:
    """Tests for SequentialWorkflow execution."""

    @pytest.mark.asyncio
    async def test_sequential_workflow_basic(self, mock_agent):
        """Test basic sequential workflow execution."""
        workflow = SequentialWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_seq_1",
            timeout=60.0,
            step_timeout=10.0,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            mock_agent1 = MagicMock()
            mock_agent1.agent_name = "agent_1"
            mock_agent1.number = 2
            mock_agent1.hist_add_user_message = MagicMock()
            mock_agent1.history = MagicMock()
            mock_agent1.history.new_topic = MagicMock()
            mock_agent1.monologue = AsyncMock(return_value="Step 1 output")

            mock_agent2 = MagicMock()
            mock_agent2.agent_name = "agent_2"
            mock_agent2.number = 3
            mock_agent2.hist_add_user_message = MagicMock()
            mock_agent2.history = MagicMock()
            mock_agent2.history.new_topic = MagicMock()
            mock_agent2.monologue = AsyncMock(return_value="Step 2 output")

            mock_create.side_effect = [mock_agent1, mock_agent2]

            agents = ["agent1", "agent2"]
            result = await workflow.execute(
                initial_input="Initial task",
                agents=agents,
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert result.workflow_id == "test_seq_1"
            assert len(result.steps) == 2
            assert result.steps[0].success is True
            assert result.steps[1].success is True

    @pytest.mark.asyncio
    async def test_sequential_workflow_fail_fast(self, mock_agent):
        """Test sequential workflow stops on failure when fail_fast=True."""
        workflow = SequentialWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_seq_fail",
            timeout=60.0,
            step_timeout=10.0,
            fail_fast=True,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            mock_agent1 = MagicMock()
            mock_agent1.agent_name = "agent_1"
            mock_agent1.number = 2
            mock_agent1.hist_add_user_message = MagicMock()
            mock_agent1.history = MagicMock()
            mock_agent1.history.new_topic = MagicMock()
            mock_agent1.monologue = AsyncMock(side_effect=Exception("Agent failed"))

            mock_create.return_value = mock_agent1

            agents = ["agent1", "agent2", "agent3"]
            result = await workflow.execute(
                initial_input="Task that will fail",
                agents=agents,
            )

            assert result.status == WorkflowStatus.FAILED
            assert len(result.steps) == 1
            assert result.steps[0].success is False

    @pytest.mark.asyncio
    async def test_sequential_workflow_timeout(self, mock_agent):
        """Test sequential workflow handles timeouts."""
        workflow = SequentialWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_seq_timeout",
            timeout=0.1,
            step_timeout=0.05,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            mock_agent1 = MagicMock()
            mock_agent1.agent_name = "agent_1"
            mock_agent1.number = 2
            mock_agent1.hist_add_user_message = MagicMock()
            mock_agent1.history = MagicMock()
            mock_agent1.history.new_topic = MagicMock()

            async def slow_monologue():
                await asyncio.sleep(1)
                return "Should not return"

            mock_agent1.monologue = slow_monologue
            mock_create.return_value = mock_agent1

            agents = ["agent1"]
            result = await workflow.execute(
                initial_input="Task that will timeout",
                agents=agents,
            )

            assert result.status in [WorkflowStatus.TIMEOUT, WorkflowStatus.FAILED]

    @pytest.mark.asyncio
    async def test_sequential_workflow_continue_on_failure(self, mock_agent):
        """Test sequential workflow continues when fail_fast=False."""
        workflow = SequentialWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_seq_continue",
            timeout=60.0,
            step_timeout=10.0,
            fail_fast=False,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            mock_agent1 = MagicMock()
            mock_agent1.agent_name = "agent_1"
            mock_agent1.number = 2
            mock_agent1.hist_add_user_message = MagicMock()
            mock_agent1.history = MagicMock()
            mock_agent1.history.new_topic = MagicMock()
            mock_agent1.monologue = AsyncMock(side_effect=Exception("Agent 1 failed"))

            mock_agent2 = MagicMock()
            mock_agent2.agent_name = "agent_2"
            mock_agent2.number = 3
            mock_agent2.hist_add_user_message = MagicMock()
            mock_agent2.history = MagicMock()
            mock_agent2.history.new_topic = MagicMock()
            mock_agent2.monologue = AsyncMock(return_value="Agent 2 succeeded")

            mock_create.side_effect = [mock_agent1, mock_agent2]

            agents = ["agent1", "agent2"]
            result = await workflow.execute(
                initial_input="Task",
                agents=agents,
            )

            assert len(result.steps) == 2
            assert result.steps[0].success is False
            assert result.steps[1].success is True


# =============================================================================
# CONCURRENT WORKFLOW TESTS
# =============================================================================

class TestConcurrentWorkflow:
    """Tests for ConcurrentWorkflow execution."""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_basic(self, mock_agent):
        """Test basic concurrent workflow execution."""
        workflow = ConcurrentWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_conc_1",
            timeout=60.0,
            agent_timeout=10.0,
            aggregation="concat",
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            agents = []
            for i in range(3):
                a = MagicMock()
                a.agent_name = f"agent_{i+1}"
                a.number = i + 2
                a.hist_add_user_message = MagicMock()
                a.history = MagicMock()
                a.history.new_topic = MagicMock()
                a.monologue = AsyncMock(return_value=f"Output {i+1}")
                agents.append(a)

            mock_create.side_effect = agents

            agent_specs = ["agent1", "agent2", "agent3"]
            result = await workflow.execute(
                initial_input="Parallel task",
                agents=agent_specs,
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert len(result.steps) == 3
            assert all(s.success for s in result.steps)

    @pytest.mark.asyncio
    async def test_concurrent_workflow_aggregation_concat(self, mock_agent):
        """Test concat aggregation strategy."""
        workflow = ConcurrentWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_conc_concat",
            aggregation="concat",
            separator="\n---\n",
        )

        results = [
            WorkflowStepResult(
                agent_name="a1",
                agent_number=1,
                success=True,
                output="Result 1",
            ),
            WorkflowStepResult(
                agent_name="a2",
                agent_number=2,
                success=True,
                output="Result 2",
            ),
        ]

        aggregated = await workflow._aggregate_results(results)
        assert "Result 1" in aggregated
        assert "Result 2" in aggregated

    @pytest.mark.asyncio
    async def test_concurrent_workflow_partial_failure(self, mock_agent):
        """Test concurrent workflow handles partial failures."""
        workflow = ConcurrentWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_conc_partial",
            aggregation="concat",
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            mock_agent1 = MagicMock()
            mock_agent1.agent_name = "agent_1"
            mock_agent1.number = 2
            mock_agent1.hist_add_user_message = MagicMock()
            mock_agent1.history = MagicMock()
            mock_agent1.history.new_topic = MagicMock()
            mock_agent1.monologue = AsyncMock(side_effect=Exception("Agent 1 failed"))

            mock_agent2 = MagicMock()
            mock_agent2.agent_name = "agent_2"
            mock_agent2.number = 3
            mock_agent2.hist_add_user_message = MagicMock()
            mock_agent2.history = MagicMock()
            mock_agent2.history.new_topic = MagicMock()
            mock_agent2.monologue = AsyncMock(return_value="Agent 2 output")

            mock_create.side_effect = [mock_agent1, mock_agent2]

            agents = ["agent1", "agent2"]
            result = await workflow.execute(
                initial_input="Task",
                agents=agents,
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert len([s for s in result.steps if s.success]) == 1


# =============================================================================
# GRAPH WORKFLOW TESTS
# =============================================================================

class TestGraphWorkflow:
    """Tests for GraphWorkflow with conditional edges."""

    @pytest.mark.asyncio
    async def test_graph_workflow_linear(self, mock_agent):
        """Test linear graph workflow (A -> B -> C)."""
        workflow = GraphWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_graph_linear",
            timeout=60.0,
            node_timeout=10.0,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            agents = []
            for i in range(3):
                a = MagicMock()
                a.agent_name = f"node_{chr(65+i)}"
                a.number = i + 2
                a.hist_add_user_message = MagicMock()
                a.history = MagicMock()
                a.history.new_topic = MagicMock()
                a.monologue = AsyncMock(return_value=f"Node {chr(65+i)} output")
                agents.append(a)

            mock_create.side_effect = agents

            nodes = [
                {"id": "A", "agent": "developer"},
                {"id": "B", "agent": "researcher"},
                {"id": "C", "agent": "coder"},
            ]
            edges = [
                {"from": "A", "to": "B"},
                {"from": "B", "to": "C"},
            ]

            result = await workflow.execute(
                initial_input="Start task",
                nodes=nodes,
                edges=edges,
                entry="A",
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert len(workflow._executed_nodes) == 3

    @pytest.mark.asyncio
    async def test_graph_workflow_conditional_branching(self, mock_agent):
        """Test graph workflow with conditional edges."""
        workflow = GraphWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_graph_cond",
            timeout=60.0,
        )

        context = {
            "output": "yes proceed",
            "success": True,
            "node_outputs": {},
            "iteration": 1,
        }

        assert workflow._evaluate_condition('"proceed" in output', context) is True
        assert workflow._evaluate_condition('"cancel" in output', context) is False

    @pytest.mark.asyncio
    async def test_graph_workflow_invalid_entry(self, mock_agent):
        """Test graph workflow with invalid entry node."""
        workflow = GraphWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_graph_invalid",
            timeout=60.0,
        )

        nodes = [{"id": "A", "agent": "developer"}]
        edges = []

        result = await workflow.execute(
            initial_input="Task",
            nodes=nodes,
            edges=edges,
            entry="nonexistent",
        )

        assert result.status == WorkflowStatus.FAILED


# =============================================================================
# MAJORITY VOTING TESTS
# =============================================================================

class TestMajorityVoting:
    """Tests for MajorityVoting consensus mechanism."""

    @pytest.mark.asyncio
    async def test_majority_voting_exact_strategy(self, mock_agent):
        """Test exact match voting strategy."""
        workflow = MajorityVoting(
            parent_agent=mock_agent,
            workflow_id="test_vote_exact",
            voting_strategy="exact",
            tie_break="first",
        )

        answers = [
            ("agent1", "The answer is 42"),
            ("agent2", "The answer is 42"),
            ("agent3", "The answer is 100"),
        ]

        result = workflow._exact_vote(answers)

        assert result.winning_answer == "The answer is 42"
        assert result.vote_count == 2
        assert result.confidence == pytest.approx(2/3, rel=0.01)
        assert result.winner_agent == "agent1"

    @pytest.mark.asyncio
    async def test_majority_voting_tie_breaking(self, mock_agent):
        """Test tie-breaking in voting."""
        workflow = MajorityVoting(
            parent_agent=mock_agent,
            workflow_id="test_vote_tie",
            voting_strategy="exact",
            tie_break="first",
        )

        answers = [
            ("agent1", "Answer A"),
            ("agent2", "Answer B"),
        ]

        result = workflow._exact_vote(answers)

        assert result.tie_broken is True
        assert result.tie_break_method == "first"
        assert result.winning_answer in ["Answer A", "Answer B"]

    @pytest.mark.asyncio
    async def test_majority_voting_full_execution(self, mock_agent):
        """Test full voting workflow execution."""
        workflow = MajorityVoting(
            parent_agent=mock_agent,
            workflow_id="test_vote_full",
            voting_strategy="exact",
            max_concurrency=5,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            agents = []
            for i in range(3):
                a = MagicMock()
                a.agent_name = f"voter_{i+1}"
                a.number = i + 2
                a.hist_add_user_message = MagicMock()
                a.history = MagicMock()
                a.history.new_topic = MagicMock()
                a.monologue = AsyncMock(return_value="Consensus answer")
                agents.append(a)

            mock_create.side_effect = agents

            result = await workflow.execute(
                initial_input="What is 2+2?",
                agents=["voter1", "voter2", "voter3"],
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert result.vote_result is not None
            assert result.vote_result.vote_count == 3


# =============================================================================
# STAR SWARM TESTS
# =============================================================================

class TestStarSwarm:
    """Tests for StarSwarm hub-and-spoke pattern."""

    @pytest.mark.asyncio
    async def test_star_swarm_decomposition(self, mock_agent):
        """Test task decomposition phase."""
        workflow = StarSwarm(
            parent_agent=mock_agent,
            workflow_id="test_star_decomp",
        )

        decomposition_output = """---SUBTASK 1---
Role: Data Analyst
Objective: Analyze the data
Instructions: Process the dataset
---SUBTASK 2---
Role: Writer
Objective: Write report
Instructions: Create a summary
"""
        subtasks = workflow._parse_subtasks(decomposition_output, 2)

        assert len(subtasks) == 2
        assert subtasks[0].role == "Data Analyst"
        assert subtasks[1].role == "Writer"

    @pytest.mark.asyncio
    async def test_star_swarm_fallback_subtasks(self, mock_agent):
        """Test fallback subtask creation when parsing fails."""
        workflow = StarSwarm(
            parent_agent=mock_agent,
            workflow_id="test_star_fallback",
        )

        subtasks = workflow._parse_subtasks("Invalid output", 3)

        assert len(subtasks) == 3
        assert all(s.role.startswith("Agent") for s in subtasks)

    @pytest.mark.asyncio
    async def test_star_swarm_full_execution(self, mock_agent):
        """Test full StarSwarm execution with all phases."""
        workflow = StarSwarm(
            parent_agent=mock_agent,
            workflow_id="test_star_full",
            hub_timeout=10.0,
            spoke_timeout=10.0,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            hub = MagicMock()
            hub.agent_name = "hub_coordinator"
            hub.number = 2
            hub.hist_add_user_message = MagicMock()
            hub.history = MagicMock()
            hub.history.new_topic = MagicMock()
            hub.monologue = AsyncMock(return_value="""---SUBTASK 1---
Role: Researcher
Objective: Research topic
Instructions: Find information
---SUBTASK 2---
Role: Writer
Objective: Write summary
Instructions: Create report
""")

            spoke1 = MagicMock()
            spoke1.agent_name = "spoke_1"
            spoke1.number = 3
            spoke1.hist_add_user_message = MagicMock()
            spoke1.history = MagicMock()
            spoke1.history.new_topic = MagicMock()
            spoke1.monologue = AsyncMock(return_value="Research results")

            spoke2 = MagicMock()
            spoke2.agent_name = "spoke_2"
            spoke2.number = 4
            spoke2.hist_add_user_message = MagicMock()
            spoke2.history = MagicMock()
            spoke2.history.new_topic = MagicMock()
            spoke2.monologue = AsyncMock(return_value="Written report")

            mock_create.side_effect = [hub, spoke1, spoke2, hub]

            result = await workflow.execute(
                initial_input="Research and report on AI trends",
                agents=["spoke1", "spoke2"],
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert len(result.subtasks) >= 1


# =============================================================================
# HIERARCHICAL SWARM TESTS
# =============================================================================

class TestHierarchicalSwarm:
    """Tests for HierarchicalSwarm multi-level pattern."""

    @pytest.mark.asyncio
    async def test_hierarchical_manager_task_parsing(self, mock_agent):
        """Test parsing of manager tasks from root decomposition."""
        workflow = HierarchicalSwarm(
            parent_agent=mock_agent,
            workflow_id="test_hier_parse",
        )

        decomposition = """---MANAGER TASK 1---
Role: Data Team Lead
Objective: Process data
Instructions: ETL pipeline
---MANAGER TASK 2---
Role: Analytics Lead
Objective: Analyze results
Instructions: Generate insights
"""
        tasks = workflow._parse_manager_tasks(decomposition, 2)

        assert len(tasks) == 2
        assert tasks[0].role == "Data Team Lead"
        assert tasks[1].role == "Analytics Lead"

    @pytest.mark.asyncio
    async def test_hierarchical_worker_task_parsing(self, mock_agent):
        """Test parsing of worker tasks from manager decomposition."""
        workflow = HierarchicalSwarm(
            parent_agent=mock_agent,
            workflow_id="test_hier_worker",
        )

        decomposition = """---WORKER TASK 1---
Role: Data Engineer
Objective: Extract data
Instructions: Pull from API
---WORKER TASK 2---
Role: Data Scientist
Objective: Transform data
Instructions: Clean and normalize
"""
        tasks = workflow._parse_worker_tasks(decomposition, "Data Team Lead", 2)

        assert len(tasks) == 2
        assert tasks[0].role == "Data Engineer"
        assert tasks[1].role == "Data Scientist"


# =============================================================================
# MIXTURE OF AGENTS TESTS
# =============================================================================

class TestMixtureOfAgents:
    """Tests for MixtureOfAgents consensus pattern."""

    @pytest.mark.asyncio
    async def test_moa_single_round(self, mock_agent):
        """Test MoA with single round."""
        workflow = MixtureOfAgents(
            parent_agent=mock_agent,
            workflow_id="test_moa_single",
            rounds=1,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            proposers = []
            for i in range(2):
                p = MagicMock()
                p.agent_name = f"proposer_{i+1}"
                p.number = i + 2
                p.hist_add_user_message = MagicMock()
                p.history = MagicMock()
                p.history.new_topic = MagicMock()
                p.monologue = AsyncMock(return_value=f"Proposal {i+1}")
                proposers.append(p)

            aggregator = MagicMock()
            aggregator.agent_name = "aggregator"
            aggregator.number = 4
            aggregator.hist_add_user_message = MagicMock()
            aggregator.history = MagicMock()
            aggregator.history.new_topic = MagicMock()
            aggregator.monologue = AsyncMock(return_value="Synthesized answer")

            mock_create.side_effect = proposers + [aggregator]

            result = await workflow.execute(
                task="Solve this problem",
                proposers=["p1", "p2"],
                aggregator="agg",
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert len(result.rounds) == 1
            assert result.final_answer == "Synthesized answer"

    @pytest.mark.asyncio
    async def test_moa_multi_round(self, mock_agent):
        """Test MoA with multiple refinement rounds."""
        workflow = MixtureOfAgents(
            parent_agent=mock_agent,
            workflow_id="test_moa_multi",
            rounds=2,
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            call_count = [0]
            def create_side_effect(config, num):
                a = MagicMock()
                a.agent_name = f"agent_{call_count[0]}"
                a.number = num
                a.hist_add_user_message = MagicMock()
                a.history = MagicMock()
                a.history.new_topic = MagicMock()
                a.monologue = AsyncMock(return_value=f"Response {call_count[0]}")
                call_count[0] += 1
                return a

            mock_create.side_effect = create_side_effect

            result = await workflow.execute(
                task="Complex problem",
                proposers=["p1"],
                aggregator="agg",
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert len(result.rounds) == 2


# =============================================================================
# ERROR HANDLING AND TIMEOUT TESTS
# =============================================================================

class TestErrorHandlingAndTimeouts:
    """Tests for error handling and timeout scenarios."""

    @pytest.mark.asyncio
    async def test_workflow_timeout_exception(self, mock_agent):
        """Test WorkflowTimeoutError is raised correctly."""
        error = WorkflowTimeoutError("Agent timed out after 30s")
        assert "timed out" in str(error)

    @pytest.mark.asyncio
    async def test_workflow_execution_exception(self, mock_agent):
        """Test WorkflowExecutionError is raised correctly."""
        error = WorkflowExecutionError("Execution failed")
        assert "Execution failed" in str(error)

    @pytest.mark.asyncio
    async def test_invalid_agent_spec(self, mock_agent):
        """Test handling of invalid agent specifications."""
        workflow = SequentialWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_invalid_spec",
        )

        with pytest.raises(ValueError):
            workflow._parse_agent_config(12345)

    @pytest.mark.asyncio
    async def test_agent_config_parsing(self, mock_agent):
        """Test various agent config parsing formats."""
        workflow = SequentialWorkflow(
            parent_agent=mock_agent,
            workflow_id="test_config_parse",
        )

        config1 = workflow._parse_agent_config("agent_name")
        assert config1.name == "agent_name"

        config2 = workflow._parse_agent_config({
            "name": "agent2",
            "profile": "developer",
            "timeout": 60.0,
        })
        assert config2.name == "agent2"
        assert config2.profile == "developer"

        config3 = workflow._parse_agent_config(
            AgentConfig(name="agent3", timeout=30.0)
        )
        assert config3.name == "agent3"


# =============================================================================
# DATA STRUCTURE TESTS
# =============================================================================

class TestDataStructures:
    """Tests for data structures and serialization."""

    def test_workflow_step_result_to_dict(self):
        """Test WorkflowStepResult serialization."""
        result = WorkflowStepResult(
            agent_name="test_agent",
            agent_number=1,
            success=True,
            output="Test output",
            error=None,
            duration_seconds=1.5,
        )

        d = result.to_dict()
        assert d["agent_name"] == "test_agent"
        assert d["success"] is True
        assert d["output"] == "Test output"

    def test_workflow_result_to_dict(self):
        """Test WorkflowResult serialization."""
        result = WorkflowResult(
            workflow_id="test_123",
            workflow_type="SequentialWorkflow",
            status=WorkflowStatus.COMPLETED,
            steps=[],
            final_output="Done",
            total_duration_seconds=5.0,
            metadata={"key": "value"},
        )

        d = result.to_dict()
        assert d["workflow_id"] == "test_123"
        assert d["status"] == "completed"
        assert d["metadata"]["key"] == "value"

    def test_vote_result_to_dict(self):
        """Test VoteResult serialization."""
        result = VoteResult(
            winning_answer="Answer",
            winner_agent="agent1",
            vote_count=2,
            total_votes=3,
            confidence=0.67,
            all_answers=[],
            voting_strategy="exact",
        )

        d = result.to_dict()
        assert d["winning_answer"] == "Answer"
        assert d["confidence"] == pytest.approx(0.67, rel=0.01)

    def test_subtask_to_prompt(self):
        """Test Subtask prompt generation."""
        subtask = Subtask(
            index=1,
            role="Data Analyst",
            objective="Analyze data",
            instructions="Process the dataset",
        )

        prompt = subtask.to_prompt()
        assert "Data Analyst" in prompt
        assert "Analyze data" in prompt
        assert "Process the dataset" in prompt


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

class TestLLMCouncil:
    """Tests for LLM Council pattern."""

    @pytest.mark.asyncio
    async def test_llm_council_basic(self, mock_agent):
        """Test basic LLM Council functionality."""
        workflow = LLMCouncil(
            chairperson="chair",
            members=["member1", "member2"],
            parent_agent=mock_agent,
            workflow_id="test_council",
            timeout=60.0,
            member_timeout=10.0,
            deliberation_rounds=1
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock agents
            chair_agent = MagicMock()
            chair_agent.agent_name = "chair"
            chair_agent.number = 1
            chair_agent.hist_add_user_message = MagicMock()
            chair_agent.history = MagicMock()
            chair_agent.history.new_topic = MagicMock()
            chair_agent.monologue = AsyncMock(side_effect=[
                "Introduction to topic",
                "Final decision"
            ])
            
            member1_agent = MagicMock()
            member1_agent.agent_name = "member1"
            member1_agent.number = 2
            member1_agent.hist_add_user_message = MagicMock()
            member1_agent.history = MagicMock()
            member1_agent.history.new_topic = MagicMock()
            member1_agent.monologue = AsyncMock(return_value="Member1 position")
            
            member2_agent = MagicMock()
            member2_agent.agent_name = "member2"
            member2_agent.number = 3
            member2_agent.hist_add_user_message = MagicMock()
            member2_agent.history = MagicMock()
            member2_agent.history.new_topic = MagicMock()
            member2_agent.monologue = AsyncMock(return_value="Member2 position")
            
            mock_create.side_effect = [chair_agent, member1_agent, member2_agent, member1_agent, member2_agent, chair_agent]

            result = await workflow.execute("Test topic")

            assert result.status == WorkflowStatus.COMPLETED
            assert "Final decision" in result.decision
            assert len(result.positions) == 2
            assert len(result.deliberation) == 2


class TestDebateWithJudge:
    """Tests for Debate with Judge pattern."""

    @pytest.mark.asyncio
    async def test_debate_with_judge_basic(self, mock_agent):
        """Test basic Debate with Judge functionality."""
        workflow = DebateWithJudge(
            debater_a="proponent",
            debater_b="opponent",
            judge="judge",
            parent_agent=mock_agent,
            workflow_id="test_debate",
            timeout=60.0,
            debater_timeout=10.0,
            rounds=1
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock agents
            agent_a = MagicMock()
            agent_a.agent_name = "proponent"
            agent_a.number = 1
            agent_a.hist_add_user_message = MagicMock()
            agent_a.history = MagicMock()
            agent_a.history.new_topic = MagicMock()
            agent_a.monologue = AsyncMock(return_value="Argument for")
            
            agent_b = MagicMock()
            agent_b.agent_name = "opponent"
            agent_b.number = 2
            agent_b.hist_add_user_message = MagicMock()
            agent_b.history = MagicMock()
            agent_b.history.new_topic = MagicMock()
            agent_b.monologue = AsyncMock(return_value="Argument against")
            
            judge_agent = MagicMock()
            judge_agent.agent_name = "judge"
            judge_agent.number = 3
            judge_agent.hist_add_user_message = MagicMock()
            judge_agent.history = MagicMock()
            judge_agent.history.new_topic = MagicMock()
            judge_agent.monologue = AsyncMock(return_value="Judge verdict: FOR wins")
            
            mock_create.side_effect = [agent_a, agent_b, judge_agent, agent_a, agent_b, judge_agent]

            result = await workflow.execute("Should we implement feature X?")

            assert result.status == WorkflowStatus.COMPLETED
            assert "FOR wins" in result.verdict
            assert len(result.debate_rounds) == 1
            assert "Argument for" in result.debate_rounds[0].a_response
            assert "Argument against" in result.debate_rounds[0].b_response


class TestSwarmRouter:
    """Tests for Swarm Router pattern."""

    @pytest.mark.asyncio
    async def test_swarm_router_basic(self, mock_agent):
        """Test basic Swarm Router functionality."""
        workflow = SwarmRouter(
            agents=["agent1", "agent2"],
            router_agent="router",
            parent_agent=mock_agent,
            workflow_id="test_router",
            timeout=60.0,
            agent_timeout=10.0
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock agents
            router_agent = MagicMock()
            router_agent.agent_name = "router"
            router_agent.number = 1
            router_agent.hist_add_user_message = MagicMock()
            router_agent.history = MagicMock()
            router_agent.history.new_topic = MagicMock()
            router_agent.monologue = AsyncMock(return_value='{"selected_agent": "agent1", "reason": "Best fit", "confidence": 0.95}')
            
            selected_agent = MagicMock()
            selected_agent.agent_name = "agent1"
            selected_agent.number = 2
            selected_agent.hist_add_user_message = MagicMock()
            selected_agent.history = MagicMock()
            selected_agent.history.new_topic = MagicMock()
            selected_agent.monologue = AsyncMock(return_value="Task completed by agent1")
            
            mock_create.side_effect = [router_agent, selected_agent]

            result = await workflow.execute("Process this task")

            assert result.status == WorkflowStatus.COMPLETED
            assert "Task completed by agent1" in result.final_output
            assert len(result.routing_decisions) == 1
            assert result.routing_decisions[0].selected_agent == "agent1"


class TestRoundRobinSwarm:
    """Tests for RoundRobinSwarm pattern."""

    @pytest.mark.asyncio
    async def test_round_robin_swarm_basic(self, mock_agent):
        """Test basic RoundRobinSwarm functionality."""
        workflow = RoundRobinSwarm(
            agents=["agent1", "agent2"],
            parent_agent=mock_agent,
            workflow_id="test_round_robin",
            timeout=60.0,
            agent_timeout=10.0,
            rounds=2
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock agents
            agent1 = MagicMock()
            agent1.agent_name = "agent1"
            agent1.number = 1
            agent1.hist_add_user_message = MagicMock()
            agent1.history = MagicMock()
            agent1.history.new_topic = MagicMock()
            agent1.monologue = AsyncMock(side_effect=[
                "Agent1 round1 response",
                "Agent1 round2 response",
                "Synthesized output"
            ])
            
            agent2 = MagicMock()
            agent2.agent_name = "agent2"
            agent2.number = 2
            agent2.hist_add_user_message = MagicMock()
            agent2.history = MagicMock()
            agent2.history.new_topic = MagicMock()
            agent2.monologue = AsyncMock(side_effect=[
                "Agent2 round1 response",
                "Agent2 round2 response"
            ])
            
            mock_create.side_effect = [agent1, agent2, agent1, agent2, agent1, agent2, agent1]

            result = await workflow.execute("Collaborate on this task")

            assert result.status == WorkflowStatus.COMPLETED
            assert "Synthesized output" in result.final_output
            assert len(result.rounds) == 2
            assert len(result.rounds[0]) == 2  # Two agents in first round
            assert len(result.rounds[1]) == 2  # Two agents in second round


class TestGroupChat:
    """Tests for GroupChat pattern."""

    @pytest.mark.asyncio
    async def test_group_chat_basic(self, mock_agent):
        """Test basic GroupChat functionality."""
        workflow = GroupChat(
            agents=["agent1", "agent2"],
            parent_agent=mock_agent,
            workflow_id="test_group_chat",
            timeout=60.0,
            agent_timeout=10.0,
            max_rounds=2
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock agents
            agent1 = MagicMock()
            agent1.agent_name = "agent1"
            agent1.number = 1
            agent1.hist_add_user_message = MagicMock()
            agent1.history = MagicMock()
            agent1.history.new_topic = MagicMock()
            agent1.monologue = AsyncMock(side_effect=[
                "Agent1 first contribution",
                "Agent1 second contribution"
            ])
            
            agent2 = MagicMock()
            agent2.agent_name = "agent2"
            agent2.number = 2
            agent2.hist_add_user_message = MagicMock()
            agent2.history = MagicMock()
            agent2.history.new_topic = MagicMock()
            agent2.monologue = AsyncMock(side_effect=[
                "Agent2 first contribution",
                "Agent2 second contribution"
            ])
            
            mock_create.side_effect = [agent1, agent2, agent1, agent2, agent1, agent2]

            result = await workflow.execute("Discuss this topic")

            assert result.status == WorkflowStatus.COMPLETED
            assert len(result.messages) == 5  # SYSTEM message + 4 contributions
            assert result.messages[0].sender == "SYSTEM"
            assert result.messages[1].sender == "agent1"
            assert result.messages[2].sender == "agent2"


class TestForestSwarm:
    """Tests for ForestSwarm pattern."""

    @pytest.mark.asyncio
    async def test_forest_swarm_basic(self, mock_agent):
        """Test basic ForestSwarm functionality."""
        tree_def = {
            "root": {
                "agent": "manager",
                "children": ["worker1", "worker2"]
            },
            "worker1": {
                "agent": "developer",
                "children": []
            },
            "worker2": {
                "agent": "tester",
                "children": []
            }
        }
        
        workflow = ForestSwarm(
            trees=[tree_def],
            parent_agent=mock_agent,
            workflow_id="test_forest",
            timeout=60.0,
            agent_timeout=10.0
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock agents
            manager_agent = MagicMock()
            manager_agent.agent_name = "manager"
            manager_agent.number = 1
            manager_agent.hist_add_user_message = MagicMock()
            manager_agent.history = MagicMock()
            manager_agent.history.new_topic = MagicMock()
            manager_agent.monologue = AsyncMock(return_value="Manager output")
            
            dev_agent = MagicMock()
            dev_agent.agent_name = "developer"
            dev_agent.number = 2
            dev_agent.hist_add_user_message = MagicMock()
            dev_agent.history = MagicMock()
            dev_agent.history.new_topic = MagicMock()
            dev_agent.monologue = AsyncMock(return_value="Developer output")
            
            tester_agent = MagicMock()
            tester_agent.agent_name = "tester"
            tester_agent.number = 3
            tester_agent.hist_add_user_message = MagicMock()
            tester_agent.history = MagicMock()
            tester_agent.history.new_topic = MagicMock()
            tester_agent.monologue = AsyncMock(return_value="Tester output")
            
            synth_agent = MagicMock()
            synth_agent.agent_name = "manager"
            synth_agent.number = 1
            synth_agent.hist_add_user_message = MagicMock()
            synth_agent.history = MagicMock()
            synth_agent.history.new_topic = MagicMock()
            synth_agent.monologue = AsyncMock(return_value="Synthesized output")
            
            mock_create.side_effect = [manager_agent, dev_agent, tester_agent, synth_agent]

            result = await workflow.execute("Develop and test a feature")

            assert result.status == WorkflowStatus.COMPLETED
            assert "Synthesized output" in result.final_output
            assert len(result.tree_structures) == 1
            assert len(result.node_results) == 3


class TestSpreadSheetSwarm:
    """Tests for SpreadSheetSwarm pattern."""

    @pytest.mark.asyncio
    async def test_spreadsheet_swarm_basic(self, mock_agent):
        """Test basic SpreadSheetSwarm functionality."""
        workflow = SpreadSheetSwarm(
            agents=["agent1", "agent2", "agent3", "agent4"],
            rows=2,
            cols=2,
            parent_agent=mock_agent,
            workflow_id="test_spreadsheet",
            timeout=60.0,
            agent_timeout=10.0,
            execution_mode="parallel"
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock agents
            agents = []
            for i in range(4):
                agent = MagicMock()
                agent.agent_name = f"agent{i+1}"
                agent.number = i + 1
                agent.hist_add_user_message = MagicMock()
                agent.history = MagicMock()
                agent.history.new_topic = MagicMock()
                agent.monologue = AsyncMock(return_value=f"Agent{i+1} output")
                agents.append(agent)
            
            mock_create.side_effect = agents + [agents[0]]  # Plus one for synthesis

            result = await workflow.execute("Process data in grid")

            assert result.status == WorkflowStatus.COMPLETED
            assert "Agent1 output" in result.final_output  # From synthesis
            assert result.grid_size["rows"] == 2
            assert result.grid_size["cols"] == 2
            assert len(result.cell_results) == 4


class TestAutoSwarmBuilder:
    """Tests for AutoSwarmBuilder pattern."""

    @pytest.mark.asyncio
    async def test_auto_swarm_builder_basic(self, mock_agent):
        """Test basic AutoSwarmBuilder functionality."""
        workflow = AutoSwarmBuilder(
            builder_agent="builder",
            agent_pool=["agent1", "agent2", "agent3"],
            parent_agent=mock_agent,
            workflow_id="test_auto_builder",
            timeout=60.0,
            agent_timeout=10.0
        )

        with patch.object(workflow, "_create_agent") as mock_create:
            # Mock builder agent
            builder_agent = MagicMock()
            builder_agent.agent_name = "builder"
            builder_agent.number = 1
            builder_agent.hist_add_user_message = MagicMock()
            builder_agent.history = MagicMock()
            builder_agent.history.new_topic = MagicMock()
            builder_agent.monologue = AsyncMock(return_value='{"pattern": "sequential", "agents": ["agent1", "agent2"], "parameters": {}, "rationale": "Simple task"}')
            
            # Mock agents for sequential execution
            agent1 = MagicMock()
            agent1.agent_name = "agent1"
            agent1.number = 2
            agent1.hist_add_user_message = MagicMock()
            agent1.history = MagicMock()
            agent1.history.new_topic = MagicMock()
            agent1.monologue = AsyncMock(return_value="Agent1 output")
            
            agent2 = MagicMock()
            agent2.agent_name = "agent2"
            agent2.number = 3
            agent2.hist_add_user_message = MagicMock()
            agent2.history = MagicMock()
            agent2.history.new_topic = MagicMock()
            agent2.monologue = AsyncMock(return_value="Agent2 output")
            
            mock_create.side_effect = [builder_agent, agent1, agent2]

            result = await workflow.execute("Simple processing task")

            assert result.status == WorkflowStatus.COMPLETED
            assert result.plan.pattern == "sequential"
            assert len(result.plan.agents) == 2
            assert "Agent2 output" in result.final_output
