#!/usr/bin/env python3
"""Example: Create content from X video URL."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from content_automation.pipeline.orchestrator import ContentAutomation
from content_automation.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Create content from X video."""
    if len(sys.argv) < 2:
        print("Usage: python example_creator.py <X_VIDEO_URL>")
        print("Example: python example_creator.py https://x.com/user/status/123456")
        sys.exit(1)

    video_url = sys.argv[1]

    logger.info(f"Creating content from: {video_url}")

    try:
        automation = ContentAutomation()

        print("
🎬 Creating AI avatar video...")
        print("This may take 2-5 minutes...
")

        video_path = await automation.create_content(
            video_url=video_url
        )

        logger.info(f"✅ Video created: {video_path}")
        print(f"
🎉 Success! Video created at:")
        print(f"   {video_path}")
        print("
Next steps:")
        print("1. Review the video")
        print("2. Mark as 'scheduled' in Airtable to publish")

    except Exception as e:
        logger.error(f"Content creation failed: {e}")
        print(f"
❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
