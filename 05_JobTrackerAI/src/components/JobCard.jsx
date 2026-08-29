import { useDraggable } from '@dnd-kit/core';
import { Link, Star } from './Icons.jsx';
import { relativeDays } from '../lib/dates.js';
import { nudgesFor, roundProgress } from '../lib/nudges.js';
import { COLUMN_BY_ID } from '../lib/constants.js';

const NUDGE_TONES = {
  rose: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
  amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
};

export default function JobCard({ job, compact, onOpen, onTogglePriority }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: job.id });
  const column = COLUMN_BY_ID[job.status];
  const nudges = nudgesFor(job);
  const rounds = roundProgress(job);

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 30 }
    : undefined;

  return (
    <article
      ref={setNodeRef}
      style={{ ...style, borderLeftColor: column?.accent }}
      className={`card-surface group border-l-[3px] transition-shadow
                  ${compact ? 'px-2.5 py-2' : 'px-3 py-2.5'}
                  ${isDragging ? 'opacity-40' : 'hover:shadow-md'}`}
    >
      {/* The whole body is the drag handle; the buttons below opt out via stopPropagation. */}
      <div {...listeners} {...attributes} className="cursor-grab active:cursor-grabbing">
        <div className="flex items-start gap-2">
          <button
            onClick={onOpen}
            onPointerDown={(e) => e.stopPropagation()}
            className="min-w-0 flex-1 text-left"
          >
            <h3 className="truncate text-sm font-semibold text-ink">{job.company || 'Untitled'}</h3>
            <p className="truncate text-xs text-ink-muted">{job.role}</p>
          </button>

          <button
            onClick={(e) => { e.stopPropagation(); onTogglePriority(); }}
            onPointerDown={(e) => e.stopPropagation()}
            aria-label={job.priority ? 'Remove priority' : 'Mark priority'}
            aria-pressed={job.priority}
            className={`shrink-0 rounded p-1 transition-colors
                        ${job.priority ? 'text-amber-500' : 'text-ink-faint opacity-0 group-hover:opacity-100 focus:opacity-100'}`}
          >
            <Star size={14} filled={job.priority} />
          </button>
        </div>

        {!compact && job.tags?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {job.tags.map((t, i) => (
              <span
                key={`${t.label}-${i}`}
                className="rounded px-1.5 py-0.5 text-[11px] font-medium"
                style={{ backgroundColor: `${t.color}1f`, color: t.color }}
              >
                {t.label}
              </span>
            ))}
          </div>
        )}

        {nudges.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {nudges.map((n) => (
              <span key={n.id} className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${NUDGE_TONES[n.tone]}`}>
                {n.label}
              </span>
            ))}
          </div>
        )}

        <div className="mt-2 flex items-center gap-2 text-[11px] text-ink-faint">
          <span className="shrink-0">{relativeDays(job.dateApplied)}</span>
          {job.resume && (
            <span className="truncate rounded bg-surface-sunken px-1.5 py-0.5 font-medium text-ink-muted">
              {job.resume}
            </span>
          )}
          {job.status === 'interview' && rounds.total > 0 && (
            <span className="shrink-0 font-medium text-violet-500">
              {rounds.done}/{rounds.total} rounds
            </span>
          )}
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer noopener"
              onClick={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              aria-label={`Open ${job.company} posting`}
              className="ml-auto shrink-0 rounded p-0.5 text-ink-faint hover:text-brand"
            >
              <Link size={13} />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
