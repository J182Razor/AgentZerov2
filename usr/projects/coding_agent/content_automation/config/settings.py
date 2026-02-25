"""Configuration management using pydantic-settings."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_env: str = "dev"
    log_level: str = "INFO"
    debug: bool = False

    # Airtable
    airtable_base_id: str
    airtable_api_key: str
    airtable_x_profiles_table: str = "X Profiles"
    airtable_ideas_table: str = "Ideas"
    airtable_create_table: str = "Create"
    airtable_avatars_table: str = "Avatars"
    airtable_music_table: str = "Music"

    # Apify
    apify_token: str
    apify_actor_id: str = "apify/twitter-scraper"

    # ElevenLabs
    elevenlabs_api_key: str
    elevenlabs_model: str = "eleven_multilingual_v2"

    # OpenAI (for script generation)
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"

    # Blotato
    blotato_api_key: str
    blotato_base_url: str = "https://api.blotato.com/v1"

    # RenderForm
    renderform_api_key: str
    renderform_template_id: Optional[str] = None

    # Wan Video (Avatar Animation)
    wan_video_api_key: str
    wan_video_model: str = "wan-video-2.2"

    # Whisper (Captions)
    whisper_model: str = "base"

    # Paths
    work_dir: str = "./work"
    temp_dir: str = "./temp"
    output_dir: str = "./output"

    # Video Processing
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30
    avatar_duration: int = 3  # seconds

    # Content Filtering
    min_views: int = 100000
    max_video_age_days: int = 3

    # Publishing
    publish_interval_hours: int = 3
    scrape_time: str = "08:00"  # Daily scrape time

    # Platform Settings
    platforms: list[str] = ["tiktok", "youtube", "instagram", "facebook"]


settings = Settings()
