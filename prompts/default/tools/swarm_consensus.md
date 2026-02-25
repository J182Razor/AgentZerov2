# Swarm Consensus Tools

Multi-agent consensus mechanisms for decision making and answer synthesis. These tools implement voting patterns and mixture-of-agents approaches for improved accuracy and reliability.

---

## swarm_council

Execute an LLM Council deliberation with specialized agents.

### Description
A council of specialized agents deliberate on a topic. Each member presents their position. Members respond to each other's positions. A chairperson moderates and issues the final decision.

### Arguments
* chairperson (str, required) - Chairperson agent specification
* members (str, required) - Comma-separated list or JSON array of council member agent specifications
* topic (str, required) - The topic for council deliberation
* timeout (str, optional) - Total workflow timeout in seconds (default: "900")
* member_timeout (str, optional) - Per-member timeout in seconds (default: "300")
* deliberation_rounds (str, optional) - Number of deliberation rounds (default: "2")

### Usage
```json
{
 "tool_name": "swarm_council",
 "tool_args": {
 "chairperson": "expert",
 "members": "analyst,researcher,critic",
 "topic": "What is the best approach to solve this problem?",
 "deliberation_rounds": "2"
 }
}
```

---

## swarm_debate

Execute a debate between two agents with a judge.

### Description
Two agents debate opposing viewpoints. A judge agent determines the winner.

### Arguments
* debater_a (str, required) - First debater agent specification
* debater_b (str, required) - Second debater agent specification
* judge (str, required) - Judge agent specification
* topic (str, required) - The debate topic
* timeout (str, optional) - Total workflow timeout in seconds (default: "900")
* debater_timeout (str, optional) - Per-debater timeout in seconds (default: "300")
* rounds (str, optional) - Number of debate rounds (default: "3")

### Usage
```json
{
 "tool_name": "swarm_debate",
 "tool_args": {
 "debater_a": "proponent",
 "debater_b": "opponent",
 "judge": "neutral_judge",
 "topic": "Should we implement feature X?",
 "rounds": "3"
 }
}
```
