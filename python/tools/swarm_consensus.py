"""
Swarm Consensus Tools for Agent Zero

Implements majority voting consensus mechanisms for multi-agent decision making.
Supports exact matching, semantic similarity clustering, and LLM-based judging.
"""

import asyncio
import logging
import re
import uuid
from collections import Counter
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
)
from initialize import initialize_agent

logger = logging.getLogger(__name__)


class VotingStrategy(Enum):
    """Strategies for determining consensus among agent responses."""
    EXACT = "exact"           # Exact string match after normalization
    SEMANTIC = "semantic"      # Embedding similarity clustering
    LLM = "llm"               # LLM as judge


class TieBreakStrategy(Enum):
    """Strategies for breaking ties in voting."""
    FIRST = "first"           # First response wins
    RANDOM = "random"         # Random selection among tied
    LLM = "llm"               # Use LLM to break tie
    LONGEST = "longest"       # Longest response wins
    SHORTEST = "shortest"     # Shortest response wins


@dataclass
class VoteResult:
    """Result of a voting process."""
    winning_answer: str
    winner_agent: str
    vote_count: int
    total_votes: int
    confidence: float  # vote_count / total_votes
    all_answers: list[dict[str, Any]]  # [{"agent": name, "answer": output, "votes": count}]
    voting_strategy: str
    tie_broken: bool = False
    tie_break_method: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "winning_answer": self.winning_answer,
            "winner_agent": self.winner_agent,
            "vote_count": self.vote_count,
            "total_votes": self.total_votes,
            "confidence": self.confidence,
            "all_answers": self.all_answers,
            "voting_strategy": self.voting_strategy,
            "tie_broken": self.tie_broken,
            "tie_break_method": self.tie_break_method,
        }


@dataclass
class ConsensusResult:
    """Complete result from a consensus workflow."""
    workflow_id: str
    status: WorkflowStatus
    vote_result: Optional[VoteResult]
    step_results: list[WorkflowStepResult]
    total_duration_seconds: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "vote_result": self.vote_result.to_dict() if self.vote_result else None,
            "step_results": [s.to_dict() for s in self.step_results],
            "total_duration_seconds": self.total_duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
        }


