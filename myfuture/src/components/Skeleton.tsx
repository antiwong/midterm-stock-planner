/**
 * Reusable skeleton loading placeholders.
 * All variants use the project's dark theme surface tokens.
 */

interface SkeletonProps {
  className?: string;
}

/** Generic rectangular shimmer bar */
export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-surface-lighter/40 ${className}`}
    />
  );
}

/** Stat card placeholder matching the Stat component layout */
export function SkeletonStat() {
  return (
    <div className="space-y-1.5">
      <Skeleton className="h-2.5 w-16" />
      <Skeleton className="h-5 w-24" />
    </div>
  );
}

/** Full-width table row placeholder */
export function SkeletonRow({ cols = 6 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-2.5">
          <Skeleton className={`h-4 ${i === 0 ? 'w-16' : 'w-12 ml-auto'}`} />
        </td>
      ))}
    </tr>
  );
}

/** Card-shaped skeleton for a full section */
export function SkeletonCard({ rows = 4, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-surface-light border border-surface-lighter/40 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-surface-lighter/40 flex items-center justify-between">
        <div className="space-y-1.5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48" />
        </div>
        <Skeleton className="h-5 w-14" />
      </div>
      <table className="w-full">
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <SkeletonRow key={i} cols={cols} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Page-level loading skeleton used by Suspense fallback */
export function PageSkeleton() {
  return (
    <div className="space-y-6 p-2">
      {/* Header area */}
      <div className="space-y-2">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-3 w-72" />
      </div>
      {/* Stat bar */}
      <div className="bg-surface-light border border-surface-lighter/40 rounded-xl p-5">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          {Array.from({ length: 7 }).map((_, i) => (
            <SkeletonStat key={i} />
          ))}
        </div>
      </div>
      {/* Table cards */}
      <SkeletonCard rows={3} cols={6} />
      <SkeletonCard rows={5} cols={9} />
    </div>
  );
}
