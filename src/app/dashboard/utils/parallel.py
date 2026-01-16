"""
Parallel Processing Utilities
=============================
Utilities for parallel processing of data downloads, analysis, and other operations.
"""

import logging
from typing import List, Callable, Any, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import wraps
import time

logger = logging.getLogger(__name__)


class ParallelProcessor:
    """Parallel processing manager with progress tracking."""
    
    def __init__(
        self,
        max_workers: int = None,
        use_processes: bool = False,
        show_progress: bool = True
    ):
        """
        Initialize parallel processor.
        
        Args:
            max_workers: Maximum number of workers (default: CPU count)
            use_processes: Use ProcessPoolExecutor instead of ThreadPoolExecutor
            show_progress: Show progress updates
        """
        import os
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.use_processes = use_processes
        self.show_progress = show_progress
        self.executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    
    def process_batch(
        self,
        items: List[Any],
        func: Callable,
        *args,
        **kwargs
    ) -> List[Tuple[Any, Any, Optional[Exception]]]:
        """
        Process items in parallel.
        
        Args:
            items: List of items to process
            func: Function to apply to each item (must accept item as first arg)
            *args: Additional positional arguments for func
            **kwargs: Additional keyword arguments for func
        
        Returns:
            List of tuples: (item, result, error)
        """
        results = []
        total = len(items)
        
        with self.executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(func, item, *args, **kwargs): item
                for item in items
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append((item, result, None))
                    
                    if self.show_progress:
                        logger.info(f"Progress: {completed}/{total} ({completed*100//total}%)")
                except Exception as e:
                    logger.error(f"Error processing {item}: {e}")
                    results.append((item, None, e))
        
        return results
    
    def process_map(
        self,
        items: List[Any],
        func: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Process items in parallel and return results only.
        
        Args:
            items: List of items to process
            func: Function to apply to each item
            *args: Additional positional arguments for func
            **kwargs: Additional keyword arguments for func
        
        Returns:
            List of results (None for failed items)
        """
        results = self.process_batch(items, func, *args, **kwargs)
        return [result for _, result, error in results if error is None]
    
    def process_with_errors(
        self,
        items: List[Any],
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[List[Any], List[Tuple[Any, Exception]]]:
        """
        Process items and separate successes from errors.
        
        Args:
            items: List of items to process
            func: Function to apply to each item
            *args: Additional positional arguments for func
            **kwargs: Additional keyword arguments for func
        
        Returns:
            Tuple of (successful_results, [(item, error), ...])
        """
        results = self.process_batch(items, func, *args, **kwargs)
        successes = [result for _, result, error in results if error is None]
        errors = [(item, error) for item, _, error in results if error is not None]
        return successes, errors


def parallel_download(
    items: List[Any],
    download_func: Callable,
    batch_size: int = 10,
    max_workers: int = None,
    delay_between_batches: float = 0.1
) -> List[Tuple[Any, Any, Optional[Exception]]]:
    """
    Download data in parallel batches with rate limiting.
    
    Args:
        items: List of items to download
        download_func: Function to download a single item
        batch_size: Number of items per batch
        max_workers: Maximum parallel workers
        delay_between_batches: Delay between batches (seconds)
    
    Returns:
        List of (item, result, error) tuples
    """
    processor = ParallelProcessor(max_workers=max_workers, show_progress=True)
    all_results = []
    
    # Process in batches to respect rate limits
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
        
        batch_results = processor.process_batch(batch, download_func)
        all_results.extend(batch_results)
        
        # Rate limiting between batches
        if i + batch_size < len(items) and delay_between_batches > 0:
            time.sleep(delay_between_batches)
    
    return all_results


def parallel_analysis(
    runs: List[Any],
    analysis_func: Callable,
    max_workers: int = None
) -> List[Tuple[Any, Any, Optional[Exception]]]:
    """
    Run analysis on multiple runs in parallel.
    
    Args:
        runs: List of run identifiers or run objects
        analysis_func: Function to analyze a single run
        max_workers: Maximum parallel workers
    
    Returns:
        List of (run, result, error) tuples
    """
    processor = ParallelProcessor(max_workers=max_workers, show_progress=True)
    return processor.process_batch(runs, analysis_func)


def parallel_calculation(
    calculations: List[Callable],
    max_workers: int = None
) -> List[Any]:
    """
    Execute multiple calculations in parallel.
    
    Args:
        calculations: List of callable functions (no arguments)
        max_workers: Maximum parallel workers
    
    Returns:
        List of results
    """
    processor = ParallelProcessor(max_workers=max_workers, show_progress=False)
    
    # Wrap each calculation to be callable with no args
    def execute_calc(calc: Callable):
        return calc()
    
    results = processor.process_batch(calculations, execute_calc)
    return [result for _, result, error in results if error is None]


def parallel_map(
    items: List[Any],
    func: Callable,
    max_workers: int = None,
    use_processes: bool = False
) -> List[Any]:
    """
    Simple parallel map function.
    
    Args:
        items: List of items to process
        func: Function to apply to each item
        max_workers: Maximum parallel workers
        use_processes: Use processes instead of threads
    
    Returns:
        List of results
    """
    processor = ParallelProcessor(
        max_workers=max_workers,
        use_processes=use_processes,
        show_progress=False
    )
    return processor.process_map(items, func)


def parallel_filter(
    items: List[Any],
    predicate: Callable,
    max_workers: int = None
) -> List[Any]:
    """
    Filter items in parallel.
    
    Args:
        items: List of items to filter
        predicate: Function that returns True/False for each item
        max_workers: Maximum parallel workers
    
    Returns:
        List of items where predicate returned True
    """
    processor = ParallelProcessor(max_workers=max_workers, show_progress=False)
    results = processor.process_batch(items, predicate)
    return [item for item, result, error in results if result is True and error is None]


# Decorator for parallel execution
def parallelize(max_workers: int = None, use_processes: bool = False):
    """
    Decorator to parallelize a function that processes a list.
    
    Usage:
        @parallelize(max_workers=4)
        def process_items(items):
            return [process(item) for item in items]
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(items: List[Any], *args, **kwargs):
            processor = ParallelProcessor(
                max_workers=max_workers,
                use_processes=use_processes,
                show_progress=True
            )
            return processor.process_map(items, func, *args, **kwargs)
        return wrapper
    return decorator


# Performance monitoring
class ParallelPerformanceMonitor:
    """Monitor parallel processing performance."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.results = []
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
    
    def stop(self):
        """Stop timing."""
        self.end_time = time.time()
    
    def get_duration(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def record_result(self, item: Any, duration: float, success: bool):
        """Record a result."""
        self.results.append({
            'item': item,
            'duration': duration,
            'success': success
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.results:
            return {}
        
        durations = [r['duration'] for r in self.results]
        successes = sum(1 for r in self.results if r['success'])
        
        return {
            'total_items': len(self.results),
            'successful': successes,
            'failed': len(self.results) - successes,
            'total_duration': self.get_duration(),
            'avg_item_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'items_per_second': len(self.results) / self.get_duration() if self.get_duration() > 0 else 0
        }