class MajorityVoting(BaseWorkflow):
    """
    Executes multiple agents in parallel on the same task and determines
    consensus through various voting strategies.
    """

    def __init__(
        self,
        parent_agent: Agent,
        workflow_id: str = "",
        timeout: float = 600.0,
        agent_timeout: float = 300.0,
        voting_strategy: str = "exact",
        tie_break: str = "first",
        similarity_threshold: float = 0.85,
        max_concurrency: int = 10,
    ):
        super().__init__(
            workflow_id=workflow_id or f"vote_{uuid.uuid4().hex[:8]}",
            timeout=timeout,
            fail_fast=False,
        )
        self.parent_agent = parent_agent
        self.agent_timeout = agent_timeout
        self.voting_strategy = VotingStrategy(voting_strategy.lower())
        self.tie_break = TieBreakStrategy(tie_break.lower())
        self.similarity_threshold = similarity_threshold
        self.max_concurrency = max_concurrency
        self._agents: list[Agent] = []
        self._results: list[WorkflowStepResult] = []

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
            logger.exception(f"Error in voting agent {agent.agent_name}")
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

    def _normalize_answer(self, text: str) -> str:
        """Normalize answer text for comparison."""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\-.,!?;:]', '', text)
        return text

    def _exact_vote(self, answers: list[tuple[str, str]]) -> VoteResult:
        """
        Perform exact match voting.
        
        Args:
            answers: List of (agent_name, answer_text) tuples
        
        Returns:
            VoteResult with winning answer
        """
        normalized_map = {}  # normalized -> original answer
        answer_counts = Counter()
        agent_answers = []  # For tracking all answers

        for agent_name, answer in answers:
            normalized = self._normalize_answer(answer)
            normalized_map[normalized] = answer  # Keep last original
            answer_counts[normalized] += 1
            agent_answers.append({
                "agent": agent_name,
                "answer": answer,
                "normalized": normalized,
            })

        # Find top vote getters
        most_common = answer_counts.most_common()
        if not most_common:
            return VoteResult(
                winning_answer="",
                winner_agent="",
                vote_count=0,
                total_votes=len(answers),
                confidence=0.0,
                all_answers=agent_answers,
                voting_strategy="exact",
            )

        top_count = most_common[0][1]
        top_answers = [norm for norm, count in most_common if count == top_count]

        # Handle tie
        tie_broken = False
        tie_break_method = None
        if len(top_answers) > 1:
            tie_broken = True
            tie_break_method = self.tie_break.value
            winner_normalized = self._break_tie(top_answers, answers, agent_answers)
        else:
            winner_normalized = top_answers[0]

        # Find the winning agent
        winner_agent = ""
        winning_answer = normalized_map.get(winner_normalized, "")
        for entry in agent_answers:
            if entry["normalized"] == winner_normalized:
                winner_agent = entry["agent"]
                break

        # Add vote counts to all_answers
        for entry in agent_answers:
            entry["votes"] = answer_counts[entry["normalized"]]

        return VoteResult(
            winning_answer=winning_answer,
            winner_agent=winner_agent,
            vote_count=top_count,
            total_votes=len(answers),
            confidence=top_count / len(answers) if answers else 0.0,
            all_answers=agent_answers,
            voting_strategy="exact",
            tie_broken=tie_broken,
            tie_break_method=tie_break_method,
        )

    async def _semantic_vote(self, answers: list[tuple[str, str]]) -> VoteResult:
        """
        Perform semantic similarity voting using embeddings.
        Clusters similar answers and selects the largest cluster.
        
        Args:
            answers: List of (agent_name, answer_text) tuples
        
        Returns:
            VoteResult with winning answer
        """
        try:
            from python.helpers import files
            from python.helpers.embeddings import get_embeddings_model
            
            # Get embeddings for all answers
            texts = [ans for _, ans in answers]
            
            try:
                embeddings_model = get_embeddings_model()
                embeddings = await embeddings_model.embed(texts)
            except Exception as e:
                logger.warning(f"Embedding failed, falling back to exact voting: {e}")
                return self._exact_vote(answers)

            # Build similarity matrix and cluster
            import numpy as np
            
            embeddings_array = np.array(embeddings)
            n = len(answers)
            
            # Compute pairwise similarities
            similarities = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i == j:
                        similarities[i][j] = 1.0
                    else:
                        # Cosine similarity
                        dot = np.dot(embeddings_array[i], embeddings_array[j])
                        norm_i = np.linalg.norm(embeddings_array[i])
                        norm_j = np.linalg.norm(embeddings_array[j])
                        if norm_i > 0 and norm_j > 0:
                            similarities[i][j] = dot / (norm_i * norm_j)
                        else:
                            similarities[i][j] = 0.0

            # Cluster answers by similarity threshold
            clusters = []
            assigned = [False] * n

            for i in range(n):
                if assigned[i]:
                    continue
                cluster = [i]
                assigned[i] = True
                for j in range(i + 1, n):
                    if not assigned[j] and similarities[i][j] >= self.similarity_threshold:
                        cluster.append(j)
                        assigned[j] = True
                clusters.append(cluster)

            # Find largest cluster
            clusters.sort(key=len, reverse=True)
            largest_cluster = clusters[0] if clusters else []

            # Check for tie in cluster sizes
            tie_broken = False
            tie_break_method = None
            if len(clusters) > 1 and len(clusters[0]) == len(clusters[1]):
                tie_broken = True
                tie_break_method = self.tie_break.value
                # Use tie-breaking to select among tied clusters
                tied_clusters = [c for c in clusters if len(c) == len(largest_cluster)]
                largest_cluster = tied_clusters[0]  # First wins by default

            # Build result
            agent_answers = []
            for i, (agent_name, answer) in enumerate(answers):
                cluster_id = next((idx for idx, c in enumerate(clusters) if i in c), -1)
                agent_answers.append({
                    "agent": agent_name,
                    "answer": answer,
                    "cluster": cluster_id,
                    "votes": len(clusters[cluster_id]) if cluster_id >= 0 else 0,
                })

            winner_idx = largest_cluster[0] if largest_cluster else 0
            winner_agent = answers[winner_idx][0]
            winning_answer = answers[winner_idx][1]

            return VoteResult(
                winning_answer=winning_answer,
                winner_agent=winner_agent,
                vote_count=len(largest_cluster),
                total_votes=len(answers),
                confidence=len(largest_cluster) / len(answers) if answers else 0.0,
                all_answers=agent_answers,
                voting_strategy="semantic",
                tie_broken=tie_broken,
                tie_break_method=tie_break_method,
            )

        except ImportError as e:
            logger.warning(f"Embeddings not available, falling back to exact voting: {e}")
            return self._exact_vote(answers)
        except Exception as e:
            logger.exception(f"Semantic voting failed, falling back to exact: {e}")
            return self._exact_vote(answers)

    async def _llm_vote(self, answers: list[tuple[str, str]]) -> VoteResult:
        """
        Use LLM as a judge to select the best answer.
        
        Args:
            answers: List of (agent_name, answer_text) tuples
        
        Returns:
            VoteResult with LLM-selected best answer
        """
        if len(answers) == 0:
            return VoteResult(
                winning_answer="",
                winner_agent="",
                vote_count=0,
                total_votes=0,
                confidence=0.0,
                all_answers=[],
                voting_strategy="llm",
            )

        if len(answers) == 1:
            return VoteResult(
                winning_answer=answers[0][1],
                winner_agent=answers[0][0],
                vote_count=1,
                total_votes=1,
                confidence=1.0,
                all_answers=[{"agent": answers[0][0], "answer": answers[0][1], "votes": 1}],
                voting_strategy="llm",
            )

        # Build judge prompt
        candidates = "\n\n".join([
            f"--- CANDIDATE {chr(65 + i)} (from {name}) ---\n{answer}"
            for i, (name, answer) in enumerate(answers)
        ])

        prompt = f"""You are an impartial judge evaluating multiple AI responses to the same question/task.
Select the SINGLE BEST response based on:
1. Accuracy and correctness
2. Completeness of the answer
3. Clarity and coherence
4. Quality of reasoning

{candidates}

Respond with ONLY the letter of the best candidate (A, B, C, etc.) on the first line.
Optionally, provide a brief explanation on subsequent lines.
Format:
[LETTER]
[Optional explanation]"""

        try:
            response = await self.parent_agent.call_llm(prompt)
            response = response.strip().upper()

            # Parse winner
            winner_idx = 0
            if response and response[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                parsed_idx = ord(response[0]) - ord("A")
                if 0 <= parsed_idx < len(answers):
                    winner_idx = parsed_idx

            winner_agent = answers[winner_idx][0]
            winning_answer = answers[winner_idx][1]

            agent_answers = [
                {
                    "agent": name,
                    "answer": answer,
                    "selected": i == winner_idx,
                    "votes": 1 if i == winner_idx else 0,
                }
                for i, (name, answer) in enumerate(answers)
            ]

            return VoteResult(
                winning_answer=winning_answer,
                winner_agent=winner_agent,
                vote_count=1,
                total_votes=len(answers),
                confidence=1.0 / len(answers),
                all_answers=agent_answers,
                voting_strategy="llm",
            )

        except Exception as e:
            logger.exception(f"LLM voting failed, falling back to exact: {e}")
            return self._exact_vote(answers)

    def _break_tie(
        self,
        tied_normalized: list[str],
        answers: list[tuple[str, str]],
        agent_answers: list[dict],
    ) -> str:
        """Break a tie among multiple answers."""
        if self.tie_break == TieBreakStrategy.FIRST:
            # Return first occurrence in original order
            for entry in agent_answers:
                if entry["normalized"] in tied_normalized:
                    return entry["normalized"]
            return tied_normalized[0]

        elif self.tie_break == TieBreakStrategy.RANDOM:
            import random
            return random.choice(tied_normalized)

        elif self.tie_break == TieBreakStrategy.LONGEST:
            # Select answer with longest original text
            best_norm = tied_normalized[0]
            best_len = 0
            for norm in tied_normalized:
                for entry in agent_answers:
                    if entry["normalized"] == norm:
                        if len(entry["answer"]) > best_len:
                            best_len = len(entry["answer"])
                            best_norm = norm
                        break
            return best_norm

        elif self.tie_break == TieBreakStrategy.SHORTEST:
            # Select answer with shortest original text
            best_norm = tied_normalized[0]
            best_len = float('inf')
            for norm in tied_normalized:
                for entry in agent_answers:
                    if entry["normalized"] == norm:
                        if len(entry["answer"]) < best_len:
                            best_len = len(entry["answer"])
                            best_norm = norm
                        break
            return best_norm

        elif self.tie_break == TieBreakStrategy.LLM:
            # LLM tie-breaking handled separately in async context
            # For now, fall back to first
            return tied_normalized[0]

        return tied_normalized[0]

    async def _perform_voting(self, answers: list[tuple[str, str]]) -> VoteResult:
        """Perform voting using the configured strategy."""
        if not answers:
            return VoteResult(
                winning_answer="",
                winner_agent="",
                vote_count=0,
                total_votes=0,
                confidence=0.0,
                all_answers=[],
                voting_strategy=self.voting_strategy.value,
            )

        if self.voting_strategy == VotingStrategy.EXACT:
            return self._exact_vote(answers)
        elif self.voting_strategy == VotingStrategy.SEMANTIC:
            return await self._semantic_vote(answers)
        elif self.voting_strategy == VotingStrategy.LLM:
            return await self._llm_vote(answers)
        else:
            return self._exact_vote(answers)

    async def execute(
        self,
        initial_input: str,
        agents: list,
    ) -> ConsensusResult:
        """
        Execute all agents in parallel on the same input and vote on results.
        
        Args:
            initial_input: The task/question for all agents
            agents: List of agent specifications (names, configs, or dicts)
        
        Returns:
            ConsensusResult with voting outcome
        """
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._results = []
        self._agents = []

        try:
            # Parse all agent configurations
            configs = [self._parse_agent_config(spec) for spec in agents]

            logger.info(
                f"MajorityVoting {self.workflow_id}: "
                f"Starting {len(configs)} agents with strategy={self.voting_strategy.value}"
            )

            # Create all agents
            for idx, config in enumerate(configs):
                agent = await self._create_agent(config, idx + 1)
                self._agents.append(agent)

            # Build execution tasks with semaphore
            semaphore = asyncio.Semaphore(self.max_concurrency)

            async def execute_with_semaphore(agent, config, idx):
                async with semaphore:
                    logger.info(
                        f"MajorityVoting {self.workflow_id}: "
                        f"Starting agent {idx + 1}/{len(configs)} ({config.name or agent.agent_name})"
                    )
                    # All agents get the SAME input (key difference from concurrent workflow)
                    input_msg = initial_input
                    if config.prompt:
                        input_msg = f"{config.prompt}\n\n---\nTask:\n{initial_input}"
                    return await self._execute_agent(agent, input_msg, config.timeout)

            # Execute all agents in parallel
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
                return ConsensusResult(
                    workflow_id=self.workflow_id,
                    status=WorkflowStatus.TIMEOUT,
                    vote_result=None,
                    step_results=self._results,
                    total_duration_seconds=(datetime.now(timezone.utc) - self._start_time).total_seconds(),
                    start_time=self._start_time,
                    end_time=datetime.now(timezone.utc),
                    metadata={"error": f"Workflow exceeded timeout of {self.timeout}s"},
                )

            # Process results
            for result in raw_results:
                if isinstance(result, Exception):
                    self._results.append(WorkflowStepResult(
                        agent_name="unknown",
                        agent_number=0,
                        success=False,
                        output="",
                        error=f"{type(result).__name__}: {str(result)}",
                    ))
                elif isinstance(result, WorkflowStepResult):
                    self._results.append(result)

            # Collect successful answers for voting
            answers = [
                (r.agent_name, r.output)
                for r in self._results
                if r.success and r.output
            ]

            # Perform voting
            vote_result = await self._perform_voting(answers)

            # Determine overall status
            successful_count = len([r for r in self._results if r.success])
            if successful_count == 0:
                status = WorkflowStatus.FAILED
            else:
                status = WorkflowStatus.COMPLETED

            self._end_time = datetime.now(timezone.utc)
            total_duration = (self._end_time - self._start_time).total_seconds()

            return ConsensusResult(
                workflow_id=self.workflow_id,
                status=status,
                vote_result=vote_result,
                step_results=self._results,
                total_duration_seconds=total_duration,
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={
                    "total_agents": len(agents),
                    "successful_agents": successful_count,
                    "failed_agents": len(self._results) - successful_count,
                    "voting_strategy": self.voting_strategy.value,
                    "tie_break": self.tie_break.value,
                    "similarity_threshold": self.similarity_threshold,
                },
            )

        except Exception as e:
            logger.exception(f"MajorityVoting {self.workflow_id} failed")
            self._end_time = datetime.now(timezone.utc)
            return ConsensusResult(
                workflow_id=self.workflow_id,
                status=WorkflowStatus.FAILED,
                vote_result=None,
                step_results=self._results,
                total_duration_seconds=(self._end_time - self._start_time).total_seconds(),
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={"error": str(e)},
            )


class swarm_vote(Tool):
    """Tool for executing majority voting consensus among multiple agents."""

    async def execute(
        self,
        agents="",
        task="",
        workflow_id="",
        timeout="600",
        agent_timeout="300",
        voting_strategy="exact",
        tie_break="first",
        similarity_threshold="0.85",
        max_concurrency="10",
        **kwargs,
    ):
        """
        Execute majority voting consensus.

        Args:
            agents: Comma-separated agent names or JSON array of agent configs
            task: The task/question for all agents to solve
            workflow_id: Optional workflow identifier
            timeout: Total workflow timeout in seconds
            agent_timeout: Per-agent timeout in seconds
            voting_strategy: One of "exact", "semantic", "llm"
            tie_break: One of "first", "random", "llm", "longest", "shortest"
            similarity_threshold: Threshold for semantic similarity (0.0-1.0)
            max_concurrency: Maximum concurrent agent executions
        """
        import json

        try:
            # Parse agents
            agent_list = self._parse_agents_param(agents)
            if not agent_list:
                return Response(
                    message="Error: No agents specified for voting",
                    break_loop=False,
                )

            if len(agent_list) < 2:
                return Response(
                    message="Error: At least 2 agents required for voting",
                    break_loop=False,
                )

            # Validate voting strategy
            valid_strategies = ["exact", "semantic", "llm"]
            voting_strategy = voting_strategy.lower().strip()
            if voting_strategy not in valid_strategies:
                return Response(
                    message=f"Error: Invalid voting strategy. Must be one of: {', '.join(valid_strategies)}",
                    break_loop=False,
                )

            # Validate tie break
            valid_tie_breaks = ["first", "random", "llm", "longest", "shortest"]
            tie_break = tie_break.lower().strip()
            if tie_break not in valid_tie_breaks:
                return Response(
                    message=f"Error: Invalid tie break strategy. Must be one of: {', '.join(valid_tie_breaks)}",
                    break_loop=False,
                )

            # Parse numeric values
            try:
                timeout_val = float(timeout)
                agent_timeout_val = float(agent_timeout)
                similarity_threshold_val = float(similarity_threshold)
                max_concurrency_val = int(max_concurrency)
            except ValueError:
                return Response(
                    message="Error: Invalid numeric parameters",
                    break_loop=False,
                )

            # Create voting workflow
            workflow = MajorityVoting(
                parent_agent=self.agent,
                workflow_id=workflow_id,
                timeout=timeout_val,
                agent_timeout=agent_timeout_val,
                voting_strategy=voting_strategy,
                tie_break=tie_break,
                similarity_threshold=similarity_threshold_val,
                max_concurrency=max_concurrency_val,
            )

            # Execute
            task_msg = task or self.message or "Solve this problem."
            result = await workflow.execute(initial_input=task_msg, agents=agent_list)

            # Format response
            response_text = self._format_result(result)
            return Response(
                message=response_text,
                break_loop=False,
                additional={
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "voting_strategy": voting_strategy,
                    "winner": result.vote_result.winner_agent if result.vote_result else None,
                    "confidence": result.vote_result.confidence if result.vote_result else 0,
                },
            )

        except Exception as e:
            logger.exception("Majority voting execution failed")
            return Response(
                message=f"Voting failed: {type(e).__name__}: {str(e)}",
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

    def _format_result(self, result: ConsensusResult) -> str:
        """Format the consensus result for display."""
        lines = [
            f"# Majority Voting Consensus: {result.workflow_id}",
            f"**Status**: {result.status.value.upper()}",
            f"**Duration**: {result.total_duration_seconds:.2f}s",
            f"**Strategy**: {result.metadata.get('voting_strategy', 'exact')}",
            "",
        ]

        vote = result.vote_result
        if vote:
            lines.append("## Voting Result")
            lines.append("")
            lines.append(f"**Winner**: {vote.winner_agent}")
            lines.append(f"**Vote Count**: {vote.vote_count}/{vote.total_votes}")
            lines.append(f"**Confidence**: {vote.confidence:.1%}")
            if vote.tie_broken:
                lines.append(f"**Tie Broken**: Yes (method: {vote.tie_break_method})")
            lines.append("")

        # Agent results
        lines.append("## Agent Responses")
        lines.append("")
        successful = [s for s in result.step_results if s.success]
        failed = [s for s in result.step_results if not s.success]

        for i, step in enumerate(result.step_results, 1):
            status_icon = "OK" if step.success else "FAIL"
            lines.append(f"### Agent {i}: {step.agent_name} [{status_icon}]")
            lines.append(f"**Duration**: {step.duration_seconds:.2f}s")
            if step.error:
                lines.append(f"**Error**: {step.error}")
            lines.append("")

        # Winning answer
        if vote:
            lines.append("---")
            lines.append("")
            lines.append("## Winning Answer")
            lines.append(vote.winning_answer)

        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://balance-scale {self.agent.agent_name}: Executing Majority Voting",
            content="",
            kvps=self.args,
        )




# =============================================================================
# MIXTURE OF AGENTS (MoA) IMPLEMENTATION
# =============================================================================

@dataclass
class MoARoundResult:
    """Result from a single round of MoA proposals."""
    round_number: int
    proposals: list[dict[str, Any]]  # [{"agent": name, "proposal": output}]
    successful_proposers: int
    failed_proposers: int
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "round_number": self.round_number,
            "proposals": self.proposals,
            "successful_proposers": self.successful_proposers,
            "failed_proposers": self.failed_proposers,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class MoAResult:
    """Complete result from a Mixture of Agents workflow."""
    workflow_id: str
    status: WorkflowStatus
    final_answer: str
    aggregator_agent: str
    rounds: list[MoARoundResult]
    total_proposals: int
    total_duration_seconds: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "final_answer": self.final_answer,
            "aggregator_agent": self.aggregator_agent,
            "rounds": [r.to_dict() for r in self.rounds],
            "total_proposals": self.total_proposals,
            "total_duration_seconds": self.total_duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
        }


