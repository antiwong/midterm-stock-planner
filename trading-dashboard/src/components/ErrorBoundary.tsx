import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <h3 className="text-red-400 font-semibold mb-2">Something went wrong</h3>
          <p className="text-sm text-muted mb-4">{this.state.error.message}</p>
          <button
            onClick={() => this.setState({ error: null })}
            className="px-4 py-1.5 bg-surface-lighter rounded-lg text-sm text-white hover:bg-surface-light transition-colors"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
