#!/usr/bin/env python3
"""Example: Scrape viral video ideas from X/Twitter."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from content_automation.pipeline.orchestrator import ContentAutomation
from content_automation.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Run the idea scraper."""
    logger.info("Starting idea scraper example")

    try:
        # Initialize automation
        automation = ContentAutomation()

        # Run scraper
        logger.info("Scraping viral video ideas...")
        count = await automation.run_idea_scraper()

        logger.info(f"✅ Successfully scraped {count} viral video ideas")
        print(f"
🎉 Scraped {count} ideas!")
        print("
Check your Airtable 'Ideas' table to review them.")

    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        print(f"
❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
