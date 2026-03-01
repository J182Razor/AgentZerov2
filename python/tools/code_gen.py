import os
import aiohttp
from python.helpers.tool import Tool, Response


class CodeGen(Tool):
    """DeepCode multi-agent code generation."""

    DEEPCODE_BASE_URL = os.environ.get("DEEPCODE_URL", "http://localhost:8300")
    MAX_RESPONSE_LENGTH = 8000

    async def execute(self, **kwargs) -> Response:
        method = self.method if hasattr(self, "method") and self.method else "paper2code"

        if method == "paper2code":
            return await self._paper2code(**kwargs)
        elif method == "text2web":
            return await self._text2web(**kwargs)
        elif method == "text2backend":
            return await self._text2backend(**kwargs)
        else:
            return Response(
                message=f"Unknown method '{method}'. Available methods: paper2code, text2web, text2backend.",
                break_loop=False,
            )

    def _truncate(self, text: str) -> str:
        if len(text) > self.MAX_RESPONSE_LENGTH:
            return text[: self.MAX_RESPONSE_LENGTH] + "\n... [truncated]"
        return text

    async def _paper2code(self, **kwargs) -> Response:
        paper_url = self.args.get("paper_url", "") or kwargs.get("paper_url", "")
        paper_text = self.args.get("paper_text", "") or kwargs.get("paper_text", "")

        if not paper_url and not paper_text:
            return Response(
                message="Error: 'paper_url' or 'paper_text' argument is required for paper2code method.",
                break_loop=False,
            )

        payload = {}
        if paper_url:
            payload["paper_url"] = paper_url
        if paper_text:
            payload["paper_text"] = paper_text

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.DEEPCODE_BASE_URL}/api/paper2code",
                    json=payload,
                ) as resp:
                    result = await resp.text()
                    return Response(message=self._truncate(result), break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to DeepCode server at {self.DEEPCODE_BASE_URL}. "
                        "Please ensure the DeepCode server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling DeepCode paper2code API: {e}", break_loop=False)

    async def _text2web(self, **kwargs) -> Response:
        description = self.args.get("description", "") or kwargs.get("description", "")
        if not description:
            return Response(
                message="Error: 'description' argument is required for text2web method.",
                break_loop=False,
            )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.DEEPCODE_BASE_URL}/api/text2web",
                    json={"description": description},
                ) as resp:
                    result = await resp.text()
                    return Response(message=self._truncate(result), break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to DeepCode server at {self.DEEPCODE_BASE_URL}. "
                        "Please ensure the DeepCode server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling DeepCode text2web API: {e}", break_loop=False)

    async def _text2backend(self, **kwargs) -> Response:
        spec = self.args.get("spec", "") or kwargs.get("spec", "")
        if not spec:
            return Response(
                message="Error: 'spec' argument is required for text2backend method.",
                break_loop=False,
            )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.DEEPCODE_BASE_URL}/api/text2backend",
                    json={"spec": spec},
                ) as resp:
                    result = await resp.text()
                    return Response(message=self._truncate(result), break_loop=False)
        except aiohttp.ClientConnectorError:
            return Response(
                message=f"Error: Could not connect to DeepCode server at {self.DEEPCODE_BASE_URL}. "
                        "Please ensure the DeepCode server is running.",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error calling DeepCode text2backend API: {e}", break_loop=False)
