import os
import aiohttp
from python.helpers.tool import Tool, Response


class CodeAnalysis(Tool):
    """FastCode integration for token-efficient codebase understanding."""

    FASTCODE_BASE_URL = os.environ.get("FASTCODE_URL", "http://localhost:8100")

    async def execute(self, **kwargs) -> Response:
        method = self.method if hasattr(self, "method") and self.method else "search"

        if method == "index":
            return await self._index(**kwargs)
        elif method == "search":
            return await self._search(**kwargs)
        elif method == "explain":
            return await self._explain(**kwargs)
        elif method == "navigate":
            return await self._navigate(**kwargs)
        else:
            return Response(
                message=f"Unknown method '{method}'. Available methods: index, search, explain, navigate.",
                break_loop=False,
            )

    async def _index(self, **kwargs) -> Response:
        path = self.args.get("path", "") or kwargs.get("path", "")
        if not path:
            return Response(message="Error: 'path' argument is required for index method.", break_loop=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.FASTCODE_BASE_URL}/api/index",
                    json={"path": path},
                ) as resp:
                    result = await resp.text()
                    return Response(message=result, break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to FastCode server at {self.FASTCODE_BASE_URL}. "
                        "Please ensure the FastCode server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling FastCode index API: {e}", break_loop=False)

    async def _search(self, **kwargs) -> Response:
        query = self.args.get("query", "") or kwargs.get("query", "")
        if not query:
            return Response(message="Error: 'query' argument is required for search method.", break_loop=False)

        params = {"q": query}
        path = self.args.get("path", "") or kwargs.get("path", "")
        if path:
            params["path"] = path

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.FASTCODE_BASE_URL}/api/search",
                    params=params,
                ) as resp:
                    result = await resp.text()
                    return Response(message=result, break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to FastCode server at {self.FASTCODE_BASE_URL}. "
                        "Please ensure the FastCode server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling FastCode search API: {e}", break_loop=False)

    async def _explain(self, **kwargs) -> Response:
        path = self.args.get("path", "") or kwargs.get("path", "")
        if not path:
            return Response(message="Error: 'path' argument is required for explain method.", break_loop=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.FASTCODE_BASE_URL}/api/explain",
                    params={"path": path},
                ) as resp:
                    result = await resp.text()
                    return Response(message=result, break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to FastCode server at {self.FASTCODE_BASE_URL}. "
                        "Please ensure the FastCode server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling FastCode explain API: {e}", break_loop=False)

    async def _navigate(self, **kwargs) -> Response:
        symbol = self.args.get("symbol", "") or kwargs.get("symbol", "")
        if not symbol:
            return Response(message="Error: 'symbol' argument is required for navigate method.", break_loop=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.FASTCODE_BASE_URL}/api/navigate",
                    params={"symbol": symbol},
                ) as resp:
                    result = await resp.text()
                    return Response(message=result, break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to FastCode server at {self.FASTCODE_BASE_URL}. "
                        "Please ensure the FastCode server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling FastCode navigate API: {e}", break_loop=False)
