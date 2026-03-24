import { useState, type FormEvent } from 'react';

interface Props {
  onLogin: (username: string, password: string) => Promise<boolean>;
  error: string | null;
}

export default function Login({ onLogin, error }: Props) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setSubmitting(true);
    await onLogin(username, password);
    setSubmitting(false);
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="bg-surface-light rounded-2xl p-8 border border-surface-lighter shadow-2xl">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-white">Stock Planner</h1>
            <p className="text-sm text-muted mt-1">Trading Dashboard</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-muted mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                autoComplete="username"
                className="w-full bg-surface border border-surface-lighter rounded-lg px-3 py-2.5 text-sm text-white placeholder-muted/50 focus:outline-none focus:border-accent transition-colors"
                placeholder="Enter username"
              />
            </div>
            <div>
              <label className="block text-xs text-muted mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="w-full bg-surface border border-surface-lighter rounded-lg px-3 py-2.5 text-sm text-white placeholder-muted/50 focus:outline-none focus:border-accent transition-colors"
                placeholder="Enter password"
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-sm text-red-400">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !username || !password}
              className="w-full bg-accent hover:bg-accent/90 disabled:bg-surface-lighter disabled:text-muted text-white font-medium rounded-lg py-2.5 text-sm transition-colors"
            >
              {submitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
