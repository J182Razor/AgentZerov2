"""FFmpeg wrapper for video processing operations."""
import asyncio
from pathlib import Path
from typing import Optional, List
import subprocess

from content_automation.core.logging import get_logger
from content_automation.core.errors import VideoProcessingError

logger = get_logger(__name__)


class FFmpegWrapper:
    """Wrapper for FFmpeg video processing operations."""

    @staticmethod
    async def combine_videos(
        avatar_video: Path,
        main_video: Path,
        output_path: Path,
        music_path: Optional[Path] = None,
        avatar_duration: int = 3
    ) -> Path:
        """Combine avatar intro with main video."""
        logger.info("Combining videos with FFmpeg")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        if music_path:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(avatar_video),
                '-i', str(main_video),
                '-i', str(music_path),
                '-filter_complex',
                f'[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa];[outa][2:a]amix=inputs=2:duration=first[a]',
                '-map', '[outv]',
                '-map', '[a]',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                str(output_path)
            ]
        else:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(avatar_video),
                '-i', str(main_video),
                '-filter_complex',
                '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]',
                '-map', '[v]',
                '-map', '[a]',
                '-c:v', 'libx264',
                '-c:a', 'aac',
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
                logger.error(f"FFmpeg error: {error_msg}")
                raise VideoProcessingError(f"Video combination failed: {error_msg}")

            logger.info(f"Videos combined successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"FFmpeg execution failed: {e}")
            raise VideoProcessingError(f"Failed to combine videos: {e}")

    @staticmethod
    async def add_overlay(
        video_path: Path,
        overlay_image: Path,
        output_path: Path,
        position: str = "top-right",
        margin: int = 20
    ) -> Path:
        """Add image overlay to video."""
        logger.info(f"Adding overlay to video at {position}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Position mapping
        positions = {
            "top-left": f"{margin}:{margin}",
            "top-right": f"W-w-{margin}:{margin}",
            "bottom-left": f"{margin}:H-h-{margin}",
            "bottom-right": f"W-w-{margin}:H-h-{margin}",
            "center": "(W-w)/2:(H-h)/2"
        }

        overlay_pos = positions.get(position, positions["top-right"])

        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-i', str(overlay_image),
            '-filter_complex',
            f'[1:v]scale=200:-1[ovrl];[0:v][ovrl]overlay={overlay_pos}',
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
                logger.error(f"FFmpeg error: {error_msg}")
                raise VideoProcessingError(f"Overlay addition failed: {error_msg}")

            logger.info(f"Overlay added successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Overlay addition failed: {e}")
            raise VideoProcessingError(f"Failed to add overlay: {e}")

    @staticmethod
    async def extract_audio(
        video_path: Path,
        output_path: Path
    ) -> Path:
        """Extract audio from video."""
        logger.info("Extracting audio from video")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vn',
            '-acodec', 'libmp3lame',
            '-q:a', '2',
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
                raise VideoProcessingError(f"Audio extraction failed: {error_msg}")

            logger.info(f"Audio extracted: {output_path}")
            return output_path

        except Exception as e:
            raise VideoProcessingError(f"Failed to extract audio: {e}")

    @staticmethod
    async def resize_video(
        video_path: Path,
        output_path: Path,
        width: int = 1080,
        height: int = 1920
    ) -> Path:
        """Resize video to specified dimensions."""
        logger.info(f"Resizing video to {width}x{height}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
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
                raise VideoProcessingError(f"Video resize failed: {error_msg}")

            logger.info(f"Video resized: {output_path}")
            return output_path

        except Exception as e:
            raise VideoProcessingError(f"Failed to resize video: {e}")
