"""
Request Batching Utilities
==========================
Utilities for batching API requests to improve performance and respect rate limits.
"""

import time
import logging
from typing import List, Callable, Any, Dict, Optional, Tuple
from collections import deque
from threading import Lock
import asyncio

logger = logging.getLogger(__name__)


class RequestBatcher:
    """Batch API requests to improve performance and respect rate limits."""
    
    def __init__(
        self,
        batch_size: int = 10,
        max_wait_time: float = 0.5,
        rate_limit_per_second: Optional[float] = None
    ):
        """
        Initialize request batcher.
        
        Args:
            batch_size: Maximum number of requests per batch
            max_wait_time: Maximum time to wait before sending batch (seconds)
            rate_limit_per_second: Maximum requests per second (None = no limit)
        """
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.rate_limit_per_second = rate_limit_per_second
        
        self.pending_requests: deque = deque()
        self.last_request_time: float = 0.0
        self.lock = Lock()
    
    def add_request(
        self,
        request_func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Any, Optional[Exception]]:
        """
        Add a request to the batch. Returns result immediately if batch is full.
        
        Args:
            request_func: Function to call for the request
            *args: Positional arguments for request_func
            **kwargs: Keyword arguments for request_func
        
        Returns:
            Tuple of (result, error)
        """
        with self.lock:
            # Add to pending
            self.pending_requests.append((request_func, args, kwargs))
            
            # Check if we should send batch
            should_send = (
                len(self.pending_requests) >= self.batch_size or
                (time.time() - self.last_request_time) >= self.max_wait_time
            )
            
            if should_send:
                return self._send_batch()
            else:
                # Wait a bit and check again
                time.sleep(0.1)
                if len(self.pending_requests) >= self.batch_size:
                    return self._send_batch()
                return None, None
    
    def _send_batch(self) -> Tuple[List[Any], Optional[Exception]]:
        """Send all pending requests in batch."""
        if not self.pending_requests:
            return [], None
        
        # Respect rate limit
        if self.rate_limit_per_second:
            time_since_last = time.time() - self.last_request_time
            min_interval = 1.0 / self.rate_limit_per_second
            if time_since_last < min_interval:
                time.sleep(min_interval - time_since_last)
        
        # Collect batch
        batch = []
        while self.pending_requests and len(batch) < self.batch_size:
            batch.append(self.pending_requests.popleft())
        
        # Execute batch
        results = []
        errors = []
        
        for request_func, args, kwargs in batch:
            try:
                result = request_func(*args, **kwargs)
                results.append(result)
                errors.append(None)
            except Exception as e:
                logger.error(f"Error in batched request: {e}")
                results.append(None)
                errors.append(e)
        
        self.last_request_time = time.time()
        
        # Return first result (for single request case)
        if len(results) == 1:
            return results[0], errors[0]
        
        return results, errors
    
    def flush(self) -> Tuple[List[Any], List[Optional[Exception]]]:
        """Flush all pending requests."""
        with self.lock:
            if not self.pending_requests:
                return [], []
            
            results = []
            errors = []
            
            while self.pending_requests:
                request_func, args, kwargs = self.pending_requests.popleft()
                try:
                    result = request_func(*args, **kwargs)
                    results.append(result)
                    errors.append(None)
                except Exception as e:
                    logger.error(f"Error in flushed request: {e}")
                    results.append(None)
                    errors.append(e)
            
            self.last_request_time = time.time()
            return results, errors


def batch_api_requests(
    requests: List[Tuple[Callable, tuple, dict]],
    batch_size: int = 10,
    max_workers: int = 4,
    rate_limit_per_second: Optional[float] = None
) -> List[Tuple[Any, Optional[Exception]]]:
    """
    Batch and execute multiple API requests in parallel.
    
    Args:
        requests: List of (function, args_tuple, kwargs_dict) tuples
        batch_size: Number of requests per batch
        max_workers: Maximum parallel workers
        rate_limit_per_second: Maximum requests per second
    
    Returns:
        List of (result, error) tuples
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = []
    batcher = RequestBatcher(
        batch_size=batch_size,
        rate_limit_per_second=rate_limit_per_second
    )
    
    # Process in batches
    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        
        # Execute batch with parallel workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(req_func, *req_args, **req_kwargs): idx
                for idx, (req_func, req_args, req_kwargs) in enumerate(batch)
            }
            
            batch_results = [None] * len(batch)
            batch_errors = [None] * len(batch)
            
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    batch_results[idx] = result
                except Exception as e:
                    batch_errors[idx] = e
            
            # Add to results
            for result, error in zip(batch_results, batch_errors):
                results.append((result, error))
        
        # Respect rate limit between batches
        if rate_limit_per_second and i + batch_size < len(requests):
            time.sleep(1.0 / rate_limit_per_second)
    
    return results
