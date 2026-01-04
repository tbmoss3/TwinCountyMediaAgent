# TwinCountyMediaAgent

A Python-based News & Community Newsletter Agent for Nash, Edgecombe, and Wilson counties in North Carolina. Deployed on Railway.app.

## Features

- **Automated News Scraping**: Collects content from local news sites using Crawl4AI
- **Government Meeting Monitoring**: Tracks city/county council meeting minutes
- **Social Media Integration**: Fetches posts from local businesses via Bright Data API
- **AI Content Filtering**: Uses Claude to filter for positive/event-based content
- **Newsletter Generation**: Auto-generates weekly newsletters with:
  - Featured top story (200-word AI-written highlight)
  - Aggregated news links by county
  - Community calendar with upcoming events
- **Mailchimp Delivery**: Preview-then-send workflow with manager approval

## Quick Start

### Local Development

1. Clone and install dependencies:
```bash
cd TwinCountyMediaAgent
pip install -r requirements.txt
playwright install chromium
```

2. Copy environment template and configure:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start PostgreSQL (or use Railway's PostgreSQL):
```bash
# Set DATABASE_URL in .env
```

4. Run the application:
```bash
python main.py
```

### Railway Deployment

1. Create a new project on [Railway.app](https://railway.app)
2. Add PostgreSQL service
3. Deploy from GitHub or CLI
4. Set environment variables in Railway dashboard

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Claude API key |
| `BRIGHT_DATA_API_KEY` | Bright Data API key (optional) |
| `MAILCHIMP_API_KEY` | Mailchimp API key |
| `MAILCHIMP_SERVER_PREFIX` | e.g., `us6` |
| `MAILCHIMP_LIST_ID` | Audience list ID |
| `MANAGER_EMAIL` | Email for draft previews |

See `.env.example` for full list.

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Health with database status

### Admin
- `POST /api/v1/admin/scrape/trigger` - Trigger content scraping
- `POST /api/v1/admin/filter/trigger` - Trigger content filtering
- `POST /api/v1/admin/newsletter/generate` - Generate newsletter
- `POST /api/v1/admin/newsletter/send` - Send pending newsletter
- `GET /api/v1/admin/content/pending` - View pending content
- `GET /api/v1/admin/content/approved` - View approved content
- `GET /api/v1/admin/stats/overview` - System statistics

## Schedule

- **Content Scraping**: Every 6 hours
- **Content Filtering**: 30 minutes after each scrape
- **Newsletter Generation**: Thursday 8:00 AM (configurable)
- **Newsletter Send**: 2 hours after preview (or manual trigger)

## Project Structure

```
TwinCountyMediaAgent/
├── api/                  # FastAPI routes
├── config/               # Settings and source configs
├── database/             # Database connection and schema
│   └── repositories/     # Data access layer
├── scrapers/             # Content scrapers
├── services/             # Business logic
├── templates/            # Email templates
├── main.py               # Entry point
├── Dockerfile            # Container config
└── railway.toml          # Railway config
```

## Adding Sources

Edit `config/sources.py` to add new news sites, social accounts, or government sources.

## License

Private - All rights reserved.
