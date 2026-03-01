import asyncio
from python.helpers.tool import Tool, Response


class IssueTracker(Tool):
    """Beads (bd) git-backed issue tracker integration."""

    async def execute(self, **kwargs) -> Response:
        method = self.method if hasattr(self, "method") and self.method else "list"

        if method == "create":
            return await self._create(**kwargs)
        elif method == "list":
            return await self._list(**kwargs)
        elif method == "ready":
            return await self._ready(**kwargs)
        elif method == "update":
            return await self._update(**kwargs)
        elif method == "show":
            return await self._show(**kwargs)
        else:
            return Response(message=f"Unknown method: {method}", break_loop=False)

    async def _run_bd(self, args: list[str]) -> tuple[int, str, str]:
        """Run a bd CLI command and return (returncode, stdout, stderr)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "bd", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return (
                proc.returncode,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
        except FileNotFoundError:
            return (
                -1,
                "",
                "Error: 'bd' (Beads) is not installed. "
                "Install it with: npm install -g beads-cli\n"
                "Or visit: https://github.com/beads-project/beads",
            )

    async def _create(self, **kwargs) -> Response:
        title = self.args.get("title", "") or kwargs.get("title", "")
        body = self.args.get("body", "") or kwargs.get("body", "")

        if not title:
            return Response(message="Error: 'title' parameter is required to create an issue.", break_loop=False)

        cmd_args = ["create", "--title", title]
        if body:
            cmd_args.extend(["--body", body])

        returncode, stdout, stderr = await self._run_bd(cmd_args)

        if returncode != 0:
            return Response(message=f"Failed to create issue:\n{stderr}\n{stdout}".strip(), break_loop=False)

        result = f"Issue created successfully.\n{stdout}".strip()
        return Response(message=result[:4000], break_loop=False)

    async def _list(self, **kwargs) -> Response:
        status_filter = self.args.get("status", "") or kwargs.get("status", "")
        cmd_args = ["list"]
        if status_filter:
            cmd_args.extend(["--status", status_filter])

        returncode, stdout, stderr = await self._run_bd(cmd_args)

        if returncode != 0:
            return Response(message=f"Failed to list issues:\n{stderr}\n{stdout}".strip(), break_loop=False)

        result = stdout.strip() if stdout.strip() else "No issues found."
        return Response(message=result[:4000], break_loop=False)

    async def _ready(self, **kwargs) -> Response:
        returncode, stdout, stderr = await self._run_bd(["ready"])

        if returncode != 0:
            return Response(message=f"Failed to get ready issues:\n{stderr}\n{stdout}".strip(), break_loop=False)

        result = stdout.strip() if stdout.strip() else "No issues are ready to work on."
        return Response(message=result[:4000], break_loop=False)

    async def _update(self, **kwargs) -> Response:
        issue_id = self.args.get("id", "") or kwargs.get("id", "")
        status = self.args.get("status", "") or kwargs.get("status", "")

        if not issue_id:
            return Response(message="Error: 'id' parameter is required to update an issue.", break_loop=False)
        if not status:
            return Response(message="Error: 'status' parameter is required to update an issue.", break_loop=False)

        cmd_args = ["update", str(issue_id), "--status", status]
        returncode, stdout, stderr = await self._run_bd(cmd_args)

        if returncode != 0:
            return Response(message=f"Failed to update issue:\n{stderr}\n{stdout}".strip(), break_loop=False)

        result = f"Issue {issue_id} updated to status '{status}'.\n{stdout}".strip()
        return Response(message=result[:4000], break_loop=False)

    async def _show(self, **kwargs) -> Response:
        issue_id = self.args.get("id", "") or kwargs.get("id", "")

        if not issue_id:
            return Response(message="Error: 'id' parameter is required to show an issue.", break_loop=False)

        cmd_args = ["show", str(issue_id)]
        returncode, stdout, stderr = await self._run_bd(cmd_args)

        if returncode != 0:
            return Response(message=f"Failed to show issue:\n{stderr}\n{stdout}".strip(), break_loop=False)

        result = stdout.strip() if stdout.strip() else f"No details found for issue {issue_id}."
        return Response(message=result[:4000], break_loop=False)
