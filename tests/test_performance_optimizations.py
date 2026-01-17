"""
Test Performance Optimizations
==============================
Test database optimizations, caching, and connection pooling.
"""

import pytest
import time
from pathlib import Path
import tempfile
import os

from src.analytics.models import get_db, DatabaseManager
from src.app.dashboard.utils.cache import QueryCache, cached_query, clear_cache, get_cache_stats


def test_query_cache_basic():
    """Test basic query cache functionality."""
    cache = QueryCache(default_ttl=60)
    
    # Set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    # Expired entry
    cache.set("key2", "value2", ttl=0.1)
    assert cache.get("key2") == "value2"
    time.sleep(0.2)
    assert cache.get("key2") is None


def test_cached_query_decorator():
    """Test cached_query decorator."""
    call_count = [0]
    
    @cached_query(ttl=60)
    def expensive_function(x):
        call_count[0] += 1
        return x * 2
    
    # First call - should execute
    result1 = expensive_function(5)
    assert result1 == 10
    assert call_count[0] == 1
    
    # Second call - should use cache
    result2 = expensive_function(5)
    assert result2 == 10
    assert call_count[0] == 1  # Should not increment
    
    # Different argument - should execute
    result3 = expensive_function(6)
    assert result3 == 12
    assert call_count[0] == 2


def test_cache_clear():
    """Test cache clearing."""
    cache = QueryCache()
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert cache.get("key1") == "value1"
    
    # Clear specific pattern
    cache.clear("key1")
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"  # Should still exist
    
    # Clear all
    cache.clear()
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_cache_stats():
    """Test cache statistics."""
    cache = QueryCache(default_ttl=60)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2", ttl=0.1)
    
    stats = cache.get_stats()
    assert stats['total_entries'] == 2
    assert stats['active_entries'] >= 1  # At least key1 should be active
    
    time.sleep(0.2)
    stats = cache.get_stats()
    assert stats['expired_entries'] >= 1


def test_database_connection_pooling():
    """Test database connection pooling."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create database manager
        db = DatabaseManager(db_path)
        
        # Get multiple sessions (should use pool)
        session1 = db.get_session()
        session2 = db.get_session()
        
        # Both should work
        assert session1 is not None
        assert session2 is not None
        
        # Close sessions
        session1.close()
        session2.close()
        
        # Cleanup
        db.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_database_indexes():
    """Test that database indexes exist."""
    from src.analytics.models import Run, StockScore
    
    # Check that indexes are defined
    assert hasattr(Run, '__table_args__')
    table_args = Run.__table_args__
    
    # Should have indexes
    indexes = [arg for arg in table_args if hasattr(arg, 'name')]
    assert len(indexes) > 0
    
    # Check StockScore indexes
    assert hasattr(StockScore, '__table_args__')


@pytest.mark.skip(reason="Requires actual database")
def test_query_performance():
    """Test query performance with indexes."""
    db = get_db()
    session = db.get_session()
    
    try:
        from src.analytics.models import Run
        
        # This query should use the index on created_at
        start = time.time()
        runs = session.query(Run).order_by(Run.created_at.desc()).limit(100).all()
        query_time = time.time() - start
        
        # Should be fast (< 100ms for indexed query)
        assert query_time < 0.1
    finally:
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
