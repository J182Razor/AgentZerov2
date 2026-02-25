## Swarm Consensus Tools

Multi-agent consensus mechanisms for decision making and answer synthesis. These tools implement voting patterns and mixture-of-agents approaches for improved accuracy and reliability.

---

### swarm_vote

Executes multiple agents in parallel on the same task and determines consensus through various voting strategies. All agents receive identical input and their outputs are compared to determine the winning answer.

#### Arguments:
* agents: str (Required) - Comma-separated agent names or JSON array of agent configs (minimum 2 agents)
* task: str (Required) - The task/question for all agents to solve
* workflow_id: str (Optional) - Custom workflow identifier
* timeout: str (Optional) - Total workflow timeout in seconds (default: "600")
* agent_timeout: str (Optional) - Per-agent timeout in seconds (default: "300")
* voting_strategy: str (Optional) - One of "exact", "semantic", "llm" (default: "exact")
* tie_break: str (Optional) - One of "first", "random", "llm", "longest", "shortest" (default: "first")
* similarity_threshold: str (Optional) - Threshold for semantic similarity 0.0-1.0 (default: "0.85")
* max_concurrency: str (Optional) - Maximum concurrent agent executions (default: "10")

#### Voting Strategies:
- **exact**: Normalizes and compares answers for exact string match. Fast and deterministic.
- **semantic**: Uses embedding similarity to cluster similar answers. Better for varied phrasings.
- **llm**: Uses LLM as judge to select best answer. Highest quality but slower.

#### Tie-Break Strategies:
- **first**: First occurrence in original order wins
- **random**: Random selection among tied answers
- **longest**: Longest response wins
- **shortest**: Shortest response wins
- **llm**: LLM decides among tied candidates

#### Usage:
~~~json
{
 "thoughts": [
 "I need consensus from multiple agents on this critical decision",
 "Using semantic voting to handle varied phrasings"
 ],
 "headline": "Executing majority voting for consensus",
 "tool_name": "swarm_vote",
 "tool_args": {
 "agents": "analyst, researcher, expert",
 "task": "What is the best architecture pattern for this microservices system?",
 "voting_strategy": "semantic",
 "tie_break": "llm"
 }
}
~~~

#### When to use:
- Critical decisions requiring multiple independent opinions
- Fact verification with multiple fact-checkers
- Code review consensus from multiple reviewers
- Important judgments where accuracy matters more than speed
- Reducing hallucination risk through consensus

---

### swarm_moa

Implements the Mixture of Agents (MoA) pattern for sophisticated consensus. Multiple proposer agents generate diverse solutions across multiple refinement rounds, then an aggregator synthesizes the best final answer.

#### Arguments:
* task: str (Required) - The task/question for all agents to solve
* proposers: str (Required) - Comma-separated agent names or JSON array of proposer configs
* aggregator: str (Required) - Agent name or JSON config for aggregator agent
* rounds: str (Optional) - Number of refinement rounds (default: "2")
* workflow_id: str (Optional) - Custom workflow identifier
* timeout: str (Optional) - Total workflow timeout in seconds (default: "900")
* agent_timeout: str (Optional) - Per-agent timeout in seconds (default: "300")
* max_concurrency: str (Optional) - Maximum concurrent agent executions (default: "10")

#### How MoA Works:
1. **Round 1**: Each proposer independently generates an initial solution
2. **Round N**: Proposers see all proposals from previous rounds and refine their answers
3. **Aggregation**: Aggregator agent synthesizes all proposals into final answer

#### Usage:
~~~json
{
 "thoughts": [
 "This complex problem benefits from diverse expert perspectives",
 "Using MoA with 3 rounds of refinement"
 ],
 "headline": "Executing Mixture of Agents for complex synthesis",
 "tool_name": "swarm_moa",
 "tool_args": {
 "task": "Design a comprehensive security architecture for a financial application",
 "proposers": "security_expert, compliance_expert, architect",
 "aggregator": "senior_architect",
 "rounds": "3",
 "timeout": "1200"
 }
}
~~~

#### When to use:
- Complex problems benefiting from diverse expert perspectives
- Research questions requiring synthesis of multiple viewpoints
- Design decisions needing comprehensive analysis
- Creative tasks where multiple approaches can be combined
- High-stakes decisions where quality justifies the overhead
- Problems without a single obvious solution

#### Tips:
- Use 2-3 rounds for most tasks; more rounds provide diminishing returns
- Choose proposers with complementary expertise
- Use a strong aggregator agent that can synthesize effectively
- Allow longer timeouts for complex tasks with multiple rounds
