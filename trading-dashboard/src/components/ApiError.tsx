interface Props {
  error: string;
  onRetry?: () => void;
}

export default function ApiError({ error, onRetry }: Props) {
  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-5 flex items-center justify-between">
      <div>
        <p className="text-red-400 text-sm font-medium">Failed to load data</p>
        <p className="text-xs text-muted mt-1">{error}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 bg-surface-lighter rounded-lg text-xs text-white hover:bg-surface-light transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
