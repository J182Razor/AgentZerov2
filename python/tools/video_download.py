import asyncio
import os
import json
from python.helpers.tool import Tool, Response


class VideoDownload(Tool):
    """youtube-dl integration tool for downloading, metadata, and search."""

    async def execute(self, **kwargs) -> Response:
        method = self.method if hasattr(self, "method") and self.method else "download"

        if method == "download":
            return await self._download(**kwargs)
        elif method == "metadata":
            return await self._metadata(**kwargs)
        elif method == "search":
            return await self._search(**kwargs)
        else:
            return Response(message=f"Unknown method: {method}", break_loop=False)

    async def _download(self, **kwargs) -> Response:
        url = self.args.get("url", "") or kwargs.get("url", "")
        if not url:
            return Response(message="Error: 'url' parameter is required for download.", break_loop=False)

        format_arg = self.args.get("format", "") or kwargs.get("format", "best")
        download_dir = os.path.join("tmp", "downloads")
        os.makedirs(download_dir, exist_ok=True)

        output_template = os.path.join(download_dir, "%(title)s.%(ext)s")

        cmd = ["yt-dlp", "-f", format_arg, "-o", output_template, url]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode("utf-8", errors="replace")
            err_output = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                result = f"Download failed (exit code {proc.returncode}).\nStderr: {err_output}"
            else:
                result = f"Download complete.\n{output}"
                if err_output:
                    result += f"\nWarnings: {err_output}"

            return Response(message=result[:4000], break_loop=False)
        except FileNotFoundError:
            return Response(
                message="Error: yt-dlp (youtube-dl) is not installed. Install it with: pip install yt-dlp",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error during download: {str(e)}"[:4000], break_loop=False)

    async def _metadata(self, **kwargs) -> Response:
        url = self.args.get("url", "") or kwargs.get("url", "")
        if not url:
            return Response(message="Error: 'url' parameter is required for metadata.", break_loop=False)

        cmd = ["yt-dlp", "--dump-json", "--no-download", url]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                err_output = stderr.decode("utf-8", errors="replace")
                return Response(message=f"Failed to get metadata: {err_output}"[:4000], break_loop=False)

            output = stdout.decode("utf-8", errors="replace")
            try:
                data = json.loads(output)
                metadata = {
                    "title": data.get("title", ""),
                    "description": data.get("description", "")[:500],
                    "duration": data.get("duration", 0),
                    "uploader": data.get("uploader", ""),
                    "upload_date": data.get("upload_date", ""),
                    "view_count": data.get("view_count", 0),
                    "like_count": data.get("like_count", 0),
                    "formats": len(data.get("formats", [])),
                    "thumbnail": data.get("thumbnail", ""),
                    "webpage_url": data.get("webpage_url", ""),
                }
                result = json.dumps(metadata, indent=2)
            except json.JSONDecodeError:
                result = output

            return Response(message=result[:4000], break_loop=False)
        except FileNotFoundError:
            return Response(
                message="Error: yt-dlp (youtube-dl) is not installed. Install it with: pip install yt-dlp",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error fetching metadata: {str(e)}"[:4000], break_loop=False)

    async def _search(self, **kwargs) -> Response:
        query = self.args.get("query", "") or kwargs.get("query", "")
        if not query:
            return Response(message="Error: 'query' parameter is required for search.", break_loop=False)

        count = self.args.get("count", 5) or kwargs.get("count", 5)
        search_term = f"ytsearch{count}:{query}"

        cmd = ["yt-dlp", "--dump-json", "--no-download", "--flat-playlist", search_term]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                err_output = stderr.decode("utf-8", errors="replace")
                return Response(message=f"Search failed: {err_output}"[:4000], break_loop=False)

            output = stdout.decode("utf-8", errors="replace")
            results = []
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    results.append({
                        "title": data.get("title", ""),
                        "url": data.get("url", data.get("webpage_url", "")),
                        "duration": data.get("duration", 0),
                        "uploader": data.get("uploader", ""),
                        "view_count": data.get("view_count", 0),
                    })
                except json.JSONDecodeError:
                    continue

            result = json.dumps(results, indent=2)
            return Response(message=result[:4000], break_loop=False)
        except FileNotFoundError:
            return Response(
                message="Error: yt-dlp (youtube-dl) is not installed. Install it with: pip install yt-dlp",
                break_loop=False,
            )
        except Exception as e:
            return Response(message=f"Error during search: {str(e)}"[:4000], break_loop=False)
