import { useDroppable } from '@dnd-kit/core';
import JobCard from './JobCard.jsx';

export default function Column({ column, jobs, compact, onOpenJob, onTogglePriority }) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <section className="flex h-full w-[17rem] shrink-0 flex-col md:w-[18.5rem]">
      <header className="mb-2 flex items-center gap-2 px-1">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: column.accent }} />
        <h2 className="text-sm font-semibold text-ink">{column.label}</h2>
        <span className="rounded-full bg-surface-sunken px-1.5 py-0.5 text-xs font-medium text-ink-muted">
          {jobs.length}
        </span>
      </header>

      <div
        ref={setNodeRef}
        className={`scroll-slim flex-1 space-y-2 overflow-y-auto rounded-xl border border-dashed p-2 transition-colors
                    ${isOver ? 'border-brand bg-brand/5' : 'border-transparent bg-surface-sunken/60'}`}
      >
        {jobs.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs leading-relaxed text-ink-faint">{column.empty}</p>
        ) : (
          jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              compact={compact}
              onOpen={() => onOpenJob(job)}
              onTogglePriority={() => onTogglePriority(job)}
            />
          ))
        )}
      </div>
    </section>
  );
}
