export default function Skeleton({ className = '' }) {
  return <div className={`skeleton rounded ${className}`} />
}

export function ArticleCardSkeleton() {
  return (
    <div className="card p-5 space-y-4">
      <div className="flex gap-2">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-32" />
      </div>
      <Skeleton className="h-8 w-3/4" />
      <Skeleton className="h-20 w-full" />
      <div className="flex justify-between pt-3 border-t border-gray-200">
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-24" />
      </div>
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-4">
        <Skeleton className="w-14 h-14 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
    </div>
  )
}
