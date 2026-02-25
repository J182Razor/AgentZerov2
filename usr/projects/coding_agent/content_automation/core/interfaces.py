"""Abstract base classes defining system interfaces."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path


class Scraper(ABC):
    """Interface for content scraping services."""

    @abstractmethod
    async def scrape_videos(
        self,
        handles: List[str],
        min_views: int = 100000,
        max_age_days: int = 3
    ) -> List[Dict[str, Any]]:
        """Scrape videos from social media accounts.

        Args:
            handles: List of account handles to scrape
            min_views: Minimum view count filter
            max_age_days: Maximum age of videos in days

        Returns:
            List of video metadata dictionaries
        """
        pass


class ScriptGenerator(ABC):
    """Interface for AI script generation."""

    @abstractmethod
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
        pass


class VoiceGenerator(ABC):
    """Interface for voice synthesis services."""

    @abstractmethod
    async def generate_voice(
        self,
        text: str,
        voice_id: str,
        output_path: Path
    ) -> Path:
        """Generate voice audio from text.

        Args:
            text: Text to convert to speech
            voice_id: Voice identifier
            output_path: Path to save audio file

        Returns:
            Path to generated audio file
        """
        pass


class AvatarGenerator(ABC):
    """Interface for avatar video generation."""

    @abstractmethod
    async def generate_avatar(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path
    ) -> Path:
        """Generate avatar video with lip-sync.

        Args:
            image_path: Path to avatar image
            audio_path: Path to audio file
            output_path: Path to save video

        Returns:
            Path to generated avatar video
        """
        pass

    @abstractmethod
    async def animate_image(
        self,
        image_path: Path,
        output_path: Path,
        duration: int = 4
    ) -> Path:
        """Animate a static image.

        Args:
            image_path: Path to image
            output_path: Path to save video
            duration: Duration in seconds

        Returns:
            Path to animated video
        """
        pass


class VideoProcessor(ABC):
    """Interface for video processing operations."""

    @abstractmethod
    async def combine_videos(
        self,
        avatar_video: Path,
        main_video: Path,
        output_path: Path,
        music_path: Optional[Path] = None
    ) -> Path:
        """Combine avatar intro with main video.

        Args:
            avatar_video: Path to avatar intro video
            main_video: Path to main content video
            output_path: Path to save combined video
            music_path: Optional background music

        Returns:
            Path to combined video
        """
        pass

    @abstractmethod
    async def add_captions(
        self,
        video_path: Path,
        output_path: Path
    ) -> Path:
        """Add captions to video.

        Args:
            video_path: Path to input video
            output_path: Path to save captioned video

        Returns:
            Path to captioned video
        """
        pass

    @abstractmethod
    async def add_overlay(
        self,
        video_path: Path,
        overlay_image: Path,
        output_path: Path,
        position: str = "top-right"
    ) -> Path:
        """Add image overlay to video.

        Args:
            video_path: Path to input video
            overlay_image: Path to overlay image
            output_path: Path to save video
            position: Overlay position

        Returns:
            Path to video with overlay
        """
        pass


class Publisher(ABC):
    """Interface for multi-platform publishing."""

    @abstractmethod
    async def publish(
        self,
        video_path: Path,
        platforms: List[str],
        captions: Dict[str, str],
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Publish video to multiple platforms.

        Args:
            video_path: Path to video file
            platforms: List of platform names
            captions: Platform-specific captions
            metadata: Additional metadata

        Returns:
            Dictionary of platform: post_id mappings
        """
        pass

    @abstractmethod
    async def generate_captions(
        self,
        script: str,
        platforms: List[str]
    ) -> Dict[str, str]:
        """Generate platform-specific captions.

        Args:
            script: Original script text
            platforms: List of platform names

        Returns:
            Dictionary of platform: caption mappings
        """
        pass


class Database(ABC):
    """Interface for database operations."""

    @abstractmethod
    async def get_profiles(self) -> List[Dict[str, Any]]:
        """Get list of X profiles to monitor."""
        pass

    @abstractmethod
    async def save_idea(self, idea: Dict[str, Any]) -> str:
        """Save scraped video idea."""
        pass

    @abstractmethod
    async def get_scheduled_content(self) -> List[Dict[str, Any]]:
        """Get content scheduled for publishing."""
        pass

    @abstractmethod
    async def update_status(
        self,
        record_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update record status."""
        pass

    @abstractmethod
    async def get_avatars(self) -> List[Dict[str, Any]]:
        """Get list of available avatars."""
        pass

    @abstractmethod
    async def get_music(self) -> List[Dict[str, Any]]:
        """Get list of available music tracks."""
        pass
