import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorCardProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorCard({ message, onRetry }: ErrorCardProps) {
  return (
    <div className="bg-loss/5 border border-loss/20 rounded-xl p-6 flex flex-col items-center text-center">
      <div className="w-12 h-12 rounded-2xl bg-loss/10 flex items-center justify-center mb-3">
        <AlertTriangle size={24} className="text-loss" />
      </div>
      <h3 className="text-sm font-semibold text-white mb-1">Something went wrong</h3>
      <p className="text-xs text-muted max-w-sm mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-lighter/40 hover:bg-surface-lighter/60 text-sm text-white font-medium transition-smooth min-h-[44px]"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}
