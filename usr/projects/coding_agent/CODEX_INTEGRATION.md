# OpenAI Codex CLI Integration Guide for AgentZero

## Overview
OpenAI Codex CLI is a powerful coding agent that runs locally in your terminal. It can read, modify, and execute code in your workspace. This guide explains how to use Codex CLI as a coding resource within AgentZero.

## Installation Status
✅ **Codex CLI v0.87.0 is installed and ready to use**

Installed via: `npm i -g @openai/codex`

## Authentication Required

⚠️ **Before using Codex CLI, you must authenticate:**

### Option 1: Using OpenAI API Key (Recommended for automation)
```bash
echo "YOUR_OPENAI_API_KEY" | codex login --with-api-key
```

### Option 2: Device Authentication (Interactive)
```bash
codex login --device-auth
```
This will open a browser for ChatGPT account authentication.

### Check Authentication Status
```bash
codex login status
```

## Key Features

### 1. Interactive Mode
Run Codex in an interactive terminal UI:
```bash
codex
```

### 2. Non-Interactive Execution (Best for AgentZero)
Execute specific tasks programmatically:
```bash
codex exec "Create a Python function to calculate fibonacci numbers"
```

### 3. Code Review
Get AI-powered code reviews:
```bash
codex review
```

### 4. Web Search Integration
Enable live web search for up-to-date information:
```bash
codex --search "Find the latest best practices for React hooks"
```

### 5. Image Input Support
Attach screenshots or design specs:
```bash
codex -i screenshot.png "Implement this UI design"
```

### 6. Model Selection
Choose different models:
```bash
codex -m gpt-5-codex "Complex coding task"
```

## Integration Patterns for AgentZero

### Pattern 1: Direct Command Execution
Use AgentZero's `code_execution_tool` to run Codex commands:

```json
{
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "terminal",
        "session": 0,
        "code": "codex exec 'Create a REST API with FastAPI for user management'"
    }
}
```

### Pattern 2: Automated Code Review
Integrate code review into your workflow:

```json
{
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "terminal",
        "session": 0,
        "code": "cd /path/to/project && codex review"
    }
}
```

### Pattern 3: Full Automation Mode
For trusted environments, use full automation:

```bash
codex exec --full-auto "Build a complete CRUD application with tests"
```

### Pattern 4: Sandboxed Execution
For safety, use sandbox modes:

```bash
# Read-only mode
codex exec -s read-only "Analyze this codebase"

# Workspace-write mode (safer)
codex exec -s workspace-write "Refactor this module"

# Full access (use with caution)
codex exec -s danger-full-access "Deploy to production"
```

## Approval Modes

Control when Codex requires human approval:

- `--ask-for-approval untrusted` - Only run trusted commands automatically
- `--ask-for-approval on-failure` - Ask only if command fails
- `--ask-for-approval on-request` - Model decides when to ask
- `--ask-for-approval never` - Never ask (dangerous)

## MCP Server Integration

Codex CLI can run as an MCP (Model Context Protocol) server:

```bash
codex mcp-server
```

This allows other agents to communicate with Codex via standardized protocol.

## Configuration

Codex uses `~/.codex/config.toml` for configuration. Override settings:

```bash
codex -c model="gpt-5" -c sandbox_permissions='["disk-full-read-access"]'
```

## Best Practices for AgentZero Integration

### 1. Use Non-Interactive Mode
Always use `codex exec` for programmatic access:
```bash
codex exec "task description"
```

### 2. Specify Working Directory
```bash
codex -C /a0/usr/projects/coding_agent exec "task"
```

### 3. Enable Web Search for Current Information
```bash
codex --search exec "Find and implement latest security best practices"
```

### 4. Use Appropriate Sandbox Mode
- Development: `--sandbox workspace-write`
- Analysis: `--sandbox read-only`
- Production: Avoid or use external sandboxing

### 5. Leverage Image Inputs
```bash
codex -i design.png exec "Implement this UI"
```

### 6. Chain with Other Tools
Combine Codex with AgentZero's other tools:
1. Use `search_engine` to find requirements
2. Use `codex exec` to implement
3. Use `code_execution_tool` to test
4. Use `codex review` to validate

## Example Workflows

### Workflow 1: Complete Feature Implementation
```bash
# Step 1: Research
codex --search exec "Research best practices for JWT authentication in FastAPI"

# Step 2: Implement
codex -C /a0/usr/projects/coding_agent exec "Implement JWT authentication with refresh tokens"

# Step 3: Review
codex review

# Step 4: Test
codex exec "Write comprehensive tests for the authentication system"
```

### Workflow 2: Code Refactoring
```bash
# Analyze and refactor
codex -s workspace-write exec "Analyze the codebase and refactor for better maintainability"

# Review changes
codex review

# Apply changes
codex apply
```

### Workflow 3: Documentation Generation
```bash
codex exec "Generate comprehensive API documentation with examples"
```

## Troubleshooting

### Issue: Not Authenticated
**Solution:** Run `codex login --with-api-key` or `codex login --device-auth`

### Issue: Command Hangs
**Solution:** Use non-interactive mode with `codex exec` instead of `codex`

### Issue: Permission Denied
**Solution:** Adjust sandbox mode or use `--dangerously-bypass-approvals-and-sandbox` (only in safe environments)

### Issue: Model Not Available
**Solution:** Check your subscription plan at https://developers.openai.com/codex/pricing

## Security Considerations

1. **Never use `--dangerously-bypass-approvals-and-sandbox` in production**
2. **Store API keys securely** - use environment variables or secret management
3. **Use appropriate sandbox modes** for the task at hand
4. **Review generated code** before committing to version control
5. **Limit workspace access** using `--add-dir` for specific directories

## Advanced Features

### Cloud Integration
Browse and apply Codex Cloud tasks:
```bash
codex cloud
```

### Resume Previous Sessions
```bash
codex resume --last
```

### Fork Sessions
```bash
codex fork --last
```

### Custom Prompts
Create reusable prompt templates in `~/.codex/prompts/`

## Resources

- Official Documentation: https://developers.openai.com/codex/cli
- Changelog: https://developers.openai.com/codex/changelog
- GitHub: https://github.com/openai/codex
- Pricing: https://developers.openai.com/codex/pricing

## Next Steps

1. ✅ Install Codex CLI (Completed)
2. ⚠️ Authenticate with OpenAI API key or ChatGPT account
3. 🔧 Test basic functionality: `codex exec "echo 'Hello from Codex'"`
4. 📝 Create custom prompts for common tasks
5. 🔗 Integrate with AgentZero workflows
6. 🚀 Build automated coding pipelines

---

**Status:** Codex CLI is installed and ready. Authentication required before use.
**Version:** 0.87.0
**Installation Date:** 2026-01-18
