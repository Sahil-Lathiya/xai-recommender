export default function SkeletonCard() {
  return (
    <div className="card p-5 flex flex-col gap-3 animate-pulse">
      <div className="w-full h-44 bg-slate-700 rounded-lg shimmer" />
      <div className="flex items-center justify-between">
        <div className="h-5 w-24 bg-slate-700 rounded shimmer" />
        <div className="h-5 w-16 bg-slate-700 rounded-full shimmer" />
      </div>
      <div className="h-4 w-3/4 bg-slate-700 rounded shimmer" />
      <div className="h-4 w-1/2 bg-slate-700 rounded shimmer" />
      <div className="flex items-center justify-between mt-1">
        <div className="h-4 w-20 bg-slate-700 rounded shimmer" />
        <div className="h-4 w-16 bg-slate-700 rounded shimmer" />
      </div>
      <div className="h-9 w-full bg-slate-700 rounded-lg shimmer mt-1" />
    </div>
  )
}
