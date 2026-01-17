#!/usr/bin/env python3
"""
Test Parallel Processing Performance
====================================
Test and benchmark parallel processing improvements.
"""

import sys
from pathlib import Path
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.dashboard.utils.parallel import (
    ParallelProcessor,
    parallel_download,
    parallel_calculation
)


def simulate_download(ticker: str) -> dict:
    """Simulate downloading data for a ticker."""
    time.sleep(0.1)  # Simulate network delay
    return {
        'ticker': ticker,
        'data': f"data_for_{ticker}",
        'status': 'success'
    }


def simulate_analysis(run_id: str) -> dict:
    """Simulate running analysis."""
    time.sleep(0.2)  # Simulate computation
    return {
        'run_id': run_id,
        'result': 'completed',
        'metrics': {'return': 0.15, 'sharpe': 1.2}
    }


def test_fundamentals_download():
    """Test fundamentals download performance."""
    print("\n" + "="*60)
    print("Testing Fundamentals Download Performance")
    print("="*60)
    
    tickers = [f"TICKER{i:03d}" for i in range(50)]
    
    # Sequential
    print("\n📊 Sequential Download:")
    start = time.time()
    sequential_results = []
    for ticker in tickers:
        result = simulate_download(ticker)
        sequential_results.append(result)
    sequential_time = time.time() - start
    print(f"   Time: {sequential_time:.2f}s")
    print(f"   Throughput: {len(tickers)/sequential_time:.2f} tickers/sec")
    
    # Parallel
    print("\n⚡ Parallel Download (8 workers):")
    start = time.time()
    parallel_results = parallel_download(
        tickers,
        simulate_download,
        batch_size=10,
        max_workers=8,
        delay_between_batches=0
    )
    parallel_time = time.time() - start
    print(f"   Time: {parallel_time:.2f}s")
    print(f"   Throughput: {len(tickers)/parallel_time:.2f} tickers/sec")
    
    # Speedup
    speedup = sequential_time / parallel_time
    print(f"\n🚀 Speedup: {speedup:.2f}x faster")
    print(f"   Time saved: {sequential_time - parallel_time:.2f}s")


def test_analysis_parallelization():
    """Test analysis parallelization performance."""
    print("\n" + "="*60)
    print("Testing Analysis Parallelization Performance")
    print("="*60)
    
    run_ids = [f"run_{i:03d}" for i in range(10)]
    
    # Sequential
    print("\n📊 Sequential Analysis:")
    start = time.time()
    sequential_results = []
    for run_id in run_ids:
        result = simulate_analysis(run_id)
        sequential_results.append(result)
    sequential_time = time.time() - start
    print(f"   Time: {sequential_time:.2f}s")
    
    # Parallel
    print("\n⚡ Parallel Analysis (4 workers):")
    start = time.time()
    analysis_funcs = [lambda rid=rid: simulate_analysis(rid) for rid in run_ids]
    parallel_results = parallel_calculation(analysis_funcs, max_workers=4)
    parallel_time = time.time() - start
    print(f"   Time: {parallel_time:.2f}s")
    
    # Speedup
    speedup = sequential_time / parallel_time
    print(f"\n🚀 Speedup: {speedup:.2f}x faster")
    print(f"   Time saved: {sequential_time - parallel_time:.2f}s")


def test_cache_performance():
    """Test cache performance."""
    print("\n" + "="*60)
    print("Testing Cache Performance")
    print("="*60)
    
    from src.app.dashboard.utils.cache import QueryCache, cached_query
    
    cache = QueryCache(default_ttl=60)
    
    @cached_query(ttl=60)
    def expensive_query(param):
        time.sleep(0.1)  # Simulate expensive operation
        return param * 2
    
    # First call (cache miss)
    print("\n📊 First Call (Cache Miss):")
    start = time.time()
    result1 = expensive_query(5)
    miss_time = time.time() - start
    print(f"   Time: {miss_time:.3f}s")
    print(f"   Result: {result1}")
    
    # Second call (cache hit)
    print("\n⚡ Second Call (Cache Hit):")
    start = time.time()
    result2 = expensive_query(5)
    hit_time = time.time() - start
    print(f"   Time: {hit_time:.3f}s")
    print(f"   Result: {result2}")
    
    # Speedup
    speedup = miss_time / hit_time if hit_time > 0 else float('inf')
    print(f"\n🚀 Cache Speedup: {speedup:.2f}x faster")
    
    # Cache stats
    from src.app.dashboard.utils.cache import get_cache_stats
    stats = get_cache_stats()
    print(f"\n📈 Cache Stats:")
    print(f"   Total Entries: {stats['total_entries']}")
    print(f"   Active Entries: {stats['active_entries']}")


def main():
    """Run all performance tests."""
    print("\n" + "="*60)
    print("Parallel Processing & Performance Optimization Tests")
    print("="*60)
    
    test_fundamentals_download()
    test_analysis_parallelization()
    test_cache_performance()
    
    print("\n" + "="*60)
    print("✅ All performance tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
