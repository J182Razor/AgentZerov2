"""Apify client for X/Twitter video scraping."""
import asyncio
from typing import Any, Dict, List
from datetime import datetime, timedelta
import aiohttp

from content_automation.config.settings import settings
from content_automation.core.logging import get_logger
from content_automation.core.errors import ExternalAPIError, ScrapingError
from content_automation.core.interfaces import Scraper

logger = get_logger(__name__)


class ApifyClient(Scraper):
    """Client for Apify X/Twitter scraping."""

    def __init__(self):
        self.token = settings.apify_token
        self.actor_id = settings.apify_actor_id
        self.base_url = "https://api.apify.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def scrape_videos(
        self,
        handles: List[str],
        min_views: int = 100000,
        max_age_days: int = 3
    ) -> List[Dict[str, Any]]:
        """Scrape videos from X/Twitter accounts.

        Args:
            handles: List of X handles to scrape
            min_views: Minimum view count filter
            max_age_days: Maximum age of videos in days

        Returns:
            List of video metadata dictionaries
        """
        logger.info(f"Scraping {len(handles)} X accounts")

        all_videos = []

        for handle in handles:
            try:
                videos = await self._scrape_handle(
                    handle,
                    min_views,
                    max_age_days
                )
                all_videos.extend(videos)
                logger.info(f"Found {len(videos)} videos from @{handle}")
            except Exception as e:
                logger.error(f"Failed to scrape @{handle}: {e}")
                continue

        logger.info(f"Total videos scraped: {len(all_videos)}")
        return all_videos

    async def _scrape_handle(
        self,
        handle: str,
        min_views: int,
        max_age_days: int
    ) -> List[Dict[str, Any]]:
        """Scrape videos from a single X handle."""
        # Start actor run
        run_input = {
            "handles": [handle],
            "tweetsDesired": 50,
            "includeSearchTerms": False,
            "onlyVideos": True,
        }

        url = f"{self.base_url}/acts/{self.actor_id}/runs"

        try:
            async with aiohttp.ClientSession() as session:
                # Start the actor
                async with session.post(
                    url,
                    headers=self.headers,
                    json=run_input
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            "Apify",
                            f"Failed to start actor: {error_text}",
                            response.status
                        )

                    run_data = await response.json()
                    run_id = run_data["data"]["id"]

                # Wait for completion
                await self._wait_for_run(run_id)

                # Get results
                dataset_id = run_data["data"]["defaultDatasetId"]
                videos = await self._get_dataset_items(dataset_id)

                # Filter videos
                filtered = self._filter_videos(
                    videos,
                    handle,
                    min_views,
                    max_age_days
                )

                return filtered

        except aiohttp.ClientError as e:
            logger.error(f"Apify request failed: {e}")
            raise ScrapingError(f"Failed to scrape @{handle}: {e}")

    async def _wait_for_run(self, run_id: str, timeout: int = 300) -> None:
        """Wait for actor run to complete."""
        url = f"{self.base_url}/actor-runs/{run_id}"
        start_time = datetime.now()

        async with aiohttp.ClientSession() as session:
            while True:
                if (datetime.now() - start_time).seconds > timeout:
                    raise ScrapingError(f"Run {run_id} timed out")

                async with session.get(url, headers=self.headers) as response:
                    data = await response.json()
                    status = data["data"]["status"]

                    if status == "SUCCEEDED":
                        return
                    elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                        raise ScrapingError(f"Run {run_id} {status}")

                    await asyncio.sleep(5)

    async def _get_dataset_items(self, dataset_id: str) -> List[Dict]:
        """Get items from dataset."""
        url = f"{self.base_url}/datasets/{dataset_id}/items"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise ExternalAPIError(
                        "Apify",
                        f"Failed to get dataset: {error_text}",
                        response.status
                    )

                return await response.json()

    def _filter_videos(
        self,
        videos: List[Dict],
        handle: str,
        min_views: int,
        max_age_days: int
    ) -> List[Dict[str, Any]]:
        """Filter videos by views and age."""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        filtered = []

        for video in videos:
            # Check if has video
            if not video.get("videos"):
                continue

            # Check views
            views = video.get("viewCount", 0)
            if views < min_views:
                continue

            # Check age
            created_at = datetime.fromisoformat(
                video.get("createdAt", "").replace("Z", "+00:00")
            )
            if created_at < cutoff_date:
                continue

            # Extract video URL
            video_url = video["videos"][0].get("url") if video["videos"] else None

            filtered.append({
                "tweet_id": video.get("id"),
                "url": video.get("url"),
                "video_url": video_url,
                "views": views,
                "created_at": video.get("createdAt"),
                "text": video.get("text"),
                "handle": handle,
            })

        return filtered
