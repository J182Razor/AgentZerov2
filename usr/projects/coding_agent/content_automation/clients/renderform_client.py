"""RenderForm client for image overlay generation."""
import asyncio
from pathlib import Path
from typing import Dict, Any
import aiohttp
import aiofiles

from content_automation.config.settings import settings
from content_automation.core.logging import get_logger
from content_automation.core.errors import ExternalAPIError

logger = get_logger(__name__)


class RenderFormClient:
    """Client for RenderForm image generation API."""

    def __init__(self):
        self.api_key = settings.renderform_api_key
        self.template_id = settings.renderform_template_id
        self.base_url = "https://get.renderform.io/api/v2"
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

    async def generate_x_handle_overlay(
        self,
        handle: str,
        profile_image_url: str,
        view_count: int,
        output_path: Path
    ) -> Path:
        """Generate X handle overlay image."""
        logger.info(f"Generating overlay for @{handle}")

        formatted_views = self._format_view_count(view_count)

        template_data = {
            "template": self.template_id or "x-handle-overlay",
            "data": {
                "handle": f"@{handle}",
                "profile_image": profile_image_url,
                "views": formatted_views
            }
        }

        url = f"{self.base_url}/render"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=template_data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            "RenderForm",
                            f"Overlay generation failed: {error_text}",
                            response.status
                        )

                    result = await response.json()
                    image_url = result.get("href")
                    await self._download_image(image_url, output_path)

                    logger.info(f"Overlay generated: {output_path}")
                    return output_path

        except aiohttp.ClientError as e:
            logger.error(f"RenderForm request failed: {e}")
            raise ExternalAPIError("RenderForm", str(e))

    async def _download_image(self, url: str, output_path: Path) -> None:
        """Download image from URL."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status >= 400:
                    raise ExternalAPIError(
                        "RenderForm",
                        f"Failed to download image: {response.status}"
                    )

                async with aiofiles.open(output_path, 'wb') as f:
                    await f.write(await response.read())

    def _format_view_count(self, count: int) -> str:
        """Format view count for display."""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        else:
            return str(count)
