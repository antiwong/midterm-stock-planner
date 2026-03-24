import { useState, useEffect, useCallback } from 'react';

interface User {
  username: string;
  display_name?: string;
  role?: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

// Session activity timeout (matches backend 8h, but we check at 7h to refresh)
const ACTIVITY_CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if we have a valid session on mount
  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        if (data.authenticated) {
          setUser(data.user);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Periodic session check — detects expiry while tab is open
  useEffect(() => {
    if (!user) return;
    const id = setInterval(() => {
      fetch('/api/auth/me', { credentials: 'include' })
        .then((r) => r.json())
        .then((data) => {
          if (!data.authenticated) {
            setUser(null);
          }
        })
        .catch(() => {});
    }, ACTIVITY_CHECK_INTERVAL);
    return () => clearInterval(id);
  }, [user]);

  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    setError(null);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (data.ok) {
        setUser(data.user);
        return true;
      }
      setError(data.error || 'Login failed');
      return false;
    } catch {
      setError('Network error');
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    setUser(null);
  }, []);

  return { user, loading, error, login, logout };
}
