## Swarm Workflow Tools

Multi-agent workflow orchestration tools for executing agents in various coordination patterns. These tools enable complex task decomposition, parallel execution, and result aggregation.

---

### swarm_sequential

Executes agents sequentially in a chain, passing output from one agent to the next. Each agent receives the output of the previous agent as input.

#### Arguments:
* agents: str (Required) - Comma-separated agent names or JSON array of agent configs
* initial_input: str (Optional) - Initial input for the first agent (default: current message)
* workflow_id: str (Optional) - Custom workflow identifier
* timeout: str (Optional) - Total workflow timeout in seconds (default: "600")
* step_timeout: str (Optional) - Per-step timeout in seconds (default: "300")
* fail_fast: str (Optional) - Stop on first failure "true"/"false" (default: "true")

#### Usage:
~~~json
{
 "thoughts": [
 "I need to process data through multiple agents in sequence",
 "First agent analyzes, second transforms, third summarizes"
 ],
 "headline": "Executing sequential workflow",
 "tool_name": "swarm_sequential",
 "tool_args": {
 "agents": "analyst, transformer, summarizer",
 "initial_input": "Analyze this dataset and provide insights",
 "timeout": "900",
 "fail_fast": "true"
 }
}
~~~

#### When to use:
- Pipeline processing where each step builds on previous results
- Data transformation chains (extract → transform → load)
- Multi-stage analysis requiring intermediate outputs
- Sequential refinement of outputs

---

### swarm_concurrent

Executes multiple agents in parallel on the same task and aggregates results. Supports multiple aggregation strategies.

#### Arguments:
* agents: str (Required) - Comma-separated agent names or JSON array of agent configs
* initial_input: str (Optional) - Task for all agents (default: current message)
* workflow_id: str (Optional) - Custom workflow identifier
* timeout: str (Optional) - Total workflow timeout in seconds (default: "600")
* agent_timeout: str (Optional) - Per-agent timeout in seconds (default: "300")
* aggregation: str (Optional) - Aggregation strategy: "concat", "best", "vote", "summary" (default: "concat")
* separator: str (Optional) - Separator for concat aggregation (default: "\n\n---\n\n")
* max_concurrency: str (Optional) - Maximum parallel executions (default: "10")

#### Aggregation Strategies:
- **concat**: Concatenate all results with separator
- **best**: Use LLM to select the best result
- **vote**: Majority voting on similar outputs
- **summary**: LLM-generated synthesis of all results

#### Usage:
~~~json
{
 "thoughts": [
 "I need multiple perspectives on this problem",
 "Running analyst, critic, and researcher in parallel"
 ],
 "headline": "Executing concurrent workflow with synthesis",
 "tool_name": "swarm_concurrent",
 "tool_args": {
 "agents": "analyst, critic, researcher",
 "initial_input": "Evaluate this architecture proposal",
 "aggregation": "summary",
 "max_concurrency": "5"
 }
}
~~~

#### When to use:
- Getting diverse perspectives on the same problem
- Parallel processing of independent tasks
- Redundancy for critical decisions (multiple agents verify)
- Speed optimization when tasks don't depend on each other

---

### swarm_graph

Executes agents as a directed graph with conditional branching and parallel paths. Supports complex workflow topologies.

#### Arguments:
* nodes: str (Required) - JSON array of node definitions with id, agent, profile, prompt, timeout
* edges: str (Required) - JSON array of edge definitions with from, to, condition
* entry: str (Required) - ID of the entry node
* initial_input: str (Optional) - Initial input for entry node (default: current message)
* workflow_id: str (Optional) - Custom workflow identifier
* timeout: str (Optional) - Total workflow timeout in seconds (default: "600")
* node_timeout: str (Optional) - Per-node timeout in seconds (default: "300")
* max_iterations: str (Optional) - Maximum graph iterations (default: "100")
* fail_fast: str (Optional) - Stop on first failure "true"/"false" (default: "true")

#### Node Definition:
~~~json
{
 "id": "analyze",
 "agent": "analyst",
 "profile": "developer",
 "prompt": "Analyze the input data",
 "timeout": 300
}
~~~

#### Edge Definition:
~~~json
{
 "from": "analyze",
 "to": "transform",
 "condition": "success == True"
}
~~~

#### Condition Context Variables:
- `output`: Output from the source node
- `success`: Whether the node succeeded
- `error`: Error message if failed
- `node_outputs`: Dict of all completed node outputs
- `iteration`: Current iteration count

#### Usage:
~~~json
{
 "thoughts": [
 "I need a workflow with branching logic",
 "Analyzer feeds to both transformer and validator based on conditions"
 ],
 "headline": "Executing graph workflow with conditional branching",
 "tool_name": "swarm_graph",
 "tool_args": {
 "nodes": "[{\"id\": \"start\", \"agent\": \"analyst\"}, {\"id\": \"process\", \"agent\": \"developer\"}, {\"id\": \"review\", \"agent\": \"reviewer\"}]",
 "edges": "[{\"from\": \"start\", \"to\": \"process\"}, {\"from\": \"process\", \"to\": \"review\"}]",
 "entry": "start",
 "initial_input": "Process this request through the pipeline"
 }
}
~~~

#### When to use:
- Complex workflows with conditional branching
- Multi-path execution based on intermediate results
- DAG (Directed Acyclic Graph) processing patterns
- Fan-out/fan-in patterns with conditions
