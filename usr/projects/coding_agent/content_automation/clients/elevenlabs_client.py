"""ElevenLabs client for voice generation."""
import asyncio
from pathlib import Path
from typing import Optional
import aiohttp
import aiofiles

from content_automation.config.settings import settings
from content_automation.core.logging import get_logger
from content_automation.core.errors import ExternalAPIError, VoiceGenerationError
from content_automation.core.interfaces import VoiceGenerator

logger = get_logger(__name__)


class ElevenLabsClient(VoiceGenerator):
    """Client for ElevenLabs voice generation API."""

    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.model = settings.elevenlabs_model
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def generate_voice(
        self,
        text: str,
        voice_id: str,
        output_path: Path
    ) -> Path:
        """Generate voice audio from text.

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID
            output_path: Path to save audio file

        Returns:
            Path to generated audio file
        """
        logger.info(f"Generating voice for {len(text)} characters")

        url = f"{self.base_url}/text-to-speech/{voice_id}"

        data = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
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
                            "ElevenLabs",
                            f"Voice generation failed: {error_text}",
                            response.status
                        )

                    # Save audio file
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(output_path, 'wb') as f:
                        await f.write(await response.read())

            logger.info(f"Voice generated successfully: {output_path}")
            return output_path

        except aiohttp.ClientError as e:
            logger.error(f"ElevenLabs request failed: {e}")
            raise VoiceGenerationError(f"Failed to generate voice: {e}")

    async def get_voices(self) -> list:
        """Get list of available voices."""
        logger.info("Fetching available voices")

        url = f"{self.base_url}/voices"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            "ElevenLabs",
                            f"Failed to fetch voices: {error_text}",
                            response.status
                        )

                    data = await response.json()
                    voices = data.get("voices", [])
                    logger.info(f"Found {len(voices)} voices")
                    return voices

        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch voices: {e}")
            raise ExternalAPIError("ElevenLabs", str(e))

    async def clone_voice(
        self,
        name: str,
        audio_files: list[Path],
        description: Optional[str] = None
    ) -> str:
        """Clone a voice from audio samples.

        Args:
            name: Name for the cloned voice
            audio_files: List of audio file paths
            description: Optional voice description

        Returns:
            Voice ID of the cloned voice
        """
        logger.info(f"Cloning voice: {name}")

        url = f"{self.base_url}/voices/add"

        # Prepare multipart form data
        data = aiohttp.FormData()
        data.add_field('name', name)
        if description:
            data.add_field('description', description)

        for audio_file in audio_files:
            async with aiofiles.open(audio_file, 'rb') as f:
                content = await f.read()
                data.add_field(
                    'files',
                    content,
                    filename=audio_file.name,
                    content_type='audio/mpeg'
                )

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"xi-api-key": self.api_key}
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ExternalAPIError(
                            "ElevenLabs",
                            f"Voice cloning failed: {error_text}",
                            response.status
                        )

                    result = await response.json()
                    voice_id = result.get("voice_id")
                    logger.info(f"Voice cloned successfully: {voice_id}")
                    return voice_id

        except aiohttp.ClientError as e:
            logger.error(f"Voice cloning failed: {e}")
            raise VoiceGenerationError(f"Failed to clone voice: {e}")
