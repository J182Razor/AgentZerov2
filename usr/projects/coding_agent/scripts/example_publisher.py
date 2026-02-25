#!/usr/bin/env python3
"""Example: Publish scheduled content to platforms."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from content_automation.pipeline.orchestrator import ContentAutomation
from content_automation.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Publish scheduled content."""
    logger.info("Starting publisher example")

    try:
        automation = ContentAutomation()

        print("
📤 Publishing scheduled content...")
        count = await automation.publish_scheduled_content()

        logger.info(f"✅ Published {count} items")
        print(f"
🎉 Successfully published {count} videos!")

        if count == 0:
            print("
No scheduled content found.")
            print("Mark videos as 'scheduled' in Airtable to publish them.")

    except Exception as e:
        logger.error(f"Publishing failed: {e}")
        print(f"
❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
