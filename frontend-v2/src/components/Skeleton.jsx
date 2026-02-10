export default function Skeleton({ className = '' }) {
  return <div className={`skeleton ${className}`} />
}

export function ArticleCardSkeleton() {
  return (
    <div className="card p-5 space-y-3">
      <div className="flex gap-1.5">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-16 w-full" />
      <div className="flex justify-between pt-3" style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
        <Skeleton className="h-5 w-14 rounded-full" />
        <Skeleton className="h-5 w-16" />
      </div>
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="card p-5">
      <Skeleton className="w-10 h-10 rounded-xl mb-3" />
      <Skeleton className="h-7 w-12 mb-1" />
      <Skeleton className="h-3 w-20" />
    </div>
  )
}
