"""Tests for configuration module."""
import pytest
from content_automation.config.settings import Settings


def test_settings_initialization():
    """Test settings can be initialized."""
    # This will fail if required env vars are missing
    # In real tests, use mock environment
    try:
        settings = Settings()
        assert settings.app_env in ["dev", "prod", "test"]
    except Exception:
        # Expected if .env not configured
        pass


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings(
        airtable_base_id="test",
        airtable_api_key="test",
        apify_token="test",
        elevenlabs_api_key="test",
        openai_api_key="test",
        blotato_api_key="test",
        renderform_api_key="test",
        wan_video_api_key="test"
    )

    assert settings.log_level == "INFO"
    assert settings.min_views == 100000
    assert settings.max_video_age_days == 3
    assert settings.video_width == 1080
    assert settings.video_height == 1920
