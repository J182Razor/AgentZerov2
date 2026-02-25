#!/usr/bin/env python3
"""
Codex CLI Wrapper for AgentZero

This module provides a Python interface to OpenAI Codex CLI,
making it easy to integrate Codex as a coding subagent in AgentZero.
"""

import subprocess
import json
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile


class CodexAgent:
    """Wrapper class for OpenAI Codex CLI integration."""

    def __init__(self, 
                 working_dir: Optional[str] = None,
                 model: str = "gpt-5-codex",
                 sandbox_mode: str = "workspace-write",
                 approval_mode: str = "on-request"):
        """
        Initialize Codex Agent.

        Args:
            working_dir: Working directory for Codex operations
            model: Model to use (gpt-5-codex, gpt-5, etc.)
            sandbox_mode: Sandbox policy (read-only, workspace-write, danger-full-access)
            approval_mode: Approval policy (untrusted, on-failure, on-request, never)
        """
        self.working_dir = working_dir or os.getcwd()
        self.model = model
        self.sandbox_mode = sandbox_mode
        self.approval_mode = approval_mode

    def _build_command(self, 
                       prompt: str,
                       images: Optional[List[str]] = None,
                       enable_search: bool = False,
                       config_overrides: Optional[Dict[str, str]] = None,
                       full_auto: bool = False) -> List[str]:
        """Build the codex command with all options."""
        cmd = ["codex"]

        # Add working directory
        if self.working_dir:
            cmd.extend(["-C", self.working_dir])

        # Add model
        cmd.extend(["-m", self.model])

        # Add sandbox mode
        cmd.extend(["-s", self.sandbox_mode])

        # Add approval mode
        if not full_auto:
            cmd.extend(["-a", self.approval_mode])
        else:
            cmd.append("--full-auto")

        # Add web search
        if enable_search:
            cmd.append("--search")

        # Add images
        if images:
            for img in images:
                cmd.extend(["-i", img])

        # Add config overrides
        if config_overrides:
            for key, value in config_overrides.items():
                cmd.extend(["-c", f"{key}={value}"])

        # Add exec subcommand and prompt
        cmd.extend(["exec", prompt])

        return cmd

    def execute(self,
                prompt: str,
                images: Optional[List[str]] = None,
                enable_search: bool = False,
                config_overrides: Optional[Dict[str, str]] = None,
                full_auto: bool = False,
                timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a Codex task.

        Args:
            prompt: Task description for Codex
            images: List of image paths to attach
            enable_search: Enable web search
            config_overrides: Configuration overrides
            full_auto: Use full automation mode
            timeout: Command timeout in seconds

        Returns:
            Dict with status, output, and error information
        """
        cmd = self._build_command(
            prompt=prompt,
            images=images,
            enable_search=enable_search,
            config_overrides=config_overrides,
            full_auto=full_auto
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_dir
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timeout",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": " ".join(cmd)
            }

    def review_code(self, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Run code review on the current workspace."""
        cmd = ["codex", "review"]

        if self.working_dir:
            cmd.extend(["-C", self.working_dir])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_dir
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": " ".join(cmd)
            }

    def check_auth_status(self) -> Dict[str, Any]:
        """Check Codex authentication status."""
        try:
            result = subprocess.run(
                ["codex", "login", "status"],
                capture_output=True,
                text=True
            )

            is_authenticated = "logged in" in result.stdout.lower()

            return {
                "authenticated": is_authenticated,
                "status": result.stdout.strip(),
                "command": "codex login status"
            }
        except Exception as e:
            return {
                "authenticated": False,
                "error": str(e),
                "command": "codex login status"
            }

    def authenticate_with_api_key(self, api_key: str) -> Dict[str, Any]:
        """Authenticate Codex with OpenAI API key."""
        try:
            result = subprocess.run(
                ["codex", "login", "--with-api-key"],
                input=api_key,
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Convenience functions for quick access

def codex_exec(prompt: str, 
               working_dir: Optional[str] = None,
               enable_search: bool = False,
               images: Optional[List[str]] = None) -> Dict[str, Any]:
    """Quick execution of Codex task."""
    agent = CodexAgent(working_dir=working_dir)
    return agent.execute(prompt, images=images, enable_search=enable_search)


def codex_review(working_dir: Optional[str] = None) -> Dict[str, Any]:
    """Quick code review."""
    agent = CodexAgent(working_dir=working_dir)
    return agent.review_code()


def codex_auth_status() -> Dict[str, Any]:
    """Check authentication status."""
    agent = CodexAgent()
    return agent.check_auth_status()


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python codex_wrapper.py <command> [args]")
        print("Commands: exec, review, status")
        sys.exit(1)

    command = sys.argv[1]

    if command == "exec":
        if len(sys.argv) < 3:
            print("Usage: python codex_wrapper.py exec <prompt>")
            sys.exit(1)
        prompt = " ".join(sys.argv[2:])
        result = codex_exec(prompt)
        print(json.dumps(result, indent=2))

    elif command == "review":
        result = codex_review()
        print(json.dumps(result, indent=2))

    elif command == "status":
        result = codex_auth_status()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
