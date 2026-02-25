#!/usr/bin/env python3
"""
Codex CLI Usage Examples for AgentZero

This script demonstrates various ways to use the Codex wrapper
in AgentZero workflows.
"""

import sys
import os
sys.path.insert(0, '/a0/usr/projects/coding_agent')

from codex_wrapper import CodexAgent, codex_exec, codex_review, codex_auth_status
import json


def example_1_simple_execution():
    """Example 1: Simple task execution"""
    print("
=== Example 1: Simple Task Execution ===")

    result = codex_exec(
        prompt="Create a Python function to calculate factorial",
        working_dir="/a0/usr/projects/coding_agent"
    )

    print(json.dumps(result, indent=2))


def example_2_with_web_search():
    """Example 2: Task with web search enabled"""
    print("
=== Example 2: Task with Web Search ===")

    result = codex_exec(
        prompt="Find and implement the latest best practices for FastAPI error handling",
        working_dir="/a0/usr/projects/coding_agent",
        enable_search=True
    )

    print(json.dumps(result, indent=2))


def example_3_object_oriented():
    """Example 3: Using CodexAgent class"""
    print("
=== Example 3: Object-Oriented Usage ===")

    # Create agent with custom settings
    agent = CodexAgent(
        working_dir="/a0/usr/projects/coding_agent",
        model="gpt-5-codex",
        sandbox_mode="workspace-write",
        approval_mode="on-request"
    )

    # Execute task
    result = agent.execute(
        prompt="Create a REST API endpoint for user registration",
        enable_search=False
    )

    print(json.dumps(result, indent=2))


def example_4_code_review():
    """Example 4: Code review"""
    print("
=== Example 4: Code Review ===")

    result = codex_review(working_dir="/a0/usr/projects/coding_agent")

    print(json.dumps(result, indent=2))


def example_5_with_images():
    """Example 5: Task with image input"""
    print("
=== Example 5: Task with Image Input ===")

    agent = CodexAgent(working_dir="/a0/usr/projects/coding_agent")

    result = agent.execute(
        prompt="Implement the UI shown in the design",
        images=["/path/to/design.png"]  # Replace with actual image path
    )

    print(json.dumps(result, indent=2))


def example_6_full_automation():
    """Example 6: Full automation mode"""
    print("
=== Example 6: Full Automation Mode ===")

    agent = CodexAgent(
        working_dir="/a0/usr/projects/coding_agent",
        sandbox_mode="workspace-write"
    )

    result = agent.execute(
        prompt="Refactor the code for better readability",
        full_auto=True
    )

    print(json.dumps(result, indent=2))


def example_7_check_auth():
    """Example 7: Check authentication status"""
    print("
=== Example 7: Check Authentication ===")

    result = codex_auth_status()

    print(json.dumps(result, indent=2))

    if not result.get('authenticated'):
        print("
⚠️  Codex is not authenticated!")
        print("To authenticate, run:")
        print("  echo 'YOUR_API_KEY' | codex login --with-api-key")
        print("  OR")
        print("  codex login --device-auth")


def example_8_agentero_integration():
    """Example 8: Integration pattern for AgentZero tools"""
    print("
=== Example 8: AgentZero Integration Pattern ===")

    # This shows how to use Codex from AgentZero's code_execution_tool
    integration_example = {
        "tool_name": "code_execution_tool",
        "tool_args": {
            "runtime": "python",
            "session": 0,
            "code": """
import sys
sys.path.insert(0, '/a0/usr/projects/coding_agent')
from codex_wrapper import codex_exec
import json

result = codex_exec(
    prompt='Create a function to validate email addresses',
    working_dir='/a0/usr/projects/coding_agent'
)

print(json.dumps(result, indent=2))
"""
        }
    }

    print("AgentZero tool call example:")
    print(json.dumps(integration_example, indent=2))


if __name__ == "__main__":
    print("
" + "="*60)
    print("Codex CLI Usage Examples for AgentZero")
    print("="*60)

    # Run all examples
    example_7_check_auth()  # Check auth first
    example_8_agentero_integration()  # Show integration pattern

    print("
" + "="*60)
    print("
📚 For more examples, see CODEX_INTEGRATION.md")
    print("
⚠️  Note: Most examples require Codex authentication")
    print("Run 'codex login status' to check authentication")
    print("="*60 + "
")
