"""Tests for client modules."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from content_automation.clients.airtable_client import AirtableClient
from content_automation.clients.openai_client import OpenAIClient
from content_automation.clients.elevenlabs_client import ElevenLabsClient


@pytest.mark.asyncio
async def test_airtable_client_get_profiles():
    """Test Airtable client can fetch profiles."""
    client = AirtableClient()

    with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {
            "records": [
                {
                    "id": "rec123",
                    "fields": {
                        "handle": "testuser",
                        "active": True,
                        "min_views": 100000
                    }
                }
            ]
        }

        profiles = await client.get_profiles()

        assert len(profiles) == 1
        assert profiles[0]["handle"] == "testuser"
        assert profiles[0]["id"] == "rec123"


@pytest.mark.asyncio
async def test_openai_client_generate_script(mock_video_url):
    """Test OpenAI client can generate scripts."""
    client = OpenAIClient()

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": "Test script content"
                }
            }]
        })

        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

        script = await client.generate_script(mock_video_url)

        assert isinstance(script, str)
        assert len(script) > 0


@pytest.mark.asyncio
async def test_elevenlabs_client_generate_voice(temp_dir, mock_script):
    """Test ElevenLabs client can generate voice."""
    client = ElevenLabsClient()
    output_path = temp_dir / "test_voice.mp3"

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"fake audio data")

        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response

        with patch('aiofiles.open', create=True) as mock_open:
            mock_file = AsyncMock()
            mock_open.return_value.__aenter__.return_value = mock_file

            result = await client.generate_voice(
                text=mock_script,
                voice_id="test_voice",
                output_path=output_path
            )

            assert result == output_path
