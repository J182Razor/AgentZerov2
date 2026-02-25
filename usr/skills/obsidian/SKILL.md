# Obsidian Integration Skill

Native Agent Zero integration for Obsidian knowledge management.

## Overview

This skill provides complete Obsidian vault management with maximum parallel processing using Agent Zero's swarm patterns.

## Features

- **Direct Vault Access** - Read, write, delete notes directly
- **Full-Text Search** - SQLite FTS5-powered fast search
- **Link Graph** - Navigate wiki links and backlinks
- **Metadata Extraction** - Tags, frontmatter, aliases
- **Swarm Patterns** - All 7 patterns for parallel processing
- **Semantic Search** - Integration with fused_memory embeddings

## Configuration

Set vault path via environment variable:
```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/vault"
```

Or use the config tool:
```json
{"tool": "obsidian_config", "action": "set", "vault_path": "/path/to/vault"}
```

## Tools

### obsidian - Main Tool

#### Read Note
```json
{
 "tool": "obsidian",
 "action": "read",
 "path": "folder/note.md"
}
```

#### Write Note
```json
{
 "tool": "obsidian",
 "action": "write",
 "path": "folder/new-note.md",
 "content": "# My Note\n\nContent here",
 "frontmatter": {
 "title": "My Note",
 "tags": ["draft", "important"]
 }
}
```

#### Delete Note
```json
{
 "tool": "obsidian",
 "action": "delete",
 "path": "folder/old-note.md"
}
```

#### List Notes
```json
{
 "tool": "obsidian",
 "action": "list",
 "folder": "Daily"
}
```

#### Search Notes
```json
{
 "tool": "obsidian",
 "action": "search",
 "query": "project planning",
 "max_results": 20
}
```

#### Get Graph
```json
{
 "tool": "obsidian",
 "action": "graph"
}
```

#### Get Tags
```json
{
 "tool": "obsidian",
 "action": "tags"
}
```

### obsidian_swarm - Parallel Operations

#### Parallel Read (swarm_concurrent)
```json
{
 "tool": "obsidian_swarm",
 "action": "read",
 "paths": "note1.md,note2.md,note3.md"
}
```

#### Parallel Write
```json
{
 "tool": "obsidian_swarm",
 "action": "write",
 "notes": {
 "note1.md": "Content 1",
 "note2.md": "Content 2"
 }
}
```

#### Parallel Search
```json
{
 "tool": "obsidian_swarm",
 "action": "search",
 "queries": "planning,project,roadmap"
}
```

#### Hierarchical Analysis (swarm_hierarchical)
```json
{
 "tool": "obsidian_swarm",
 "action": "analyze",
 "folder": "Projects"
}
```

#### Content Synthesis (swarm_moa)
```json
{
 "tool": "obsidian_swarm",
 "action": "synthesize",
 "topic": "Product Roadmap",
 "paths": "note1.md,note2.md,note3.md"
}
```

#### Star-Coordinated Search
```json
{
 "tool": "obsidian_swarm",
 "action": "star_search",
 "query": "meeting notes Q1"
}
```

#### Vote Validation
```json
{
 "tool": "obsidian_swarm",
 "action": "validate",
 "paths": "note1.md,note2.md,note3.md"
}
```

### obsidian_config - Configuration

#### Status
```json
{"tool": "obsidian_config", "action": "status"}
```

#### Set Vault Path
```json
{"tool": "obsidian_config", "action": "set", "vault_path": "/new/vault/path"}
```

#### Test Connection
```json
{"tool": "obsidian_config", "action": "test"}
```

## Swarm Patterns Reference

| Pattern | Tool Action | Use Case |
|---------|-------------|----------|
| concurrent | swarm read/write/search | Batch operations |
| hierarchical | analyze | Multi-level analysis |
| moa | synthesize | Content synthesis |
| star | star_search | Coordinated search |
| vote | validate | Quality validation |
| sequential | (via tool chain) | Dependent operations |
| graph | (via tool chain) | Complex workflows |

## Procedures

### 1. Quick Note Retrieval
```
1. Use obsidian read for single note
2. Use obsidian_swarm read for multiple notes
```

### 2. Research Across Vault
```
1. Use obsidian search for simple queries
2. Use obsidian_swarm star_search for complex queries
3. Use obsidian_swarm synthesize for summarization
```

### 3. Bulk Note Management
```
1. Use obsidian list to get note paths
2. Use obsidian_swarm write for bulk updates
3. Use obsidian_swarm validate to verify changes
```

### 4. Vault Analysis
```
1. Use obsidian graph for link structure
2. Use obsidian tags for tag distribution
3. Use obsidian_swarm analyze for deep analysis
```

## Integration with Agent Zero

- **Memory**: Notes can be indexed to fused_memory
- **A2A**: Share vault access with other agents
- **Scheduler**: Automate periodic note operations
- **Browser**: Extract web content to notes

## Templates

Located in: `/a0/usr/skills/obsidian/templates/`

- `daily.md` - Daily note template
- `meeting.md` - Meeting note template
- `project.md` - Project note template
