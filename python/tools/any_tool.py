import os
import aiohttp
from python.helpers.tool import Tool, Response


class AnyTool(Tool):
    """AnyTool universal tool executor."""

    ANYTOOL_BASE_URL = os.environ.get("ANYTOOL_URL", "http://localhost:8200")
    MAX_RESPONSE_LENGTH = 4000

    async def execute(self, **kwargs) -> Response:
        method = self.method if hasattr(self, "method") and self.method else "execute"

        if method == "execute":
            return await self._execute(**kwargs)
        elif method == "discover":
            return await self._discover(**kwargs)
        elif method == "gui":
            return await self._gui(**kwargs)
        else:
            return Response(
                message=f"Unknown method '{method}'. Available methods: execute, discover, gui.",
                break_loop=False,
            )

    def _truncate(self, text: str) -> str:
        if len(text) > self.MAX_RESPONSE_LENGTH:
            return text[: self.MAX_RESPONSE_LENGTH] + "\n... [truncated]"
        return text

    async def _execute(self, **kwargs) -> Response:
        task = self.args.get("task", "") or kwargs.get("task", "")
        if not task:
            return Response(message="Error: 'task' argument is required for execute method.", break_loop=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ANYTOOL_BASE_URL}/api/execute",
                    json={"task": task},
                ) as resp:
                    result = await resp.text()
                    return Response(message=self._truncate(result), break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to AnyTool server at {self.ANYTOOL_BASE_URL}. "
                        "Please ensure the AnyTool server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling AnyTool execute API: {e}", break_loop=False)

    async def _discover(self, **kwargs) -> Response:
        query = self.args.get("query", "") or kwargs.get("query", "")
        if not query:
            return Response(message="Error: 'query' argument is required for discover method.", break_loop=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ANYTOOL_BASE_URL}/api/discover",
                    params={"q": query},
                ) as resp:
                    result = await resp.text()
                    return Response(message=self._truncate(result), break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to AnyTool server at {self.ANYTOOL_BASE_URL}. "
                        "Please ensure the AnyTool server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling AnyTool discover API: {e}", break_loop=False)

    async def _gui(self, **kwargs) -> Response:
        action = self.args.get("action", "") or kwargs.get("action", "")
        if not action:
            return Response(message="Error: 'action' argument is required for gui method.", break_loop=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ANYTOOL_BASE_URL}/api/gui",
                    json={"action": action},
                ) as resp:
                    result = await resp.text()
                    return Response(message=self._truncate(result), break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to AnyTool server at {self.ANYTOOL_BASE_URL}. "
                        "Please ensure the AnyTool server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling AnyTool gui API: {e}", break_loop=False)
