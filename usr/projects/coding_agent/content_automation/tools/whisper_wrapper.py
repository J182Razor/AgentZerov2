"""Whisper wrapper for audio transcription and caption generation."""
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import json

from content_automation.core.logging import get_logger
from content_automation.core.errors import VideoProcessingError

logger = get_logger(__name__)


class WhisperWrapper:
    """Wrapper for Whisper audio transcription."""

    def __init__(self, model: str = "base"):
        self.model = model

    async def transcribe(
        self,
        audio_path: Path,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (default: en)

        Returns:
            Transcription result with text and segments
        """
        logger.info(f"Transcribing audio: {audio_path}")

        cmd = [
            'whisper',
            str(audio_path),
            '--model', self.model,
            '--language', language,
            '--output_format', 'json',
            '--output_dir', str(audio_path.parent)
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"Whisper error: {error_msg}")
                raise VideoProcessingError(f"Transcription failed: {error_msg}")

            # Read the generated JSON file
            json_path = audio_path.with_suffix('.json')
            with open(json_path, 'r') as f:
                result = json.load(f)

            logger.info("Transcription completed successfully")
            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise VideoProcessingError(f"Failed to transcribe audio: {e}")

    async def generate_srt(
        self,
        audio_path: Path,
        output_path: Path,
        language: str = "en"
    ) -> Path:
        """Generate SRT subtitle file.

        Args:
            audio_path: Path to audio file
            output_path: Path to save SRT file
            language: Language code

        Returns:
            Path to generated SRT file
        """
        logger.info("Generating SRT subtitles")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'whisper',
            str(audio_path),
            '--model', self.model,
            '--language', language,
            '--output_format', 'srt',
            '--output_dir', str(output_path.parent)
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                raise VideoProcessingError(f"SRT generation failed: {error_msg}")

            # Whisper saves with original filename + .srt
            generated_srt = audio_path.with_suffix('.srt')

            # Move to desired output path if different
            if generated_srt != output_path:
                generated_srt.rename(output_path)

            logger.info(f"SRT file generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"SRT generation failed: {e}")
            raise VideoProcessingError(f"Failed to generate SRT: {e}")

    async def add_captions_to_video(
        self,
        video_path: Path,
        srt_path: Path,
        output_path: Path,
        font_size: int = 24,
        font_color: str = "white",
        outline_color: str = "black"
    ) -> Path:
        """Add captions to video using SRT file.

        Args:
            video_path: Path to input video
            srt_path: Path to SRT subtitle file
            output_path: Path to save captioned video
            font_size: Caption font size
            font_color: Caption text color
            outline_color: Caption outline color

        Returns:
            Path to captioned video
        """
        logger.info("Adding captions to video")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # FFmpeg command to burn subtitles
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', f"subtitles={srt_path}:force_style='FontSize={font_size},PrimaryColour=&H{font_color},OutlineColour=&H{outline_color},Outline=2'",
            '-c:a', 'copy',
            str(output_path)
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                raise VideoProcessingError(f"Caption addition failed: {error_msg}")

            logger.info(f"Captions added successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to add captions: {e}")
            raise VideoProcessingError(f"Failed to add captions to video: {e}")
