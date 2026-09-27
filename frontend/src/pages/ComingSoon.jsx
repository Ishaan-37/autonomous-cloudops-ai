export default function ComingSoon({ page, phase }) {
  return (
    <div className="p-8">
      <div className="card p-10 flex flex-col items-center text-center gap-2 max-w-md mx-auto mt-16">
        <p className="eyebrow">{page}</p>
        <h2 className="font-display text-lg font-semibold">Scheduled for {phase}</h2>
        <p className="text-sm text-muted">
          This view is scoped and wired into the router — build it out once the
          matching backend endpoint is ready.
        </p>
      </div>
    </div>
  )
}
