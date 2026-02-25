"""Pytest configuration and fixtures."""
import pytest
import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory for tests."""
    return tmp_path


@pytest.fixture
def mock_video_url():
    """Provide mock X video URL."""
    return "https://x.com/testuser/status/123456789"


@pytest.fixture
def mock_script():
    """Provide mock script text."""
    return "This is a test script for video content."
