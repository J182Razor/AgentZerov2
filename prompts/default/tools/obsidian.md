# Obsidian Tool

Native Agent Zero tool for Obsidian vault management.

## Usage

### Read Note
```json
{
 "thoughts": ["I need to read a note from the vault..."],
 "tool_name": "obsidian",
 "tool_args": {
 "action": "read",
 "path": "folder/note.md"
 }
}
```

### Write Note
```json
{
 "thoughts": ["Creating a new note..."],
 "tool_name": "obsidian",
 "tool_args": {
 "action": "write",
 "path": "folder/new-note.md",
 "content": "# Title\n\nContent here",
 "frontmatter": "title: My Note\ntags:\n - draft"
 }
}
```

### Search Notes
```json
{
 "thoughts": ["Searching for relevant notes..."],
 "tool_name": "obsidian",
 "tool_args": {
 "action": "search",
 "query": "project planning",
 "max_results": 20
 }
}
```

### List Notes
```json
{
 "thoughts": ["Listing notes in folder..."],
 "tool_name": "obsidian",
 "tool_args": {
 "action": "list",
 "folder": "Daily"
 }
}
```

### Get Link Graph
```json
{
 "thoughts": ["Building vault link graph..."],
 "tool_name": "obsidian",
 "tool_args": {
 "action": "graph"
 }
}
```

### Get Tags
```json
{
 "thoughts": ["Getting tag frequency..."],
 "tool_name": "obsidian",
 "tool_args": {
 "action": "tags"
 }
}
```

## Actions

| Action | Description | Args |
|--------|-------------|------|
| read | Read a note | path |
| write | Write/create a note | path, content, frontmatter? |
| delete | Delete a note | path |
| list | List notes in folder | folder? |
| search | Search note contents | query, max_results?, regex? |
| graph | Get link graph | - |
| tags | Get tag frequency | - |

## Configuration

Set vault path via environment variable:
```
OBSIDIAN_VAULT_PATH=/path/to/vault
```

Or use obsidian_config tool:
```json
{
 "tool_name": "obsidian_config",
 "tool_args": {
 "action": "set",
 "vault_path": "/path/to/vault"
 }
}
```
