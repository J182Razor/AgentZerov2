## Swarm Pattern Tools

Advanced multi-agent coordination patterns for complex task orchestration. These tools implement hub-and-spoke and tree-structured hierarchical coordination for sophisticated task decomposition and result synthesis.

---

### swarm_star

Hub-and-spoke coordination pattern where a central hub agent decomposes tasks into subtasks for spoke agents, which execute in parallel. The hub then aggregates all results into a final answer.

#### Flow:
1. **Decomposition**: Hub agent breaks down the main task into independent subtasks
2. **Execution**: Spoke agents execute their assigned subtasks in parallel
3. **Aggregation**: Hub agent synthesizes all spoke results into final output

#### Arguments:
* agents: str (Required) - Comma-separated agent names or JSON array of spoke agent configs
* task: str (Required) - The main task to decompose and distribute
* workflow_id: str (Optional) - Custom workflow identifier
* timeout: str (Optional) - Total workflow timeout in seconds (default: "900")
* hub_timeout: str (Optional) - Hub agent timeout for decomposition/aggregation (default: "300")
* spoke_timeout: str (Optional) - Individual spoke agent timeout (default: "300")
* decomposition_prompt: str (Optional) - Custom prompt for task decomposition
* aggregation_prompt: str (Optional) - Custom prompt for result aggregation
* max_concurrency: str (Optional) - Maximum concurrent spoke executions (default: "10")

#### Usage:
~~~json
{
 "thoughts": [
 "This complex task needs decomposition and parallel processing",
 "Using StarSwarm with hub coordinator and specialized spokes"
 ],
 "headline": "Executing StarSwarm hub-and-spoke pattern",
 "tool_name": "swarm_star",
 "tool_args": {
 "agents": "researcher, analyst, fact_checker, writer",
 "task": "Research the impact of AI on healthcare and produce a comprehensive report",
 "timeout": "1200",
 "max_concurrency": "4"
 }
}
~~~

#### When to use:
- Complex tasks that can be decomposed into independent subtasks
- Research and analysis requiring multiple specialized perspectives
- Tasks benefiting from parallel execution with central coordination
- Scenarios where subtasks have clear boundaries but contribute to a unified output
- Report generation with multiple contributors

#### Tips:
- Use 3-6 spoke agents for optimal decomposition granularity
- Each spoke should have a distinct role/specialty
- The hub agent should be good at synthesis and organization
- Allow sufficient timeout for all three phases

---

### swarm_hierarchical

Tree-structured hierarchical coordination pattern with multiple levels of management. Root agent decomposes tasks to managers, managers decompose to workers, workers execute, and results bubble up through aggregation at each level.

#### Structure:
```
Root (1)
├── Manager 1
│   ├── Worker 1.1
│   └── Worker 1.2
├── Manager 2
│   ├── Worker 2.1
│   └── Worker 2.2
└── Manager 3
    ├── Worker 3.1
    └── Worker 3.2
```

#### Flow:
1. **Root Decomposition**: Root agent decomposes task into manager-level assignments
2. **Manager Decomposition**: Each manager decomposes their task into worker tasks
3. **Worker Execution**: All workers execute in parallel across all teams
4. **Manager Aggregation**: Each manager synthesizes their workers' results
5. **Root Aggregation**: Root synthesizes all manager results into final answer

#### Arguments:
* root: str (Optional) - Root agent name/config
* managers: str (Required) - Comma-separated or JSON array of manager agent names/configs
* workers: str (Optional) - JSON object mapping manager name to list of worker names
* task: str (Required) - The main task to process through the hierarchy
* workflow_id: str (Optional) - Custom workflow identifier
* timeout: str (Optional) - Total workflow timeout in seconds (default: "1800")
* root_timeout: str (Optional) - Root agent timeout (default: "300")
* manager_timeout: str (Optional) - Manager agent timeout (default: "300")
* worker_timeout: str (Optional) - Worker agent timeout (default: "300")
* root_decomposition_prompt: str (Optional) - Custom prompt for root decomposition
* manager_decomposition_prompt: str (Optional) - Custom prompt for manager decomposition
* manager_aggregation_prompt: str (Optional) - Custom prompt for manager aggregation
* root_aggregation_prompt: str (Optional) - Custom prompt for root aggregation
* max_concurrency: str (Optional) - Maximum concurrent worker executions (default: "10")

#### Workers Mapping Format:
~~~json
{
 "manager_1": ["worker_1", "worker_2"],
 "manager_2": ["worker_3", "worker_4"]
}
~~~

#### Usage:
~~~json
{
 "thoughts": [
 "This enterprise-scale task requires hierarchical decomposition",
 "Using 3 manager teams with specialized workers each"
 ],
 "headline": "Executing hierarchical swarm pattern",
 "tool_name": "swarm_hierarchical",
 "tool_args": {
 "managers": "frontend_lead, backend_lead, devops_lead",
 "workers": "{\"frontend_lead\": [\"ui_dev\", \"ux_designer\"], \"backend_lead\": [\"api_dev\", \"db_engineer\"], \"devops_lead\": [\"infra_eng\", \"security_eng\"]}",
 "task": "Design and plan implementation of a new e-commerce platform",
 "timeout": "1800"
 }
}
~~~

#### When to use:
- Enterprise-scale tasks requiring multiple levels of coordination
- Projects with distinct domains each needing their own team
- Complex workflows where each component needs sub-decomposition
- Large-scale research with multiple teams investigating different aspects
- Software architecture planning with specialized sub-teams
- Multi-department coordination scenarios

#### Tips:
- Use 2-5 managers for optimal span of control
- Assign 2-4 workers per manager for balanced teams
- Each manager should have domain expertise in their assigned area
- The root agent should excel at high-level organization and synthesis
- Allow generous timeouts (1800s+) for the five-phase execution
- Workers mapping is optional - default workers will be created if not specified
