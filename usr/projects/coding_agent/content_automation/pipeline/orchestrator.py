"""Main orchestrator for content automation pipeline."""
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from content_automation.config.settings import settings
from content_automation.core.logging import get_logger
from content_automation.core.errors import AutomationError

from content_automation.clients.airtable_client import AirtableClient
from content_automation.clients.apify_client import ApifyClient
from content_automation.clients.openai_client import OpenAIClient
from content_automation.clients.elevenlabs_client import ElevenLabsClient
from content_automation.clients.blotato_client import BlototoClient
from content_automation.clients.renderform_client import RenderFormClient

from content_automation.tools.ffmpeg_wrapper import FFmpegWrapper
from content_automation.tools.whisper_wrapper import WhisperWrapper

logger = get_logger(__name__)


class ContentAutomation:
    """Main orchestrator for AI avatar content automation."""

    def __init__(self):
        # Initialize clients
        self.db = AirtableClient()
        self.scraper = ApifyClient()
        self.script_gen = OpenAIClient()
        self.voice_gen = ElevenLabsClient()
        self.publisher = BlototoClient()
        self.overlay_gen = RenderFormClient()

        # Initialize tools
        self.ffmpeg = FFmpegWrapper()
        self.whisper = WhisperWrapper(model=settings.whisper_model)

        # Setup directories
        self.work_dir = Path(settings.work_dir)
        self.temp_dir = Path(settings.temp_dir)
        self.output_dir = Path(settings.output_dir)

        for dir_path in [self.work_dir, self.temp_dir, self.output_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def run_idea_scraper(self) -> int:
        """Scrape viral video ideas from X profiles.

        Returns:
            Number of ideas scraped
        """
        logger.info("Starting idea scraper")

        try:
            # Get profiles to monitor
            profiles = await self.db.get_profiles()

            if not profiles:
                logger.warning("No active profiles found")
                return 0

            handles = [p["handle"] for p in profiles]

            # Scrape videos
            videos = await self.scraper.scrape_videos(
                handles=handles,
                min_views=settings.min_views,
                max_age_days=settings.max_video_age_days
            )

            # Save ideas to database
            saved_count = 0
            for video in videos:
                try:
                    await self.db.save_idea(video)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save idea: {e}")

            logger.info(f"Scraped and saved {saved_count} ideas")
            return saved_count

        except Exception as e:
            logger.error(f"Idea scraper failed: {e}")
            raise AutomationError(f"Idea scraping failed: {e}")

    async def create_content(
        self,
        video_url: str,
        avatar_id: Optional[str] = None,
        voice_id: Optional[str] = None
    ) -> Path:
        """Create complete video content from X video URL.

        Args:
            video_url: URL of source X video
            avatar_id: Optional avatar ID (uses first available if not provided)
            voice_id: Optional voice ID (uses avatar's voice if not provided)

        Returns:
            Path to final video file
        """
        logger.info(f"Creating content from: {video_url}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_path = self.work_dir / timestamp
        work_path.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Generate script
            logger.info("Step 1: Generating script")
            script = await self.script_gen.generate_script(video_url)

            # 2. Get avatar
            logger.info("Step 2: Getting avatar")
            avatars = await self.db.get_avatars()
            if not avatars:
                raise AutomationError("No avatars available")

            avatar = next(
                (a for a in avatars if a["id"] == avatar_id),
                avatars[0]
            )

            # 3. Generate voice
            logger.info("Step 3: Generating voice")
            voice_id = voice_id or avatar.get("voice_id")
            if not voice_id:
                raise AutomationError("No voice ID available")

            audio_path = work_path / "voice.mp3"
            await self.voice_gen.generate_voice(
                text=script,
                voice_id=voice_id,
                output_path=audio_path
            )

            # 4. Download source video (placeholder - would use actual downloader)
            logger.info("Step 4: Downloading source video")
            source_video = work_path / "source.mp4"
            # TODO: Implement actual video download

            # 5. Get avatar video
            logger.info("Step 5: Getting avatar video")
            avatar_video_url = avatar.get("video_url")
            if not avatar_video_url:
                raise AutomationError("Avatar video not available")

            # TODO: Download avatar video
            avatar_video = work_path / "avatar.mp4"

            # 6. Combine videos
            logger.info("Step 6: Combining videos")
            combined_video = work_path / "combined.mp4"

            # Get music track
            music_tracks = await self.db.get_music()
            music_path = None
            if music_tracks:
                # TODO: Download music track
                music_path = work_path / "music.mp3"

            await self.ffmpeg.combine_videos(
                avatar_video=avatar_video,
                main_video=source_video,
                output_path=combined_video,
                music_path=music_path
            )

            # 7. Generate and add captions
            logger.info("Step 7: Adding captions")
            srt_path = work_path / "captions.srt"
            await self.whisper.generate_srt(
                audio_path=audio_path,
                output_path=srt_path
            )

            captioned_video = work_path / "captioned.mp4"
            await self.whisper.add_captions_to_video(
                video_path=combined_video,
                srt_path=srt_path,
                output_path=captioned_video
            )

            # 8. Add X handle overlay
            logger.info("Step 8: Adding overlay")
            overlay_image = work_path / "overlay.png"
            # Extract handle from URL
            handle = video_url.split("/")[3]  # Simplified extraction

            await self.overlay_gen.generate_x_handle_overlay(
                handle=handle,
                profile_image_url="",  # TODO: Get from X API
                view_count=100000,
                output_path=overlay_image
            )

            final_video = self.output_dir / f"{timestamp}_final.mp4"
            await self.ffmpeg.add_overlay(
                video_path=captioned_video,
                overlay_image=overlay_image,
                output_path=final_video,
                position="top-right"
            )

            logger.info(f"Content created successfully: {final_video}")
            return final_video

        except Exception as e:
            logger.error(f"Content creation failed: {e}")
            raise AutomationError(f"Failed to create content: {e}")

    async def publish_scheduled_content(self) -> int:
        """Publish all scheduled content.

        Returns:
            Number of items published
        """
        logger.info("Publishing scheduled content")

        try:
            # Get scheduled content
            content_items = await self.db.get_scheduled_content()

            if not content_items:
                logger.info("No scheduled content found")
                return 0

            published_count = 0

            for item in content_items:
                try:
                    # Generate platform-specific captions
                    platforms = item.get("platforms", settings.platforms)
                    script = item.get("script", "")

                    captions = await self.publisher.generate_captions(
                        script=script,
                        platforms=platforms
                    )

                    # Publish
                    video_path = Path(item["video_path"])
                    results = await self.publisher.publish(
                        video_path=video_path,
                        platforms=platforms,
                        captions=captions,
                        metadata=item.get("metadata", {})
                    )

                    # Update status
                    await self.db.update_status(
                        record_id=item["id"],
                        status="published",
                        metadata={"publish_results": results}
                    )

                    published_count += 1
                    logger.info(f"Published content: {item['id']}")

                except Exception as e:
                    logger.error(f"Failed to publish {item['id']}: {e}")
                    await self.db.update_status(
                        record_id=item["id"],
                        status="error",
                        metadata={"error": str(e)}
                    )

            logger.info(f"Published {published_count} items")
            return published_count

        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            raise AutomationError(f"Failed to publish content: {e}")

    async def run_full_pipeline(
        self,
        scrape: bool = True,
        create: bool = True,
        publish: bool = True
    ) -> Dict[str, Any]:
        """Run the complete automation pipeline.

        Args:
            scrape: Whether to run idea scraper
            create: Whether to create content
            publish: Whether to publish content

        Returns:
            Dictionary with pipeline results
        """
        logger.info("Starting full automation pipeline")

        results = {
            "scraped": 0,
            "created": 0,
            "published": 0,
            "errors": []
        }

        try:
            # Scrape ideas
            if scrape:
                try:
                    results["scraped"] = await self.run_idea_scraper()
                except Exception as e:
                    results["errors"].append(f"Scraping error: {e}")

            # Create content
            if create:
                # TODO: Implement batch content creation
                pass

            # Publish content
            if publish:
                try:
                    results["published"] = await self.publish_scheduled_content()
                except Exception as e:
                    results["errors"].append(f"Publishing error: {e}")

            logger.info(f"Pipeline completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise AutomationError(f"Pipeline execution failed: {e}")