class MixtureOfAgents:
    """
    Implements the Mixture of Agents (MoA) consensus pattern.

    Flow:
    1. Multiple proposer agents generate diverse solutions in parallel
    2. Proposers see all proposals from previous rounds and can refine
    3. Aggregator agent synthesizes the best final answer

    This pattern leverages diversity of thought by having multiple independent
    agents propose solutions, then aggregating their collective wisdom.
    """

    def __init__(
        self,
        parent_agent: Agent,
        workflow_id: str = "",
        timeout: float = 900.0,
        agent_timeout: float = 300.0,
        rounds: int = 2,
        max_concurrency: int = 10,
    ):
        self.workflow_id = workflow_id or f"moa_{uuid.uuid4().hex[:8]}"
        self.parent_agent = parent_agent
        self.timeout = timeout
        self.agent_timeout = agent_timeout
        self.rounds = max(1, rounds)
        self.max_concurrency = max_concurrency
        self._status = WorkflowStatus.PENDING
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._round_results: list[MoARoundResult] = []

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

    async def _execute_proposer(
        self,
        agent: Agent,
        config: AgentConfig,
        task: str,
        previous_proposals: list[dict],
    ) -> dict[str, Any]:
        """Execute a single proposer agent and return its proposal."""
        step_start = datetime.now(timezone.utc)

        try:
            # Build input message
            if previous_proposals:
                # Include previous proposals for refinement
                proposals_text = "\n\n".join([
                    f"--- PROPOSAL from {p['agent']} ---\n{p['proposal']}"
                    for p in previous_proposals
                ])
                input_msg = f"""{config.prompt if config.prompt else ''}

TASK: {task}

=== PREVIOUS ROUND PROPOSALS ===
{proposals_text}

=== YOUR TASK ===
Review the proposals above and provide your refined solution.
You may incorporate good ideas from others, improve upon them, or propose a completely different approach.
Provide your best solution:"""
            else:
                # First round - no previous proposals
                input_msg = task
                if config.prompt:
                    input_msg = f"{config.prompt}\n\n{task}"

            agent.hist_add_user_message(UserMessage(message=input_msg, attachments=[]))

            async def run_agent():
                return await agent.monologue()

            try:
                result = await asyncio.wait_for(run_agent(), timeout=config.timeout)
            except asyncio.TimeoutError:
                raise WorkflowTimeoutError(
                    f"Proposer {agent.agent_name} exceeded timeout of {config.timeout}s"
                )

            agent.history.new_topic()
            step_end = datetime.now(timezone.utc)

            return {
                "agent": agent.agent_name,
                "proposal": result,
                "success": True,
                "error": None,
                "duration_seconds": (step_end - step_start).total_seconds(),
            }

        except Exception as e:
            step_end = datetime.now(timezone.utc)
            logger.exception(f"Error in proposer {agent.agent_name}")
            return {
                "agent": agent.agent_name,
                "proposal": "",
                "success": False,
                "error": f"{type(e).__name__}: {str(e)}",
                "duration_seconds": (step_end - step_start).total_seconds(),
            }

    async def _execute_aggregator(
        self,
        agent: Agent,
        config: AgentConfig,
        task: str,
        all_proposals: list[dict],
    ) -> str:
        """Execute the aggregator agent to synthesize final answer."""
        try:
            # Build synthesis prompt with all proposals
            proposals_text = "\n\n".join([
                f"--- PROPOSAL from {p['agent']} ---\n{p['proposal']}"
                for p in all_proposals if p.get('success') and p.get('proposal')
            ])

            input_msg = f"""{config.prompt if config.prompt else ''}

ORIGINAL TASK: {task}

=== ALL PROPOSALS FROM EXPERT AGENTS ===
{proposals_text}

=== YOUR TASK ===
You are the aggregator. Synthesize the best final answer from all proposals above.

Guidelines:
1. Identify the best ideas from each proposal
2. Combine complementary insights
3. Resolve any contradictions using your judgment
4. Provide a comprehensive, coherent final answer
5. Credit specific agents whose ideas you incorporate

Provide your synthesized final answer:"""

            agent.hist_add_user_message(UserMessage(message=input_msg, attachments=[]))

            async def run_agent():
                return await agent.monologue()

            result = await asyncio.wait_for(run_agent(), timeout=config.timeout)
            agent.history.new_topic()
            return result

        except asyncio.TimeoutError:
            raise WorkflowTimeoutError(
                f"Aggregator {agent.agent_name} exceeded timeout of {config.timeout}s"
            )
        except Exception as e:
            logger.exception(f"Error in aggregator {agent.agent_name}")
            raise

    async def execute(
        self,
        task: str,
        proposers: list,
        aggregator: Union[str, AgentConfig, dict],
    ) -> MoAResult:
        """
        Execute the Mixture of Agents workflow.

        Args:
            task: The task/question for all agents
            proposers: List of proposer agent specifications
            aggregator: The aggregator agent specification

        Returns:
            MoAResult with final synthesized answer
        """
        self._status = WorkflowStatus.RUNNING
        self._start_time = datetime.now(timezone.utc)
        self._round_results = []

        try:
            # Parse configurations
            proposer_configs = [self._parse_agent_config(p) for p in proposers]
            aggregator_config = self._parse_agent_config(aggregator)

            if not proposer_configs:
                raise ValueError("At least one proposer agent required")

            logger.info(
                f"MixtureOfAgents {self.workflow_id}: "
                f"Starting with {len(proposer_configs)} proposers, {self.rounds} rounds"
            )

            all_proposals = []  # Collect all proposals across rounds

            # Execute refinement rounds
            for round_num in range(1, self.rounds + 1):
                round_start = datetime.now(timezone.utc)
                logger.info(f"MoA {self.workflow_id}: Starting round {round_num}/{self.rounds}")

                # Create fresh agents for this round
                round_agents = []
                for idx, config in enumerate(proposer_configs):
                    agent = await self._create_agent(config, idx + 1)
                    round_agents.append((agent, config))

                # Get previous proposals for refinement (empty for round 1)
                previous_proposals = [
                    p for p in all_proposals
                    if p.get('success') and p.get('proposal')
                ]

                # Execute all proposers in parallel
                semaphore = asyncio.Semaphore(self.max_concurrency)

                async def execute_proposer_with_semaphore(agent, config):
                    async with semaphore:
                        return await self._execute_proposer(
                            agent, config, task, previous_proposals
                        )

                async def run_round():
                    tasks = [
                        execute_proposer_with_semaphore(agent, config)
                        for agent, config in round_agents
                    ]
                    return await asyncio.gather(*tasks, return_exceptions=True)

                # Run round with timeout
                try:
                    round_results = await asyncio.wait_for(
                        run_round(),
                        timeout=self.timeout / self.rounds
                    )
                except asyncio.TimeoutError:
                    self._status = WorkflowStatus.TIMEOUT
                    return MoAResult(
                        workflow_id=self.workflow_id,
                        status=WorkflowStatus.TIMEOUT,
                        final_answer="",
                        aggregator_agent="",
                        rounds=self._round_results,
                        total_proposals=len(all_proposals),
                        total_duration_seconds=(datetime.now(timezone.utc) - self._start_time).total_seconds(),
                        start_time=self._start_time,
                        end_time=datetime.now(timezone.utc),
                        metadata={"error": f"Round {round_num} exceeded timeout"},
                    )

                # Process round results
                proposals = []
                successful = 0
                failed = 0

                for result in round_results:
                    if isinstance(result, Exception):
                        proposals.append({
                            "agent": "unknown",
                            "proposal": "",
                            "success": False,
                            "error": f"{type(result).__name__}: {str(result)}",
                        })
                        failed += 1
                    elif isinstance(result, dict):
                        proposals.append(result)
                        if result.get('success'):
                            successful += 1
                        else:
                            failed += 1

                all_proposals.extend(proposals)

                round_end = datetime.now(timezone.utc)
                round_result = MoARoundResult(
                    round_number=round_num,
                    proposals=proposals,
                    successful_proposers=successful,
                    failed_proposers=failed,
                    duration_seconds=(round_end - round_start).total_seconds(),
                )
                self._round_results.append(round_result)

                logger.info(
                    f"MoA {self.workflow_id}: Round {round_num} completed - "
                    f"{successful} successful, {failed} failed"
                )

            # Execute aggregator to synthesize final answer
            logger.info(f"MoA {self.workflow_id}: Executing aggregator")

            aggregator_agent = await self._create_agent(aggregator_config, len(proposer_configs) + 1)

            try:
                final_answer = await self._execute_aggregator(
                    aggregator_agent,
                    aggregator_config,
                    task,
                    all_proposals,
                )
            except Exception as e:
                self._status = WorkflowStatus.FAILED
                return MoAResult(
                    workflow_id=self.workflow_id,
                    status=WorkflowStatus.FAILED,
                    final_answer="",
                    aggregator_agent=aggregator_config.name or aggregator_agent.agent_name,
                    rounds=self._round_results,
                    total_proposals=len(all_proposals),
                    total_duration_seconds=(datetime.now(timezone.utc) - self._start_time).total_seconds(),
                    start_time=self._start_time,
                    end_time=datetime.now(timezone.utc),
                    metadata={"error": f"Aggregator failed: {str(e)}"},
                )

            self._status = WorkflowStatus.COMPLETED
            self._end_time = datetime.now(timezone.utc)
            total_duration = (self._end_time - self._start_time).total_seconds()

            return MoAResult(
                workflow_id=self.workflow_id,
                status=WorkflowStatus.COMPLETED,
                final_answer=final_answer,
                aggregator_agent=aggregator_config.name or aggregator_agent.agent_name,
                rounds=self._round_results,
                total_proposals=len(all_proposals),
                total_duration_seconds=total_duration,
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={
                    "num_proposers": len(proposer_configs),
                    "num_rounds": self.rounds,
                    "total_proposals": len(all_proposals),
                    "successful_proposals": len([p for p in all_proposals if p.get('success')]),
                },
            )

        except Exception as e:
            logger.exception(f"MixtureOfAgents {self.workflow_id} failed")
            self._end_time = datetime.now(timezone.utc)
            return MoAResult(
                workflow_id=self.workflow_id,
                status=WorkflowStatus.FAILED,
                final_answer="",
                aggregator_agent="",
                rounds=self._round_results,
                total_proposals=0,
                total_duration_seconds=(self._end_time - self._start_time).total_seconds(),
                start_time=self._start_time,
                end_time=self._end_time,
                metadata={"error": str(e)},
            )


