# Migration Guide: v3.11

> [← Back to Documentation Index](README.md)

**Upgrading from v3.10.x to v3.11.x**

## Overview

Version 3.11 introduces significant performance improvements, lazy loading capabilities, and advanced optimizations. This guide will help you migrate smoothly.

## What's New in v3.11

### Performance Improvements

1. **Lazy Loading**
   - Charts load on-demand for faster page loads
   - Large dataframes show previews with "Load Full Data" options
   - Progressive chart loading (sequential or batch)

2. **Query Caching**
   - Automatic caching of frequently accessed queries (5-minute TTL)
   - Data compression for cached results (20-40% memory savings)
   - Cache statistics and management tools

3. **Chart Optimization**
   - Automatic downsampling for charts with 1000+ data points
   - Improved rendering performance for large datasets
   - Configurable optimization settings

4. **Request Batching**
   - API requests automatically batched
   - Rate limit compliance
   - Parallel execution for improved performance

### New Components

- `lazy_dataframes.py`: Lazy loading for large tables
- `progressive_charts.py`: Progressive chart loading
- `request_batching.py`: API request batching utilities
- Enhanced `cache.py`: Data compression support

## Migration Steps

### Step 1: Backup Your Data

```bash
# Backup database
cp data/analysis.db data/analysis.db.backup

# Backup configuration
cp config/config.yaml config/config.yaml.backup
cp config/watchlists.yaml config/watchlists.yaml.backup
```

### Step 2: Update Dependencies

```bash
# Activate virtual environment
source ~/venv/bin/activate  # or your venv path

# Update requirements
pip install -r requirements.txt --upgrade
```

**New Dependencies:**
- No new external dependencies required
- Uses standard library (`gzip`, `pickle`) for compression

### Step 3: Verify Installation

```bash
# Test imports
python -c "from src.app.dashboard.components.lazy_dataframes import lazy_dataframe"
python -c "from src.app.dashboard.utils.request_batching import RequestBatcher"
python -c "from src.app.dashboard.utils.cache import QueryCache"
```

### Step 4: Clear Old Cache (Optional)

If you have custom caching code, you may need to clear old cache:

```python
from src.app.dashboard.utils.cache import clear_cache
clear_cache()  # Clears all cached data
```

### Step 5: Test Performance Features

1. **Test Lazy Loading:**
   - Go to Portfolio Analysis page
   - Select a run with large dataset
   - Enable "Lazy Load" mode
   - Verify charts load on-demand

2. **Test Query Caching:**
   - Go to Performance Monitoring page
   - Check "Cache Performance" tab
   - Verify cache statistics are displayed

3. **Test Chart Optimization:**
   - Create a run with 1000+ data points
   - View charts in Portfolio Analysis
   - Verify charts render quickly (downsampling applied)

## Breaking Changes

### None. Version 3.11 is fully backward compatible.

All new features are opt-in or automatic optimizations that don't change existing behavior.

## Configuration Changes

### Optional: Configure Cache TTL

Edit `src/app/dashboard/utils/cache.py`:

```python
# Default TTL is 300 seconds (5 minutes)
_global_cache = QueryCache(default_ttl=600)  # Change to 10 minutes
```

### Optional: Configure Request Batching

Edit `src/app/dashboard/utils/request_batching.py`:

```python
# Default batch size is 10
batcher = RequestBatcher(
    batch_size=20,  # Increase batch size
    rate_limit_per_second=5.0  # Set rate limit
)
```

### Optional: Configure Chart Optimization

Edit `src/app/dashboard/components/charts.py`:

```python
# Default max_points is 1000
def create_equity_curve(..., max_points=2000, optimize=True):
    # Increase max_points for higher resolution
```

## Performance Expectations

### Before v3.11

- Page load time: 3-5 seconds (large datasets)
- Chart rendering: 2-4 seconds (1000+ points)
- Memory usage: High for large datasets

### After v3.11

- Page load time: 1-2 seconds (40-60% improvement)
- Chart rendering: <1 second (with optimization)
- Memory usage: 20-40% reduction (with compression)

## Troubleshooting

### Issue: Charts not loading

**Solution:**
- Check browser console for errors
- Verify data is available for the run
- Try disabling lazy loading (use "All Charts" mode)

### Issue: Cache not working

**Solution:**
- Check cache statistics in Performance Monitoring
- Clear cache and retry
- Verify cache TTL settings

### Issue: Slow performance

**Solution:**
1. Enable lazy loading for charts
2. Use pagination for large tables
3. Clear cache if it's too large
4. Check Performance Monitoring for bottlenecks

### Issue: API rate limits

**Solution:**
- Request batching is automatic
- Adjust `rate_limit_per_second` in `request_batching.py`
- Check API provider limits

## Rollback Instructions

If you need to rollback to v3.10.x:

```bash
# Restore database backup
cp data/analysis.db.backup data/analysis.db

# Restore configuration
cp config/config.yaml.backup config/config.yaml

# Revert code (if using git)
git checkout v3.10.0  # or your previous version
```

## Support

For issues or questions:
1. Check the [FAQ](faq.md)
2. Review [User Guide](user-guide.md)
3. Check [Performance Monitoring](performance-monitoring.md) page in dashboard

## Next Steps

After migration:
1. Test all workflows
2. Monitor performance in Performance Monitoring page
3. Adjust cache/optimization settings as needed
4. Enjoy faster page loads! 🚀

---

**Last Updated:** 2026-01-17  
**Version:** 3.11.2

---

## See Also

- [Full v3.11 release notes](v3.11-complete-summary.md)
- [Post-v3.11 priorities](next-steps-v3.11.md)
- [Configuration reference](configuration-cli.md)
