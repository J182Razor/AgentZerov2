"""OpenAI client for script generation."""
import asyncio
from typing import Optional
import aiohttp

from content_automation.config.settings import settings
from content_automation.core.logging import get_logger
from content_automation.core.errors import ExternalAPIError
from content_automation.core.interfaces import ScriptGenerator

logger = get_logger(__name__)


class OpenAIClient(ScriptGenerator):
    """Client for OpenAI API script generation."""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_script(
        self,
        video_url: str,
        context: Optional[str] = None
    ) -> str:
        """Generate a script from video content.

        Args:
            video_url: URL of the source video
            context: Additional context for script generation

        Returns:
            Generated script text
        """
        logger.info(f"Generating script for video: {video_url}")

        # Build prompt
        prompt = f"""Create a short-form video script (30-60 seconds) based on this X/Twitter video: {video_url}

The script should:
- Start with a strong hook in the first 3 seconds
- Be conversational and engaging
- Include a clear call-to-action at the end
- Be optimized for TikTok/Instagram Reels format
- Be around 150-200 words
"""

        if context:
            prompt += f"

Additional context: {context}"

        url = f"{self.base_url}/chat/completions"

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert short-form video script writer specializing in viral social media content."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            "OpenAI",
                            f"Script generation failed: {error_text}",
                            response.status
                        )

                    result = await response.json()
                    script = result["choices"][0]["message"]["content"]

                    logger.info(f"Script generated: {len(script)} characters")
                    return script.strip()

        except aiohttp.ClientError as e:
            logger.error(f"OpenAI request failed: {e}")
            raise ExternalAPIError("OpenAI", str(e))

    async def generate_captions(
        self,
        script: str,
        platform: str
    ) -> str:
        """Generate platform-specific caption.

        Args:
            script: Original script text
            platform: Target platform (tiktok, instagram, youtube, facebook)

        Returns:
            Platform-optimized caption
        """
        logger.info(f"Generating {platform} caption")

        platform_guidelines = {
            "tiktok": "Hook-heavy, conversational, 3-5 trending hashtags",
            "instagram": "Story-driven, emoji-friendly, 10-15 mixed hashtags",
            "youtube": "SEO-optimized, descriptive, 5-10 searchable keywords",
            "facebook": "Question-based, shareable, 2-3 minimal hashtags"
        }

        guideline = platform_guidelines.get(platform, "Engaging and platform-appropriate")

        prompt = f"""Convert this video script into a {platform} caption:

{script}

Guidelines: {guideline}

Provide only the caption text, no explanations."""

        url = f"{self.base_url}/chat/completions"

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a social media expert specializing in {platform} content."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.8,
            "max_tokens": 300
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=data
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            "OpenAI",
                            f"Caption generation failed: {error_text}",
                            response.status
                        )

                    result = await response.json()
                    caption = result["choices"][0]["message"]["content"]

                    logger.info(f"Caption generated for {platform}")
                    return caption.strip()

        except aiohttp.ClientError as e:
            logger.error(f"Caption generation failed: {e}")
            raise ExternalAPIError("OpenAI", str(e))