class swarm_moa(Tool):
    """Tool for executing Mixture of Agents consensus pattern."""

    async def execute(
        self,
        task="",
        proposers="",
        aggregator="",
        rounds="2",
        workflow_id="",
        timeout="900",
        agent_timeout="300",
        max_concurrency="10",
        **kwargs,
    ):
        """
        Execute Mixture of Agents consensus.

        Args:
            task: The task/question for all agents to solve
            proposers: Comma-separated agent names or JSON array of proposer configs
            aggregator: Agent name or JSON config for aggregator agent
            rounds: Number of refinement rounds (default 2)
            workflow_id: Optional workflow identifier
            timeout: Total workflow timeout in seconds
            agent_timeout: Per-agent timeout in seconds
            max_concurrency: Maximum concurrent agent executions
        """
        import json

        try:
            # Parse proposers
            proposer_list = self._parse_agents_param(proposers)
            if not proposer_list:
                return Response(
                    message="Error: No proposer agents specified",
                    break_loop=False,
                )

            if len(proposer_list) < 1:
                return Response(
                    message="Error: At least 1 proposer agent required",
                    break_loop=False,
                )

            # Parse aggregator
            aggregator_config = self._parse_single_agent(aggregator)
            if not aggregator_config:
                return Response(
                    message="Error: No aggregator agent specified",
                    break_loop=False,
                )

            # Parse numeric values
            try:
                rounds_val = int(rounds)
                timeout_val = float(timeout)
                agent_timeout_val = float(agent_timeout)
                max_concurrency_val = int(max_concurrency)
            except ValueError:
                return Response(
                    message="Error: Invalid numeric parameters",
                    break_loop=False,
                )

            # Create MoA workflow
            workflow = MixtureOfAgents(
                parent_agent=self.agent,
                workflow_id=workflow_id,
                timeout=timeout_val,
                agent_timeout=agent_timeout_val,
                rounds=rounds_val,
                max_concurrency=max_concurrency_val,
            )

            # Execute
            task_msg = task or self.message or "Solve this problem."
            result = await workflow.execute(
                task=task_msg,
                proposers=proposer_list,
                aggregator=aggregator_config,
            )

            # Format response
            response_text = self._format_result(result)
            return Response(
                message=response_text,
                break_loop=False,
                additional={
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "rounds": len(result.rounds),
                    "total_proposals": result.total_proposals,
                },
            )

        except Exception as e:
            logger.exception("Mixture of Agents execution failed")
            return Response(
                message=f"MoA failed: {type(e).__name__}: {str(e)}",
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

    def _parse_single_agent(self, agent: str) -> Union[str, dict, None]:
        """Parse single agent specification."""
        import json
        if not agent:
            return None
        agent = agent.strip()
        if agent.startswith("{"):
            try:
                return json.loads(agent)
            except json.JSONDecodeError:
                pass
        return agent

    def _format_result(self, result: MoAResult) -> str:
        """Format the MoA result for display."""
        lines = [
            f"# Mixture of Agents: {result.workflow_id}",
            f"**Status**: {result.status.value.upper()}",
            f"**Duration**: {result.total_duration_seconds:.2f}s",
            f"**Total Proposals**: {result.total_proposals}",
            f"**Aggregator**: {result.aggregator_agent}",
            "",
        ]

        # Round summaries
        lines.append("## Rounds")
        lines.append("")
        for round_result in result.rounds:
            lines.append(f"### Round {round_result.round_number}")
            lines.append(f"- **Duration**: {round_result.duration_seconds:.2f}s")
            lines.append(f"- **Successful Proposers**: {round_result.successful_proposers}/{round_result.successful_proposers + round_result.failed_proposers}")

            # List proposals from this round
            for prop in round_result.proposals:
                status = "OK" if prop.get('success') else "FAIL"
                lines.append(f"  - {prop['agent']} [{status}]")
            lines.append("")

        # Final answer
        if result.final_answer:
            lines.append("---")
            lines.append("")
            lines.append("## Final Synthesized Answer")
            lines.append(result.final_answer)

        return "\n".join(lines)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://sitemap {self.agent.agent_name}: Executing Mixture of Agents",
            content="",
            kvps=self.args,
        )

