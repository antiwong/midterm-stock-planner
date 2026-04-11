import { useState, useEffect, useRef, useCallback } from 'react';

interface UsePollingResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

/**
 * Polls an async fetcher on an interval. Returns current data,
 * loading state, error, and timestamp of last successful fetch.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs = 30000,
  /** Extra dependency — when it changes, re-fetch immediately */
  dep?: unknown,
): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mountedRef = useRef(true);

  const doFetch = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetcher();
      if (!mountedRef.current) return;
      setData(result);
      setError(null);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      if (!mountedRef.current) return;
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    mountedRef.current = true;
    doFetch();
    const id = setInterval(doFetch, intervalMs);
    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
  }, [doFetch, intervalMs, dep]);

  return { data, loading, error, lastUpdated };
}
