#!/usr/bin/env python3
"""Example: Run the complete automation pipeline."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from content_automation.pipeline.orchestrator import ContentAutomation
from content_automation.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Run full automation pipeline."""
    logger.info("Starting full pipeline")

    try:
        automation = ContentAutomation()

        print("
🚀 Running full automation pipeline...")
        print("
Steps:")
        print("1. Scrape viral video ideas")
        print("2. Create content (if enabled)")
        print("3. Publish scheduled content")
        print("
This may take several minutes...
")

        results = await automation.run_full_pipeline(
            scrape=True,
            create=False,  # Set to True to auto-create content
            publish=True
        )

        print("
" + "="*50)
        print("📊 Pipeline Results")
        print("="*50)
        print(f"Ideas scraped: {results['scraped']}")
        print(f"Videos created: {results['created']}")
        print(f"Videos published: {results['published']}")

        if results['errors']:
            print(f"
⚠️  Errors encountered:")
            for error in results['errors']:
                print(f"  - {error}")
        else:
            print("
✅ No errors!")

        print("="*50)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"
❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
