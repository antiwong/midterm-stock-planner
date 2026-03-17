# API Configuration

> [← Back to Documentation Index](README.md)

This document describes how to configure API keys and external services for the Mid-term Stock Planner.

## Overview

The system integrates with several external APIs:

| API | Purpose | Required |
|-----|---------|----------|
| Gemini | AI-powered insights | Optional |
| NewsAPI | News sentiment analysis | Optional |
| Alpha Vantage | Market data | Optional |
| OpenAI | Alternative LLM | Optional |

## Environment Setup

### .env File

Create a `.env` file in the project root:

```bash
# Required for AI insights
GEMINI_API_KEY=your-gemini-api-key

# Optional - for news sentiment
NEWSAPI_KEY=your-newsapi-key
ALPHA_VANTAGE_API_KEY=your-alphavantage-key

# Optional - alternative LLM
OPENAI_API_KEY=your-openai-key
```

### Loading Keys

Keys are automatically loaded when importing config:

```python
from src.config.api_keys import load_api_keys

# Load all keys from .env
keys = load_api_keys()
print(f"Loaded {len(keys)} API keys")
```

Or via shell script:

```bash
source scripts/setup_env.sh
```

## Obtaining API Keys

### Gemini (Google AI)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with Google account
3. Create new API key
4. Copy key to `.env` as `GEMINI_API_KEY`

**Free tier:** 60 requests/minute, 1M tokens/day

### NewsAPI

1. Go to [NewsAPI](https://newsapi.org/)
2. Sign up for free account
3. Get API key from dashboard
4. Copy to `.env` as `NEWSAPI_KEY`

**Free tier:** 100 requests/day, 1 month history

### Alpha Vantage

1. Go to [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
2. Request free API key
3. Copy to `.env` as `ALPHA_VANTAGE_API_KEY`

**Free tier:** 5 requests/minute, 500 requests/day

### OpenAI (Optional)

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create account and add payment method
3. Generate API key
4. Copy to `.env` as `OPENAI_API_KEY`

**Note:** OpenAI requires payment method

## API Key Module

### Location

```
src/config/api_keys.py
```

### Functions

```python
from src.config.api_keys import (
    load_api_keys,
    get_api_key_status,
    test_api_connections,
)

# Load keys from .env
keys = load_api_keys()

# Check which keys are set
status = get_api_key_status()
# {
#     'GEMINI_API_KEY': True,
#     'NEWSAPI_KEY': False,
#     ...
# }

# Test connections
results = test_api_connections()
# {
#     'Gemini': {'status': 'OK', 'message': 'Connected'},
#     'NewsAPI': {'status': 'MISSING', 'message': 'Key not set'},
# }
```

### Usage in Code

```python
import os
from src.config.api_keys import load_api_keys

# Ensure keys are loaded
load_api_keys()

# Access keys via environment
gemini_key = os.environ.get('GEMINI_API_KEY')
if gemini_key:
    # Use Gemini API
    pass
```

## Configuration File

Keys can also be referenced in `config/config.yaml`:

```yaml
api:
  gemini:
    enabled: true
    model: gemini-2.0-flash
  
  news:
    enabled: true
    sources:
      - newsapi
      - alphavantage
```

## Security Best Practices

### DO

✅ Store keys in `.env` file (gitignored)
✅ Use environment variables
✅ Rotate keys periodically
✅ Use minimal required permissions

### DON'T

❌ Commit keys to git
❌ Share keys in plain text
❌ Use production keys in development
❌ Log API keys

## Troubleshooting

### Key not loading

1. Check `.env` file exists in project root
2. Verify no quotes around values:
   ```bash
   # Correct
   GEMINI_API_KEY=abc123
   
   # Wrong
   GEMINI_API_KEY="abc123"
   ```
3. Run `source scripts/setup_env.sh`

### API returning 401

- Verify key is correct
- Check key hasn't expired
- Verify key has required permissions

### Rate limiting (429)

- Reduce request frequency
- Implement exponential backoff
- Upgrade to paid tier if needed

### Quota exceeded

- Wait for quota reset
- Check usage dashboard
- Consider caching responses

## Testing Connections

Run the API test script:

```bash
cd midterm-stock-planner
source ~/venv/bin/activate
python -c "
from src.config.api_keys import load_api_keys, test_api_connections
load_api_keys()
results = test_api_connections()
for api, result in results.items():
    print(f'{api}: {result[\"status\"]}')
"
```

Expected output:
```
NewsAPI: OK
Gemini: OK
Alpha Vantage: OK
OpenAI: QUOTA_EXCEEDED  # or OK/MISSING
```

## API Usage in Features

### AI Insights (Gemini)

```python
from src.analytics.ai_insights import AIInsightsGenerator

# Automatically uses GEMINI_API_KEY
generator = AIInsightsGenerator()
if generator.is_available:
    insights = generator.generate_portfolio_insights(...)
```

### News Sentiment (NewsAPI)

```python
from src.sentiment.analyzer import SentimentAnalyzer

# Uses NEWSAPI_KEY
analyzer = SentimentAnalyzer()
sentiment = analyzer.analyze("AAPL")
```

### Fundamental Data (Alpha Vantage)

```python
from src.fundamental.data_fetcher import FundamentalDataFetcher

# Uses ALPHA_VANTAGE_API_KEY
fetcher = FundamentalDataFetcher()
fundamentals = fetcher.fetch("AAPL")
```

## Rate Limit Handling

The system implements automatic rate limiting:

```python
import time
from functools import wraps

def rate_limited(max_per_minute):
    min_interval = 60.0 / max_per_minute
    last_call = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = func(*args, **kwargs)
            last_call[0] = time.time()
            return result
        return wrapper
    return decorator
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | None |
| `NEWSAPI_KEY` | NewsAPI.org API key | None |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | None |
| `OPENAI_API_KEY` | OpenAI API key | None |
| `DATABASE_PATH` | SQLite database path | `data/analysis.db` |

---

## See Also

- [Configuration and CLI](configuration-cli.md)
- [Sentiment analysis (uses Gemini API)](sentiment.md)
- [AI insights (uses Gemini API)](ai-insights.md)
- [Data provider options](data-providers-guide.md)
