# Obsidian Swarm Tool

Parallel processing for Obsidian vault operations using swarm patterns.

## Usage

### Parallel Read (swarm_concurrent)
```json
{
 "thoughts": ["Reading multiple notes in parallel..."],
 "tool_name": "obsidian_swarm",
 "tool_args": {
 "action": "read",
 "paths": "note1.md,note2.md,note3.md"
 }
}
```

### Parallel Write
```json
{
 "thoughts": ["Writing multiple notes in parallel..."],
 "tool_name": "obsidian_swarm",
 "tool_args": {
 "action": "write",
 "notes": "{\"note1.md\": \"Content 1\", \"note2.md\": \"Content 2\"}"
 }
}
```

### Parallel Search
```json
{
 "thoughts": ["Executing parallel searches..."],
 "tool_name": "obsidian_swarm",
 "tool_args": {
 "action": "search",
 "queries": "planning,project,roadmap"
 }
}
```

### Hierarchical Analysis (swarm_hierarchical)
```json
{
 "thoughts": ["Performing deep vault analysis..."],
 "tool_name": "obsidian_swarm",
 "tool_args": {
 "action": "analyze",
 "folder": "Projects"
 }
}
```

### Content Synthesis (swarm_moa)
```json
{
 "thoughts": ["Synthesizing content from multiple notes..."],
 "tool_name": "obsidian_swarm",
 "tool_args": {
 "action": "synthesize",
 "topic": "Product Roadmap",
 "paths": "note1.md,note2.md,note3.md"
 }
}
```

### Star-Coordinated Search
```json
{
 "thoughts": ["Executing coordinated search..."],
 "tool_name": "obsidian_swarm",
 "tool_args": {
 "action": "star_search",
 "query": "meeting notes Q1"
 }
}
```

### Vote Validation
```json
{
 "thoughts": ["Validating note quality..."],
 "tool_name": "obsidian_swarm",
 "tool_args": {
 "action": "validate",
 "paths": "note1.md,note2.md,note3.md"
 }
}
```

## Actions

| Action | Pattern | Description |
|--------|---------|-------------|
| read | concurrent | Read multiple notes in parallel |
| write | concurrent | Write multiple notes in parallel |
| search | concurrent | Execute multiple searches in parallel |
| analyze | hierarchical | Deep vault analysis |
| synthesize | moa | Content synthesis from notes |
| star_search | star | Coordinated search |
| validate | vote | Note quality validation |

## Performance

- **Max Concurrency**: 20 parallel operations
- **Timeout**: 5 minutes for large operations
- **Recommended Batch Size**: 10-50 notes
