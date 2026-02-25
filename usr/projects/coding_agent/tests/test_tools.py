"""Tests for tool modules."""
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from content_automation.tools.ffmpeg_wrapper import FFmpegWrapper
from content_automation.tools.whisper_wrapper import WhisperWrapper


@pytest.mark.asyncio
async def test_ffmpeg_combine_videos(temp_dir):
    """Test FFmpeg can combine videos."""
    avatar_video = temp_dir / "avatar.mp4"
    main_video = temp_dir / "main.mp4"
    output_video = temp_dir / "output.mp4"

    # Create dummy files
    avatar_video.touch()
    main_video.touch()

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_process

        result = await FFmpegWrapper.combine_videos(
            avatar_video=avatar_video,
            main_video=main_video,
            output_path=output_video
        )

        assert result == output_video
        mock_subprocess.assert_called_once()


@pytest.mark.asyncio
async def test_whisper_transcribe(temp_dir):
    """Test Whisper can transcribe audio."""
    audio_file = temp_dir / "test.mp3"
    audio_file.touch()

    whisper = WhisperWrapper(model="base")

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_process

        # Mock JSON file creation
        json_file = audio_file.with_suffix('.json')
        json_file.write_text('{"text": "Test transcription"}')

        result = await whisper.transcribe(audio_file)

        assert "text" in result
        assert result["text"] == "Test transcription"
