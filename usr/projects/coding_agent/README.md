# 🤖 AI Avatar Content Automation System

**Production-ready system for automated content creation and multi-platform publishing using AI avatars, voice cloning, and intelligent video processing.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

Automates the entire content creation pipeline:
1. **Scrapes** viral videos from X/Twitter
2. **Generates** AI-powered scripts  
3. **Creates** AI avatar videos with voice cloning
4. **Processes** videos with captions and overlays
5. **Publishes** to multiple platforms automatically

## ✨ Features

### Content Automation
- 🎬 AI Avatar Generation from images
- 🎙️ Voice Cloning with ElevenLabs
- 📝 AI Script Generation with GPT-4
- 🎨 Professional Video Processing with FFmpeg
- 📊 Automatic Caption Generation with Whisper

### Multi-Platform Publishing
- 📱 TikTok, 📺 YouTube Shorts, 📸 Instagram Reels, 👥 Facebook
- Platform-specific caption optimization
- Scheduled posting every 3 hours

## 📦 Prerequisites

### System Requirements
- Python 3.10+
- FFmpeg installed
- 4GB RAM minimum, 8GB recommended
- 50GB+ storage for video processing

### Required API Keys
1. **Airtable** - Database
2. **Apify** - X/Twitter scraping
3. **OpenAI** - Script generation
4. **ElevenLabs** - Voice generation
5. **Blotato** - Multi-platform publishing
6. **RenderForm** - Image overlays
7. **Wan Video** - Avatar animation

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/yourusername/content-automation.git
cd content-automation

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install openai-whisper

# Verify FFmpeg
ffmpeg -version
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 3. Airtable Setup

Create tables: **X Profiles**, **Ideas**, **Create**, **Avatars**, **Music**

See full schema in [Configuration](#configuration) section.

## 💻 Usage

### Basic Example

```python
import asyncio
from content_automation.pipeline.orchestrator import ContentAutomation

async def main():
    automation = ContentAutomation()

    # Scrape viral ideas
    ideas = await automation.run_idea_scraper()
    print(f"Scraped {ideas} ideas")

    # Create content
    video = await automation.create_content(
        video_url="https://x.com/user/status/123456"
    )
    print(f"Created: {video}")

    # Publish scheduled content
    published = await automation.publish_scheduled_content()
    print(f"Published {published} videos")

asyncio.run(main())
```

### Full Pipeline

```python
async def run_pipeline():
    automation = ContentAutomation()
    results = await automation.run_full_pipeline(
        scrape=True,
        create=True,
        publish=True
    )
    print(results)

asyncio.run(run_pipeline())
```

## 🏗️ Architecture

```
Content Automation System
├── Scraper (Apify) → Find viral X videos
├── Script Generator (OpenAI) → Create engaging scripts
├── Voice Generator (ElevenLabs) → Text-to-speech & cloning
├── Avatar Generator (Wan Video) → Lip-synced avatars
├── Video Processor (FFmpeg + Whisper) → Edit & caption
├── Publisher (Blotato) → Multi-platform posting
└── Database (Airtable) → Track everything
```

## 📁 Project Structure

```
content_automation/
├── config/          # Settings and configuration
├── core/            # Base classes and interfaces
├── clients/         # External API integrations
├── pipeline/        # Main orchestration logic
├── tools/           # FFmpeg and Whisper wrappers
├── workflows/       # N8N workflow templates
└── templates/       # Prompt templates
```

## ⚙️ Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Airtable
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_API_KEY=your_api_key

# OpenAI
OPENAI_API_KEY=sk-...

# ElevenLabs  
ELEVENLABS_API_KEY=your_key

# Content Settings
MIN_VIEWS=100000
MAX_VIDEO_AGE_DAYS=3
PUBLISH_INTERVAL_HOURS=3
```

### Airtable Schema

#### X Profiles Table
- `handle` (text) - X/Twitter handle
- `min_views` (number) - View threshold
- `active` (checkbox) - Enable monitoring

#### Ideas Table  
- `tweet_id` (text) - Unique ID
- `url` (URL) - Video link
- `views` (number) - View count
- `status` (select) - new/selected/rejected

#### Create Table
- `idea_id` (link) - Source idea
- `script` (long text) - Generated script
- `avatar_id` (link) - Avatar used
- `status` (select) - processing/review/scheduled/published
- `output_video` (attachment) - Final video

## 💰 Cost Analysis

### Per Video
- Avatar animation: $0.11 (one-time)
- Voice generation: ~$0.02
- Lip-sync: ~$0.05
- Scraping: ~$0.01
- **Total: ~$0.19 per video**

### Monthly Operating Costs
- N8N Hosting: $10-20/mo
- ElevenLabs: $11/mo (with cloning)
- Airtable: Free-$20/mo
- Apify: Free-$49/mo
- RenderForm: Free-$29/mo
- Blotato: Free-$15/mo
- **Total: $10-$145/mo**

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=content_automation

# Specific test
pytest tests/test_orchestrator.py
```

## 🔧 Troubleshooting

### FFmpeg not found
```bash
sudo apt-get install ffmpeg
```

### API rate limits
- Check your API usage dashboards
- Increase delays between requests
- Upgrade to higher tier plans

### Video processing fails
- Ensure sufficient disk space
- Check FFmpeg installation
- Verify video file formats

## 📚 Documentation

- [API Documentation](docs/API.md)
- [N8N Workflows](docs/N8N.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing Guide](CONTRIBUTING.md)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- OpenAI for GPT-4 and Whisper
- ElevenLabs for voice technology
- Apify for scraping infrastructure
- All open-source contributors

## 📞 Support

- Issues: [GitHub Issues](https://github.com/yourusername/content-automation/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/content-automation/discussions)
- Email: support@example.com

---

**Built with ❤️ for content creators**
