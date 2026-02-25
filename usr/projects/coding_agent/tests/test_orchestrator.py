"""Tests for pipeline orchestrator."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from content_automation.pipeline.orchestrator import ContentAutomation


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test orchestrator can be initialized."""
    with patch('content_automation.pipeline.orchestrator.AirtableClient'):
        with patch('content_automation.pipeline.orchestrator.ApifyClient'):
            with patch('content_automation.pipeline.orchestrator.OpenAIClient'):
                with patch('content_automation.pipeline.orchestrator.ElevenLabsClient'):
                    with patch('content_automation.pipeline.orchestrator.BlototoClient'):
                        with patch('content_automation.pipeline.orchestrator.RenderFormClient'):
                            automation = ContentAutomation()

                            assert automation.db is not None
                            assert automation.scraper is not None
                            assert automation.script_gen is not None


@pytest.mark.asyncio
async def test_run_idea_scraper():
    """Test idea scraper workflow."""
    with patch('content_automation.pipeline.orchestrator.AirtableClient') as MockDB:
        with patch('content_automation.pipeline.orchestrator.ApifyClient') as MockScraper:
            # Setup mocks
            mock_db = MockDB.return_value
            mock_db.get_profiles = AsyncMock(return_value=[
                {"id": "rec1", "handle": "testuser", "min_views": 100000}
            ])
            mock_db.save_idea = AsyncMock(return_value="rec123")

            mock_scraper = MockScraper.return_value
            mock_scraper.scrape_videos = AsyncMock(return_value=[
                {
                    "tweet_id": "123",
                    "url": "https://x.com/test/status/123",
                    "views": 150000
                }
            ])

            # Patch other clients
            with patch('content_automation.pipeline.orchestrator.OpenAIClient'):
                with patch('content_automation.pipeline.orchestrator.ElevenLabsClient'):
                    with patch('content_automation.pipeline.orchestrator.BlototoClient'):
                        with patch('content_automation.pipeline.orchestrator.RenderFormClient'):
                            automation = ContentAutomation()
                            count = await automation.run_idea_scraper()

                            assert count == 1
                            mock_db.get_profiles.assert_called_once()
                            mock_scraper.scrape_videos.assert_called_once()
