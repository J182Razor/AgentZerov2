"""Git Auto-Sync for Agent Zero

Automatically commits and pushes changes to GitHub for version control.
Called periodically and on significant changes.
"""

import os
import subprocess
import datetime
import hashlib
from typing import Optional, List


class GitAutoSync:
    """Automatic git synchronization for version control"""

    def __init__(self, repo_path: str = "/a0", remote: str = "origin", branch: str = "main"):
        self.repo_path = repo_path
        self.remote = remote
        self.branch = branch
        self.last_sync_hash = None

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the repo directory"""
        cmd = ["git"] + list(args)
        return subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False
        )

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes"""
        result = self._run_git("status", "--porcelain")
        return bool(result.stdout.strip())

    def get_changed_files(self) -> List[str]:
        """Get list of changed files"""
        result = self._run_git("status", "--porcelain")
        files = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                # Extract filename from status line
                parts = line.strip().split(" ", 1)
                if len(parts) == 2:
                    files.append(parts[1])
        return files

    def commit(self, message: Optional[str] = None) -> bool:
        """Commit all changes"""
        if not self.has_changes():
            return False

        # Add all changes
        self._run_git("add", "-A")

        # Generate commit message if not provided
        if not message:
            changed_files = self.get_changed_files()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"Auto-sync: {len(changed_files)} files changed at {timestamp}"

        result = self._run_git("commit", "-m", message)
        return result.returncode == 0

    def push(self) -> bool:
        """Push to remote repository"""
        result = self._run_git("push", self.remote, self.branch)
        return result.returncode == 0

    def sync(self, message: Optional[str] = None) -> dict:
        """Commit and push all changes"""
        result = {
            "has_changes": self.has_changes(),
            "committed": False,
            "pushed": False,
            "error": None
        }

        if not result["has_changes"]:
            return result

        try:
            result["committed"] = self.commit(message)
            if result["committed"]:
                result["pushed"] = self.push()
        except Exception as e:
            result["error"] = str(e)

        return result

    def get_status(self) -> dict:
        """Get current git status"""
        return {
            "has_changes": self.has_changes(),
            "changed_files": self.get_changed_files(),
            "branch": self.branch,
            "remote": self.remote
        }


# Singleton instance
_syncer = None


def get_syncer() -> GitAutoSync:
    """Get the git sync singleton"""
    global _syncer
    if _syncer is None:
        _syncer = GitAutoSync()
    return _syncer


async def auto_sync(message: Optional[str] = None) -> dict:
    """Auto-sync function to be called from agent"""
    syncer = get_syncer()
    return syncer.sync(message)
