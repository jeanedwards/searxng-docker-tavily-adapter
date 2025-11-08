# Testing Raw Content Feature

## Overview
The `/search` endpoint now uses Crawl4AI for more reliable raw content scraping with detailed error logging.

## Testing Steps

### 1. Start the services
```bash
docker compose up -d
```

### 2. Test without raw content (baseline)
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python web scraping",
    "max_results": 3,
    "include_raw_content": false
  }'
```

### 3. Test with raw content (new feature)
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python web scraping",
    "max_results": 3,
    "include_raw_content": true
  }'
```

### 4. Check the logs for scraping statistics
```bash
docker compose logs -f adapter
```

Look for log entries like:
```
Raw content scraping: 3/3 successful, 0 failed. Errors: {}
```

Or if some failed:
```
Raw content scraping: 2/3 successful, 1 failed. Errors: {'timeout': 1}
```

## Expected Results

### Success Indicators
- The `raw_content` field in each result should contain markdown-formatted content
- Logs should show successful scraping counts
- Content should be truncated to 2500 characters max (with "..." if truncated)

### Improved Reliability
- JavaScript-rendered pages now work (Playwright browser automation)
- Detailed error logging shows why specific pages failed
- Common error types: `timeout`, `no_content`, `crawl_failed`, `unknown_error`

## Configuration

Edit `config.yaml` to tune scraping behavior:

```yaml
adapter:
  scraper:
    timeout: 10  # Timeout per page in seconds
    max_content_length: 2500  # Max characters in raw_content
    user_agent: "Mozilla/5.0 (compatible; TavilyBot/1.0)"
```

## Troubleshooting

### Issue: All pages timeout
- Increase `scraper.timeout` in config.yaml
- Check network connectivity from adapter container

### Issue: No content extracted
- Check logs for specific error messages
- Verify pages are not blocking automated access
- Try different URLs

### Issue: Slow performance
- Reduce `max_results` to scrape fewer pages
- Set `include_raw_content: false` when not needed
- Adjust `scraper.timeout` to fail faster

