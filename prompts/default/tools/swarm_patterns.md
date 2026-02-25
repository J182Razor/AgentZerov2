# Swarm Pattern Tools

Advanced multi-agent coordination patterns for complex task orchestration. These tools implement various organizational structures for sophisticated task decomposition and result synthesis.

---

## swarm_router

Route tasks to the most appropriate agent using intelligent routing.

### Description
Route tasks to the most appropriate agent based on task characteristics. Uses an LLM to analyze the task and select the best agent.

### Arguments
* agents (str, required) - Comma-separated list or JSON array of agent specifications
* router (str, required) - Router agent specification
* task (str, required) - The task to route
* timeout (str, optional) - Total workflow timeout in seconds (default: "600")
* agent_timeout (str, optional) - Per-agent timeout in seconds (default: "300")

### Usage
```json
{
 "tool_name": "swarm_router",
 "tool_args": {
 "agents": "developer,researcher,writer",
 "router": "task_master",
 "task": "Implement a new feature for our web application"
 }
}
```

---

## swarm_round_robin

Execute a round-robin workflow where agents take turns contributing.

### Description
Agents take turns in a round-robin fashion to contribute to a task. Each agent gets a chance to respond in sequence for multiple rounds.

### Arguments
* agents (str, required) - Comma-separated list or JSON array of agent specifications
* task (str, required) - The task to work on
* timeout (str, optional) - Total workflow timeout in seconds (default: "600")
* agent_timeout (str, optional) - Per-agent timeout in seconds (default: "300")
* rounds (str, optional) - Number of rounds (default: "3")

### Usage
```json
{
 "tool_name": "swarm_round_robin",
 "tool_args": {
 "agents": "analyst,researcher,writer",
 "task": "Analyze the market opportunity for our product",
 "rounds": "3"
 }
}
```

---

## swarm_group_chat

Execute a group chat conversation among multiple agents.

### Description
Multi-agent conversation where agents can freely exchange messages. Agents decide when to contribute or when the conversation is complete.

### Arguments
* agents (str, required) - Comma-separated list or JSON array of agent specifications
* task (str, required) - The task to discuss
* timeout (str, optional) - Total workflow timeout in seconds (default: "600")
* agent_timeout (str, optional) - Per-agent timeout in seconds (default: "300")
* max_rounds (str, optional) - Maximum number of rounds (default: "10")

### Usage
```json
{
 "tool_name": "swarm_group_chat",
 "tool_args": {
 "agents": "developer,designer,product_manager",
 "task": "Plan the next sprint for our project",
 "max_rounds": "5"
 }
}
```

---

## swarm_forest

Execute a forest swarm workflow with multiple tree structures.

### Description
Tree-structured agent organization with multiple independent trees. Each tree has a root node with child nodes forming a hierarchy.

### Arguments
* trees (str, required) - JSON array of tree definitions
* task (str, required) - The task to work on
* timeout (str, optional) - Total workflow timeout in seconds (default: "900")
* agent_timeout (str, optional) - Per-agent timeout in seconds (default: "300")

### Usage
```json
{
 "tool_name": "swarm_forest",
 "tool_args": {
 "trees": "[{\"root\": {\"agent\": \"manager\", \"children\": [\"worker1\", \"worker2\"]}, \"worker1\": {\"agent\": \"developer\", \"children\": []}, \"worker2\": {\"agent\": \"tester\", \"children\": []}}]",
 "task": "Develop and test a new feature"
 }
}
```

---

## swarm_spreadsheet

Execute a spreadsheet swarm workflow with agents arranged in a grid.

### Description
Agents arranged in a grid/spreadsheet pattern. Each cell contains an agent that processes data. Supports row-wise, column-wise, or parallel execution.

### Arguments
* agents (str, required) - Comma-separated list or JSON array of agent specifications
* task (str, required) - The task to work on
* rows (str, required) - Number of rows in the grid
* cols (str, required) - Number of columns in the grid
* timeout (str, optional) - Total workflow timeout in seconds (default: "900")
* agent_timeout (str, optional) - Per-agent timeout in seconds (default: "300")
* execution_mode (str, optional) - Execution mode: "parallel", "row_by_row", or "column_by_column" (default: "parallel")

### Usage
```json
{
 "tool_name": "swarm_spreadsheet",
 "tool_args": {
 "agents": "analyst1,analyst2,analyst3,analyst4",
 "task": "Analyze different aspects of our financial data",
 "rows": "2",
 "cols": "2",
 "execution_mode": "parallel"
 }
}
```

---

## swarm_auto_builder

Automatically build and execute the best swarm for a given task.

### Description
Automatically selects and configures the best swarm pattern for a given task. Analyzes the task requirements and builds an appropriate swarm configuration.

### Arguments
* builder (str, required) - Builder agent specification
* agent_pool (str, required) - Comma-separated list or JSON array of available agent specifications
* task (str, required) - The task to work on
* timeout (str, optional) - Total workflow timeout in seconds (default: "900")
* agent_timeout (str, optional) - Per-agent timeout in seconds (default: "300")

### Usage
```json
{
 "tool_name": "swarm_auto_builder",
 "tool_args": {
 "builder": "swarm_architect",
 "agent_pool": "developer,researcher,writer,analyst",
 "task": "Create a comprehensive report on our market position"
 }
}
```