# ===== LLM Council Pattern =====

from dataclasses import dataclass
from typing import List

@dataclass
class CouncilMemberPosition:
    member: str
    position: str
    
@dataclass
class CouncilDeliberation:
    member: str
    response: str
    
@dataclass
class CouncilResult(ConsensusResult):
    introduction: str = ""
    positions: List[CouncilMemberPosition] = None
    deliberation: List[CouncilDeliberation] = None
    decision: str = ""
    
    def __post_init__(self):
        if self.positions is None:
            self.positions = []
        if self.deliberation is None:
            self.deliberation = []


class LLMCouncil(BaseWorkflow):
    """
    A council of specialized agents deliberate on a topic.
    Each member presents their position.
    Members respond to each other's positions.
    A chairperson moderates and issues the final decision.
    """
    
    def __init__(
        self,
        chairperson: AgentConfig,
        members: List[AgentConfig],
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 900,
        member_timeout: int = 300,
        deliberation_rounds: int = 2
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.chairperson = chairperson
        self.members = members
        self.member_timeout = member_timeout
        self.deliberation_rounds = deliberation_rounds
    
    async def execute(self, topic: str) -> CouncilResult:
        """Execute the LLM Council deliberation process."""
        start_time = asyncio.get_event_loop().time()
        result = CouncilResult(
            workflow_id=self.workflow_id,
            workflow_type="llm_council",
            status=WorkflowStatus.RUNNING,
            steps=[],
            introduction="",
            positions=[],
            deliberation=[],
            decision="",
            timing={}
        )        
        try:
            # Phase 1: Chair introduces topic
            chair_agent = await self._create_agent(self.chairperson)
            introduction_prompt = f"Introduce this topic for council deliberation: {topic}"
            
            intro_start = asyncio.get_event_loop().time()
            introduction = await asyncio.wait_for(
                chair_agent.run(introduction_prompt),
                timeout=self.member_timeout
            )
            intro_duration = asyncio.get_event_loop().time() - intro_start
            
            result.introduction = introduction
            result.steps.append(WorkflowStepResult(
                agent_name=self.chairperson.name,
                agent_number=chair_agent.number,
                success=True,
                output=introduction,
                error=None,
                timing={"duration": intro_duration}
            ))
            
            # Phase 2: Each member presents position
            position_tasks = []
            for member_config in self.members:
                position_tasks.append(self._execute_member_position(member_config, topic))
            
            positions = await asyncio.gather(*position_tasks, return_exceptions=True)
            
            for i, position_result in enumerate(positions):
                if isinstance(position_result, Exception):
                    result.steps.append(WorkflowStepResult(
                        agent_name=self.members[i].name,
                        agent_number=-1,
                        success=False,
                        output="",
                        error=str(position_result),
                        timing={}
                    ))
                else:
                    result.positions.append(CouncilMemberPosition(
                        member=self.members[i].name,
                        position=position_result.output
                    ))
                    result.steps.append(position_result)
            
            # Phase 3: Deliberation (members respond to each other)
            for round_num in range(self.deliberation_rounds):
                round_deliberation = []
                deliberation_tasks = []
                
                for i, member_config in enumerate(self.members):
                    # Other positions for this member to respond to
                    other_positions = [p for j, p in enumerate(result.positions) if j != i]
                    deliberation_tasks.append(
                        self._execute_member_deliberation(
                            member_config, topic, other_positions, round_num + 1
                        )
                    )
                
                deliberations = await asyncio.gather(*deliberation_tasks, return_exceptions=True)
                
                for i, delib_result in enumerate(deliberations):
                    if isinstance(delib_result, Exception):
                        result.steps.append(WorkflowStepResult(
                            agent_name=self.members[i].name,
                            agent_number=-1,
                            success=False,
                            output="",
                            error=str(delib_result),
                            timing={}
                        ))
                    else:
                        result.deliberation.append(CouncilDeliberation(
                            member=self.members[i].name,
                            response=delib_result.output
                        ))
                        result.steps.append(delib_result)
            
            # Phase 4: Chair calls for vote and decides
            decision_prompt = (
                f"Based on council deliberation:\n"
                f"Introduction: {introduction}\n\n"
                f"Positions: {result.positions}\n\n"
                f"Deliberation: {result.deliberation}\n\n"
                f"Issue the final council decision on: {topic}"
            )
            
            decision_start = asyncio.get_event_loop().time()
            decision = await asyncio.wait_for(
                chair_agent.run(decision_prompt),
                timeout=self.member_timeout
            )
            decision_duration = asyncio.get_event_loop().time() - decision_start
            
            result.decision = decision
            result.steps.append(WorkflowStepResult(
                agent_name=self.chairperson.name,
                agent_number=chair_agent.number,
                success=True,
                output=decision,
                error=None,
                timing={"duration": decision_duration}
            ))
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            result.final_output = decision
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"Council workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result
    
    async def _execute_member_position(self, member_config: AgentConfig, topic: str) -> WorkflowStepResult:
        """Execute a single council member's position presentation."""
        start_time = asyncio.get_event_loop().time()
        try:
            member_agent = await self._create_agent(member_config)
            prompt = f"Council Topic: {topic}\n\nPresent your position and reasoning:"
            
            output = await asyncio.wait_for(
                member_agent.run(prompt),
                timeout=self.member_timeout
            )
            
            return WorkflowStepResult(
                agent_name=member_config.name,
                agent_number=member_agent.number,
                success=True,
                output=output,
                error=None,
                timing={"duration": asyncio.get_event_loop().time() - start_time}
            )
        except Exception as e:
            return WorkflowStepResult(
                agent_name=member_config.name,
                agent_number=-1,
                success=False,
                output="",
                error=str(e),
                timing={"duration": asyncio.get_event_loop().time() - start_time}
            )
    
    async def _execute_member_deliberation(
        self, 
        member_config: AgentConfig, 
        topic: str, 
        other_positions: List[CouncilMemberPosition],
        round_num: int
    ) -> WorkflowStepResult:
        """Execute a single council member's deliberation response."""
        start_time = asyncio.get_event_loop().time()
        try:
            member_agent = await self._create_agent(member_config)
            prompt = (
                f"Council Round {round_num} - Respond to other council members' positions:\n"
                f"{other_positions}"
            )
            
            output = await asyncio.wait_for(
                member_agent.run(prompt),
                timeout=self.member_timeout
            )
            
            return WorkflowStepResult(
                agent_name=member_config.name,
                agent_number=member_agent.number,
                success=True,
                output=output,
                error=None,
                timing={"duration": asyncio.get_event_loop().time() - start_time}
            )
        except Exception as e:
            return WorkflowStepResult(
                agent_name=member_config.name,
                agent_number=-1,
                success=False,
                output="",
                error=str(e),
                timing={"duration": asyncio.get_event_loop().time() - start_time}
            )


class swarm_council(Tool):
    """Execute an LLM Council deliberation with specialized agents."""
    
    async def execute(
        self,
        chairperson: str,
        members: str,
        topic: str,
        timeout: str = "900",
        member_timeout: str = "300",
        deliberation_rounds: str = "2",
        **kwargs
    ) -> Response:
        """Execute an LLM Council deliberation."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 900
            member_timeout_int = int(member_timeout) if member_timeout.isdigit() else 300
            rounds_int = int(deliberation_rounds) if deliberation_rounds.isdigit() else 2
            
            # Parse chairperson
            chair_config = self._parse_agent_spec(chairperson)
            
            # Parse members
            member_configs = []
            if isinstance(members, str):
                # Try to parse as JSON array first
                try:
                    members_list = json.loads(members)
                    if not isinstance(members_list, list):
                        raise ValueError()
                except:
                    # Treat as comma-separated string
                    members_list = [m.strip() for m in members.split(",") if m.strip()]
                
                for member_spec in members_list:
                    member_configs.append(self._parse_agent_spec(member_spec))
            
            # Create and execute workflow
            workflow = LLMCouncil(
                chairperson=chair_config,
                members=member_configs,
                parent_agent=self.agent,
                timeout=timeout_int,
                member_timeout=member_timeout_int,
                deliberation_rounds=rounds_int
            )
            
            result = await workflow.execute(topic)
            
            # Format response
            response_parts = [
                f"# 🏛️ LLM Council Decision",
                f"**Topic**: {topic}",
                f"**Status**: {result.status.value}",
                "",
                f"## Introduction",
                f"> {result.introduction}",
                "",
                f"## Member Positions",
            ]
            
            for position in result.positions:
                response_parts.extend([
                    f"### {position.member}",
                    f"> {position.position}",
                    ""
                ])
            
            response_parts.append("## Deliberation")
            for delib in result.deliberation:
                response_parts.extend([
                    f"### {delib.member}",
                    f"> {delib.response}",
                    ""
                ])
            
            response_parts.extend([
                "## Final Decision",
                f"> {result.decision}",
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "llm_council"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing LLM Council: {str(e)}",
                break_loop=False
            )

# ===== Debate with Judge Pattern =====

@dataclass
class DebateRound:
    round_number: int
    a_response: str
    b_response: str
    
@dataclass
class DebateResult(ConsensusResult):
    opening_statements: dict = None
    debate_rounds: List[DebateRound] = None
    verdict: str = ""
    
    def __post_init__(self):
        if self.opening_statements is None:
            self.opening_statements = {}
        if self.debate_rounds is None:
            self.debate_rounds = []


class DebateWithJudge(BaseWorkflow):
    """
    Two agents debate opposing viewpoints.
    A judge agent determines the winner.
    """
    
    def __init__(
        self,
        debater_a: AgentConfig,
        debater_b: AgentConfig,
        judge: AgentConfig,
        parent_agent: "Agent",
        workflow_id: str = None,
        timeout: int = 900,
        debater_timeout: int = 300,
        rounds: int = 3
    ):
        super().__init__(parent_agent, workflow_id, timeout)
        self.debater_a = debater_a
        self.debater_b = debater_b
        self.judge = judge
        self.debater_timeout = debater_timeout
        self.rounds = rounds
    
    async def execute(self, topic: str) -> DebateResult:
        """Execute the debate with judge process."""
        start_time = asyncio.get_event_loop().time()
        result = DebateResult(
            workflow_id=self.workflow_id,
            workflow_type="debate_with_judge",
            status=WorkflowStatus.RUNNING,
            steps=[],
            opening_statements={},
            debate_rounds=[],
            verdict="",
            timing={}
        )
        
        try:
            # Create agents
            agent_a = await self._create_agent(self.debater_a)
            agent_b = await self._create_agent(self.debater_b)
            judge_agent = await self._create_agent(self.judge)
            
            # Opening statements
            opening_prompt_a = f"Present your opening argument FOR: {topic}"
            opening_prompt_b = f"Present your opening argument AGAINST: {topic}"
            
            opening_a_start = asyncio.get_event_loop().time()
            opening_a = await asyncio.wait_for(
                agent_a.run(opening_prompt_a),
                timeout=self.debater_timeout
            )
            opening_a_duration = asyncio.get_event_loop().time() - opening_a_start
            
            opening_b_start = asyncio.get_event_loop().time()
            opening_b = await asyncio.wait_for(
                agent_b.run(opening_prompt_b),
                timeout=self.debater_timeout
            )
            opening_b_duration = asyncio.get_event_loop().time() - opening_b_start
            
            result.opening_statements = {
                "for": opening_a,
                "against": opening_b
            }
            
            result.steps.extend([
                WorkflowStepResult(
                    agent_name=self.debater_a.name,
                    agent_number=agent_a.number,
                    success=True,
                    output=opening_a,
                    error=None,
                    timing={"duration": opening_a_duration}
                ),
                WorkflowStepResult(
                    agent_name=self.debater_b.name,
                    agent_number=agent_b.number,
                    success=True,
                    output=opening_b,
                    error=None,
                    timing={"duration": opening_b_duration}
                )
            ])
            
            # Debate rounds
            prev_a_response = opening_a
            prev_b_response = opening_b
            
            for round_num in range(self.rounds):
                # A responds to B
                a_prompt = (
                    f"Opponent argues: {prev_b_response}\n"
                    f"Rebut and strengthen your position."
                )
                
                a_start = asyncio.get_event_loop().time()
                response_a = await asyncio.wait_for(
                    agent_a.run(a_prompt),
                    timeout=self.debater_timeout
                )
                a_duration = asyncio.get_event_loop().time() - a_start
                
                # B responds to A
                b_prompt = (
                    f"Opponent argues: {response_a}\n"
                    f"Rebut and strengthen your position."
                )
                
                b_start = asyncio.get_event_loop().time()
                response_b = await asyncio.wait_for(
                    agent_b.run(b_prompt),
                    timeout=self.debater_timeout
                )
                b_duration = asyncio.get_event_loop().time() - b_start
                
                # Store round results
                round_result = DebateRound(
                    round_number=round_num + 1,
                    a_response=response_a,
                    b_response=response_b
                )
                result.debate_rounds.append(round_result)
                
                result.steps.extend([
                    WorkflowStepResult(
                        agent_name=self.debater_a.name,
                        agent_number=agent_a.number,
                        success=True,
                        output=response_a,
                        error=None,
                        timing={"duration": a_duration}
                    ),
                    WorkflowStepResult(
                        agent_name=self.debater_b.name,
                        agent_number=agent_b.number,
                        success=True,
                        output=response_b,
                        error=None,
                        timing={"duration": b_duration}
                    )
                ])
                
                # Update previous responses for next round
                prev_a_response = response_a
                prev_b_response = response_b
            
            # Judge renders verdict
            transcript = json.dumps({
                "opening_statements": result.opening_statements,
                "debate_rounds": [{
                    "round": r.round_number,
                    "a": r.a_response,
                    "b": r.b_response
                } for r in result.debate_rounds]
            }, indent=2)
            
            judge_prompt = (
                f"You are the judge. Review this debate and render a verdict.\n\n"
                f"Topic: {topic}\n\n"
                f"Debate transcript:\n{transcript}\n\n"
                f"Provide: 1) Winner (FOR or AGAINST), 2) Reasoning, 3) Key arguments"
            )
            
            judge_start = asyncio.get_event_loop().time()
            verdict = await asyncio.wait_for(
                judge_agent.run(judge_prompt),
                timeout=self.debater_timeout
            )
            judge_duration = asyncio.get_event_loop().time() - judge_start
            
            result.verdict = verdict
            result.steps.append(WorkflowStepResult(
                agent_name=self.judge.name,
                agent_number=judge_agent.number,
                success=True,
                output=verdict,
                error=None,
                timing={"duration": judge_duration}
            ))
            
            # Mark workflow as completed
            result.status = WorkflowStatus.COMPLETED
            result.final_output = verdict
            
        except asyncio.TimeoutError as e:
            result.status = WorkflowStatus.TIMEOUT
            result.error = f"Debate workflow timed out after {self.timeout} seconds"
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        finally:
            result.timing["total_duration"] = asyncio.get_event_loop().time() - start_time
        
        return result


class swarm_debate(Tool):
    """Execute a debate between two agents with a judge."""
    
    async def execute(
        self,
        debater_a: str,
        debater_b: str,
        judge: str,
        topic: str,
        timeout: str = "900",
        debater_timeout: str = "300",
        rounds: str = "3",
        **kwargs
    ) -> Response:
        """Execute a debate with judge."""
        try:
            # Parse inputs
            timeout_int = int(timeout) if timeout.isdigit() else 900
            debater_timeout_int = int(debater_timeout) if debater_timeout.isdigit() else 300
            rounds_int = int(rounds) if rounds.isdigit() else 3
            
            # Parse agent specs
            config_a = self._parse_agent_spec(debater_a)
            config_b = self._parse_agent_spec(debater_b)
            judge_config = self._parse_agent_spec(judge)
            
            # Create and execute workflow
            workflow = DebateWithJudge(
                debater_a=config_a,
                debater_b=config_b,
                judge=judge_config,
                parent_agent=self.agent,
                timeout=timeout_int,
                debater_timeout=debater_timeout_int,
                rounds=rounds_int
            )
            
            result = await workflow.execute(topic)
            
            # Format response
            response_parts = [
                f"# ⚖️ Debate with Judge",
                f"**Topic**: {topic}",
                f"**Status**: {result.status.value}",
                "",
                f"## Opening Statements",
                f"### FOR: {result.opening_statements.get('for', 'N/A')}",
                f"### AGAINST: {result.opening_statements.get('against', 'N/A')}",
                "",
                f"## Debate Rounds",
            ]
            
            for round_obj in result.debate_rounds:
                response_parts.extend([
                    f"### Round {round_obj.round_number}",
                    f"**FOR**: {round_obj.a_response}",
                    f"**AGAINST**: {round_obj.b_response}",
                    ""
                ])
            
            response_parts.extend([
                "## Judge's Verdict",
                f"> {result.verdict}",
                "",
                f"**Execution Time**: {result.timing.get('total_duration', 0):.2f} seconds",
                f"**Steps Executed**: {len(result.steps)}"
            ])
            
            return Response(
                message="\n".join(response_parts),
                break_loop=False,
                additional={
                    "result": result.to_dict(),
                    "type": "debate_with_judge"
                }
            )
            
        except Exception as e:
            return Response(
                message=f"Error executing debate: {str(e)}",
                break_loop=False
            )
