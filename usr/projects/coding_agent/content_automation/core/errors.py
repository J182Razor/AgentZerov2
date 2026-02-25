"""Custom exception classes for the automation system."""


class AutomationError(Exception):
    """Base exception for all automation errors."""
    pass


class ExternalAPIError(AutomationError):
    """Raised when external API calls fail."""

    def __init__(self, service: str, message: str, status_code: int = None):
        self.service = service
        self.status_code = status_code
        super().__init__(f"{service} API error: {message}")


class ValidationError(AutomationError):
    """Raised when data validation fails."""
    pass


class VideoProcessingError(AutomationError):
    """Raised when video processing fails."""
    pass


class ScrapingError(AutomationError):
    """Raised when content scraping fails."""
    pass


class PublishingError(AutomationError):
    """Raised when content publishing fails."""
    pass


class AvatarGenerationError(AutomationError):
    """Raised when avatar generation fails."""
    pass


class VoiceGenerationError(AutomationError):
    """Raised when voice generation fails."""
    pass
