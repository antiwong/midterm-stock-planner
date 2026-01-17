#!/usr/bin/env python3
"""
Core Features Validation
========================
Validate core features without requiring full dashboard imports.
"""

import sys
from pathlib import Path
import traceback

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_utils_imports():
    """Test utils module imports directly."""
    print("\n" + "="*60)
    print("Testing Utils Module Imports")
    print("="*60)
    
    try:
        # Import modules directly without going through package __init__
        import importlib.util
        
        base_path = Path(__file__).parent.parent / "src" / "app" / "dashboard" / "utils"
        
        # Test parallel module
        parallel_path = base_path / "parallel.py"
        spec = importlib.util.spec_from_file_location("parallel", parallel_path)
        parallel_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parallel_mod)
        assert hasattr(parallel_mod, 'ParallelProcessor')
        print("✅ ParallelProcessor import works")
        
        # Test cache module
        cache_path = base_path / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_mod)
        assert hasattr(cache_mod, 'QueryCache')
        print("✅ QueryCache import works")
        
        # Test retry module
        retry_path = base_path / "retry.py"
        spec = importlib.util.spec_from_file_location("retry", retry_path)
        retry_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retry_mod)
        assert hasattr(retry_mod, 'retry_network')
        print("✅ retry_network import works")
        
        # Test data_validation module
        validation_path = base_path / "data_validation.py"
        spec = importlib.util.spec_from_file_location("data_validation", validation_path)
        validation_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validation_mod)
        assert hasattr(validation_mod, 'DataQualityChecker')
        print("✅ DataQualityChecker import works")
        
        return True
    except Exception as e:
        print(f"❌ Utils imports failed: {e}")
        traceback.print_exc()
        return False


def test_parallel_processing():
    """Test parallel processing functionality."""
    print("\n" + "="*60)
    print("Testing Parallel Processing")
    print("="*60)
    
    try:
        import importlib.util
        parallel_path = Path(__file__).parent.parent / "src" / "app" / "dashboard" / "utils" / "parallel.py"
        spec = importlib.util.spec_from_file_location("parallel", parallel_path)
        parallel_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parallel_mod)
        
        ParallelProcessor = parallel_mod.ParallelProcessor
        parallel_map = parallel_mod.parallel_map
        parallel_calculation = parallel_mod.parallel_calculation
        import time
        
        # Test parallel_map
        def square(x):
            time.sleep(0.01)
            return x * x
        
        items = [1, 2, 3, 4, 5]
        results = parallel_map(items, square, max_workers=3)
        # Results may not be in order with parallel processing, so check values
        assert sorted(results) == [1, 4, 9, 16, 25], f"Expected [1,4,9,16,25], got {results}"
        print("✅ parallel_map works")
        
        # Test parallel_calculation
        def calc1():
            return 10
        def calc2():
            return 20
        
        results = parallel_calculation([calc1, calc2], max_workers=2)
        assert set(results) == {10, 20}
        print("✅ parallel_calculation works")
        
        # Test ParallelProcessor
        processor = ParallelProcessor(max_workers=2, show_progress=False)
        results = processor.process_map([1, 2, 3], square)
        assert set(results) == {1, 4, 9}  # Order may vary with parallel processing
        print("✅ ParallelProcessor works")
        
        return True
    except Exception as e:
        print(f"❌ Parallel processing test failed: {e}")
        traceback.print_exc()
        return False


def test_query_cache():
    """Test query caching."""
    print("\n" + "="*60)
    print("Testing Query Cache")
    print("="*60)
    
    try:
        import importlib.util
        cache_path = Path(__file__).parent.parent / "src" / "app" / "dashboard" / "utils" / "cache.py"
        spec = importlib.util.spec_from_file_location("cache", cache_path)
        cache_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cache_mod)
        
        QueryCache = cache_mod.QueryCache
        cached_query = cache_mod.cached_query
        get_cache_stats = cache_mod.get_cache_stats
        import time
        
        cache = QueryCache(default_ttl=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        print("✅ Cache set/get works")
        
        cache.set("key2", "value2", ttl=0.1)
        time.sleep(0.2)
        assert cache.get("key2") is None
        print("✅ Cache TTL works")
        
        call_count = [0]
        @cached_query(ttl=1)
        def expensive():
            call_count[0] += 1
            return 42
        
        expensive()
        expensive()
        assert call_count[0] == 1
        print("✅ @cached_query decorator works")
        
        stats = get_cache_stats()
        assert 'total_entries' in stats
        print("✅ Cache stats work")
        
        return True
    except Exception as e:
        print(f"❌ Query cache test failed: {e}")
        traceback.print_exc()
        return False


def test_retry_logic():
    """Test retry logic."""
    print("\n" + "="*60)
    print("Testing Retry Logic")
    print("="*60)
    
    try:
        import importlib.util
        retry_path = Path(__file__).parent.parent / "src" / "app" / "dashboard" / "utils" / "retry.py"
        spec = importlib.util.spec_from_file_location("retry", retry_path)
        retry_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retry_mod)
        
        retry_network = retry_mod.retry_network
        
        call_count = [0]
        
        # retry_network is a pre-configured decorator, use it directly
        @retry_network
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Simulated error")
            return "success"
        
        result = flaky()
        assert result == "success"
        assert call_count[0] >= 1  # Should retry at least once
        print("✅ Retry logic works")
        
        return True
    except Exception as e:
        print(f"❌ Retry logic test failed: {e}")
        traceback.print_exc()
        return False


def test_price_download_parallel():
    """Test that price download has parallel processing."""
    print("\n" + "="*60)
    print("Testing Price Download Parallel Processing")
    print("="*60)
    
    try:
        # Check if download_prices.py has parallel parameter
        download_script = Path(__file__).parent / "download_prices.py"
        if download_script.exists():
            content = download_script.read_text()
            if "parallel=True" in content or "parallel: bool" in content:
                print("✅ Price download has parallel parameter")
                return True
            else:
                print("⚠️  Price download parallel parameter not found")
                return False
        else:
            print("⚠️  download_prices.py not found")
            return False
    except Exception as e:
        print(f"❌ Price download test failed: {e}")
        return False


def test_analysis_parallel():
    """Test that comprehensive analysis has parallel processing."""
    print("\n" + "="*60)
    print("Testing Analysis Parallel Processing")
    print("="*60)
    
    try:
        analysis_file = Path(__file__).parent.parent / "src" / "analytics" / "comprehensive_analysis.py"
        if analysis_file.exists():
            content = analysis_file.read_text()
            if "parallel_calculation" in content and "independent_analyses" in content:
                print("✅ Comprehensive analysis has parallel processing")
                return True
            else:
                print("⚠️  Parallel processing not found in comprehensive analysis")
                return False
        else:
            print("⚠️  comprehensive_analysis.py not found")
            return False
    except Exception as e:
        print(f"❌ Analysis parallel test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("Core Features Validation")
    print("Version 3.11.1")
    print("="*60)
    
    tests = [
        ("Utils Imports", test_utils_imports),
        ("Parallel Processing", test_parallel_processing),
        ("Query Cache", test_query_cache),
        ("Retry Logic", test_retry_logic),
        ("Price Download Parallel", test_price_download_parallel),
        ("Analysis Parallel", test_analysis_parallel),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} test crashed: {e}")
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Validation Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All core features validated!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
