"""
Test Parallel Processing
========================
Test parallel processing utilities and integration.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from src.app.dashboard.utils.parallel import (
    ParallelProcessor,
    parallel_download,
    parallel_analysis,
    parallel_calculation,
    parallel_map,
    ParallelPerformanceMonitor
)


def test_parallel_processor_basic():
    """Test basic parallel processing."""
    processor = ParallelProcessor(max_workers=2, show_progress=False)
    
    def square(x):
        return x * x
    
    items = [1, 2, 3, 4, 5]
    results = processor.process_map(items, square)
    
    assert len(results) == 5
    assert results == [1, 4, 9, 16, 25]


def test_parallel_processor_with_errors():
    """Test parallel processing with errors."""
    processor = ParallelProcessor(max_workers=2, show_progress=False)
    
    def process_item(x):
        if x == 3:
            raise ValueError("Test error")
        return x * 2
    
    items = [1, 2, 3, 4, 5]
    results = processor.process_batch(items, process_item)
    
    assert len(results) == 5
    # Check successful results
    successes = [r for _, r, e in results if e is None]
    assert successes == [2, 4, 8, 10]
    # Check errors
    errors = [e for _, _, e in results if e is not None]
    assert len(errors) == 1
    assert "Test error" in str(errors[0])


def test_parallel_download():
    """Test parallel download function."""
    def download_item(item):
        time.sleep(0.01)  # Simulate download
        return f"downloaded_{item}"
    
    items = ["item1", "item2", "item3"]
    results = parallel_download(
        items,
        download_item,
        batch_size=2,
        max_workers=2,
        delay_between_batches=0
    )
    
    assert len(results) == 3
    # Check all items were processed
    processed_items = [item for item, _, _ in results]
    assert set(processed_items) == set(items)


def test_parallel_calculation():
    """Test parallel calculation."""
    def calc1():
        time.sleep(0.01)
        return 10
    
    def calc2():
        time.sleep(0.01)
        return 20
    
    def calc3():
        time.sleep(0.01)
        return 30
    
    calculations = [calc1, calc2, calc3]
    results = parallel_calculation(calculations, max_workers=3)
    
    assert len(results) == 3
    assert set(results) == {10, 20, 30}


def test_parallel_map():
    """Test parallel map function."""
    def double(x):
        return x * 2
    
    items = [1, 2, 3, 4, 5]
    results = parallel_map(items, double, max_workers=2)
    
    assert results == [2, 4, 6, 8, 10]


def test_performance_monitor():
    """Test performance monitoring."""
    monitor = ParallelPerformanceMonitor()
    monitor.start()
    
    time.sleep(0.1)
    
    monitor.record_result("item1", 0.05, True)
    monitor.record_result("item2", 0.03, True)
    monitor.record_result("item3", 0.02, False)
    
    monitor.stop()
    
    stats = monitor.get_stats()
    assert stats['total_items'] == 3
    assert stats['successful'] == 2
    assert stats['failed'] == 1
    assert stats['total_duration'] > 0
    assert stats['items_per_second'] > 0


def test_parallel_processing_performance():
    """Test that parallel processing is faster than sequential."""
    def slow_operation(x):
        time.sleep(0.1)
        return x * 2
    
    items = list(range(5))
    
    # Sequential
    start = time.time()
    sequential_results = [slow_operation(x) for x in items]
    sequential_time = time.time() - start
    
    # Parallel
    start = time.time()
    parallel_results = parallel_map(items, slow_operation, max_workers=5)
    parallel_time = time.time() - start
    
    # Results should be the same
    assert sequential_results == parallel_results
    
    # Parallel should be faster (at least 2x for 5 items)
    # Note: This might not always be true due to overhead, but should be generally true
    assert parallel_time < sequential_time * 0.8  # Allow some overhead


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
