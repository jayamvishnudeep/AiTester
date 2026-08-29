import { useState } from 'react';
import Modal from './Modal.jsx';
import { Check, Close, Link, Plus, Star, Trash } from './Icons.jsx';
import { COLUMNS, COLUMN_BY_ID } from '../lib/constants.js';
import { formatDate, formatDateTime, relativeDays } from '../lib/dates.js';
import { daysInCurrentStage, isFollowUpOverdue, roundProgress } from '../lib/nudges.js';

function Field({ label, children }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{children || <span className="text-ink-faint">—</span>}</dd>
    </div>
  );
}

export default function JobDetailPanel({ job, open, onClose, onUpdate, onEdit, onDelete }) {
  const [newRound, setNewRound] = useState('');
  if (!job) return null;

  const column = COLUMN_BY_ID[job.status];
  const rounds = roundProgress(job);
  const overdue = isFollowUpOverdue(job);

  const setRounds = (next) => onUpdate(job.id, { rounds: next });

  const toggleRound = (i) =>
    setRounds(job.rounds.map((r, j) => (j === i ? { ...r, done: !r.done } : r)));

  const removeRound = (i) => setRounds(job.rounds.filter((_, j) => j !== i));

  function addRound() {
    const label = newRound.trim();
    if (!label) return;
    setRounds([...(job.rounds || []), { label, done: false }]);
    setNewRound('');
  }

  const history = [...(job.history || [])].sort((a, b) => new Date(b.at) - new Date(a.at));

  return (
    <Modal
      open={open}
      onClose={onClose}
      variant="panel"
      title={job.company}
      subtitle={job.role}
      footer={
        <>
          <button onClick={() => onDelete(job)} className="btn-ghost mr-auto text-rose-500 hover:bg-rose-500/10">
            <Trash size={14} /> Delete
          </button>
          <button onClick={onClose} className="btn-outline">Close</button>
          <button onClick={() => onEdit(job)} className="btn-primary">Edit</button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Status + quick actions */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={job.status}
            onChange={(e) => onUpdate(job.id, { status: e.target.value })}
            className="field w-auto py-1 text-sm font-medium"
            style={{ borderLeft: `3px solid ${column?.accent}` }}
            aria-label="Status"
          >
            {COLUMNS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>

          <button
            onClick={() => onUpdate(job.id, { priority: !job.priority })}
            className={`btn-outline ${job.priority ? 'text-amber-500' : ''}`}
            aria-pressed={job.priority}
          >
            <Star size={14} filled={job.priority} />
            {job.priority ? 'Priority' : 'Flag priority'}
          </button>

          {job.url && (
            <a href={job.url} target="_blank" rel="noreferrer noopener" className="btn-outline">
              <Link size={14} /> Open posting
            </a>
          )}

          <span className="ml-auto text-xs text-ink-faint">
            {daysInCurrentStage(job)}d in {column?.label}
          </span>
        </div>

        {overdue && (
          <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-600 dark:text-rose-400">
            Follow-up was due {formatDate(job.followUpBy)} — {relativeDays(job.followUpBy).replace(' ago', ' overdue')}.
          </p>
        )}

        {/* Core fields */}
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
          <Field label="Date applied">{formatDate(job.dateApplied)}</Field>
          <Field label="Follow up by">{job.followUpBy ? formatDate(job.followUpBy) : null}</Field>
          <Field label="Resume used">{job.resume}</Field>
          <Field label="Salary range">{job.salary}</Field>
          <Field label="Recruiter">{job.recruiterName}</Field>
          <Field label="Recruiter contact">
            {job.recruiterContact && /@/.test(job.recruiterContact) ? (
              <a className="text-brand hover:underline" href={`mailto:${job.recruiterContact}`}>{job.recruiterContact}</a>
            ) : job.recruiterContact}
          </Field>
        </dl>

        {job.tags?.length > 0 && (
          <div>
            <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-ink-muted">Tags</h3>
            <div className="flex flex-wrap gap-1.5">
              {job.tags.map((t, i) => (
                <span key={i} className="rounded px-2 py-0.5 text-xs font-medium"
                  style={{ backgroundColor: `${t.color}1f`, color: t.color }}>
                  {t.label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Interview checklist */}
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-medium uppercase tracking-wide text-ink-muted">Interview rounds</h3>
            <span className="text-xs text-ink-faint">{rounds.done}/{rounds.total} complete</span>
          </div>

          {rounds.total > 0 && (
            <div className="mb-2 h-1 overflow-hidden rounded-full bg-surface-sunken">
              <div
                className="h-full rounded-full bg-violet-500 transition-all"
                style={{ width: `${rounds.total ? (rounds.done / rounds.total) * 100 : 0}%` }}
              />
            </div>
          )}

          <ul className="space-y-1">
            {(job.rounds || []).map((r, i) => (
              <li key={`${r.label}-${i}`} className="group flex items-center gap-2">
                <button
                  onClick={() => toggleRound(i)}
                  aria-pressed={r.done}
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors
                             ${r.done ? 'border-violet-500 bg-violet-500 text-white' : 'border-edge hover:border-violet-400'}`}
                >
                  {r.done && <Check size={11} />}
                </button>
                <span className={`flex-1 text-sm ${r.done ? 'text-ink-faint line-through' : 'text-ink'}`}>
                  {r.label}
                </span>
                <button
                  onClick={() => removeRound(i)}
                  aria-label={`Remove ${r.label}`}
                  className="rounded p-0.5 text-ink-faint opacity-0 transition-opacity hover:text-rose-500 group-hover:opacity-100"
                >
                  <Close size={12} />
                </button>
              </li>
            ))}
          </ul>

          <div className="mt-2 flex gap-2">
            <input
              className="field flex-1 py-1 text-sm"
              value={newRound}
              onChange={(e) => setNewRound(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addRound(); } }}
              placeholder="Add a round…"
            />
            <button onClick={addRound} className="btn-outline"><Plus size={14} /></button>
          </div>
        </section>

        {job.notes && (
          <section>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-muted">Notes</h3>
            <p className="whitespace-pre-wrap rounded-lg bg-surface-sunken px-3 py-2 text-sm text-ink">{job.notes}</p>
          </section>
        )}

        {job.jdSnapshot && (
          <section>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-muted">Job description snapshot</h3>
            <div className="scroll-slim max-h-56 overflow-y-auto whitespace-pre-wrap rounded-lg bg-surface-sunken px-3 py-2 text-xs leading-relaxed text-ink-muted">
              {job.jdSnapshot}
            </div>
          </section>
        )}

        {/* Auto-generated, read-only */}
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-muted">Status history</h3>
          <ol className="space-y-0">
            {history.map((h, i) => {
              const col = COLUMN_BY_ID[h.status];
              return (
                <li key={`${h.at}-${i}`} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: col?.accent }} />
                    {i < history.length - 1 && <span className="w-px flex-1 bg-edge" />}
                  </div>
                  <div className="pb-3">
                    <p className="text-sm text-ink">Moved to {col?.label || h.status}</p>
                    <p className="text-xs text-ink-faint">{formatDateTime(h.at)}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      </div>
    </Modal>
  );
}
