"""Airtable client for database operations."""
import asyncio
from typing import Any, Dict, List, Optional
import aiohttp

from content_automation.config.settings import settings
from content_automation.core.logging import get_logger
from content_automation.core.errors import ExternalAPIError
from content_automation.core.interfaces import Database

logger = get_logger(__name__)


class AirtableClient(Database):
    """Client for Airtable API operations."""

    def __init__(self):
        self.base_id = settings.airtable_base_id
        self.api_key = settings.airtable_api_key
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Airtable API."""
        url = f"{self.base_url}/{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=self.headers,
                    json=data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            "Airtable",
                            f"Request failed: {error_text}",
                            response.status
                        )
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Airtable request failed: {e}")
            raise ExternalAPIError("Airtable", str(e))

    async def get_profiles(self) -> List[Dict[str, Any]]:
        """Get list of X profiles to monitor."""
        logger.info("Fetching X profiles from Airtable")

        response = await self._request(
            "GET",
            settings.airtable_x_profiles_table
        )

        profiles = []
        for record in response.get("records", []):
            fields = record.get("fields", {})
            if fields.get("active", True):
                profiles.append({
                    "id": record["id"],
                    "handle": fields.get("handle"),
                    "min_views": fields.get("min_views", settings.min_views),
                    "category": fields.get("category"),
                })

        logger.info(f"Found {len(profiles)} active profiles")
        return profiles

    async def save_idea(self, idea: Dict[str, Any]) -> str:
        """Save scraped video idea."""
        logger.info(f"Saving idea: {idea.get('url')}")

        data = {
            "fields": {
                "tweet_id": idea.get("tweet_id"),
                "url": idea.get("url"),
                "views": idea.get("views"),
                "created_at": idea.get("created_at"),
                "status": "new",
                "raw_video_url": idea.get("video_url"),
                "handle": idea.get("handle"),
            }
        }

        response = await self._request(
            "POST",
            settings.airtable_ideas_table,
            data
        )

        record_id = response["id"]
        logger.info(f"Saved idea with ID: {record_id}")
        return record_id

    async def get_scheduled_content(self) -> List[Dict[str, Any]]:
        """Get content scheduled for publishing."""
        logger.info("Fetching scheduled content")

        # Filter for records with status="scheduled"
        filter_formula = "{status}='scheduled'"

        response = await self._request(
            "GET",
            f"{settings.airtable_create_table}?filterByFormula={filter_formula}"
        )

        content = []
        for record in response.get("records", []):
            fields = record.get("fields", {})
            content.append({
                "id": record["id"],
                "video_path": fields.get("output_video"),
                "script": fields.get("script"),
                "platforms": fields.get("platforms", settings.platforms),
                "metadata": fields,
            })

        logger.info(f"Found {len(content)} scheduled items")
        return content

    async def update_status(
        self,
        record_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update record status."""
        logger.info(f"Updating record {record_id} to status: {status}")

        fields = {"status": status}
        if metadata:
            fields.update(metadata)

        data = {"fields": fields}

        await self._request(
            "PATCH",
            f"{settings.airtable_create_table}/{record_id}",
            data
        )

        logger.info(f"Updated record {record_id}")

    async def get_avatars(self) -> List[Dict[str, Any]]:
        """Get list of available avatars."""
        logger.info("Fetching avatars")

        response = await self._request(
            "GET",
            settings.airtable_avatars_table
        )

        avatars = []
        for record in response.get("records", []):
            fields = record.get("fields", {})
            if fields.get("active", True):
                avatars.append({
                    "id": record["id"],
                    "name": fields.get("name"),
                    "image_url": fields.get("image_url"),
                    "video_url": fields.get("video_url"),
                    "voice_id": fields.get("voice_id"),
                    "style": fields.get("style"),
                })

        logger.info(f"Found {len(avatars)} active avatars")
        return avatars

    async def get_music(self) -> List[Dict[str, Any]]:
        """Get list of available music tracks."""
        logger.info("Fetching music tracks")

        response = await self._request(
            "GET",
            settings.airtable_music_table
        )

        tracks = []
        for record in response.get("records", []):
            fields = record.get("fields", {})
            if fields.get("active", True):
                tracks.append({
                    "id": record["id"],
                    "name": fields.get("name"),
                    "track_url": fields.get("track_url"),
                    "mood": fields.get("mood"),
                })

        logger.info(f"Found {len(tracks)} active tracks")
        return tracks

    async def create_content_record(
        self,
        idea_id: str,
        script: str,
        avatar_id: str,
        voice_id: str
    ) -> str:
        """Create a new content creation record."""
        logger.info(f"Creating content record for idea: {idea_id}")

        data = {
            "fields": {
                "idea_id": idea_id,
                "script": script,
                "avatar_id": avatar_id,
                "voice_id": voice_id,
                "status": "processing",
            }
        }

        response = await self._request(
            "POST",
            settings.airtable_create_table,
            data
        )

        record_id = response["id"]
        logger.info(f"Created content record: {record_id}")
        return record_id
