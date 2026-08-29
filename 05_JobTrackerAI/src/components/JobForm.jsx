import { useEffect, useMemo, useState } from 'react';
import Modal from './Modal.jsx';
import { Close, Warning } from './Icons.jsx';
import { COLUMNS, DEFAULT_ROUNDS, TAG_COLORS } from '../lib/constants.js';
import { fromDateInput, toDateInput, todayISO } from '../lib/dates.js';
import { knownResumes } from '../lib/analytics.js';

const blank = () => ({
  company: '', role: '', url: '', resume: '',
  dateApplied: todayISO(), salary: '', notes: '',
  status: 'wishlist', recruiterName: '', recruiterContact: '',
  tags: [], priority: false,
  rounds: DEFAULT_ROUNDS.map((label) => ({ label, done: false })),
  jdSnapshot: '', followUpBy: null,
});

export default function JobForm({ open, onClose, onSave, job, allJobs }) {
  const [form, setForm] = useState(blank);
  const [errors, setErrors] = useState({});
  const [tagDraft, setTagDraft] = useState('');
  const [tagColor, setTagColor] = useState(TAG_COLORS[1].hex);

  const isEdit = Boolean(job);

  useEffect(() => {
    if (!open) return;
    setForm(job ? { ...job } : blank());
    setErrors({});
    setTagDraft('');
  }, [open, job]);

  const resumeOptions = useMemo(() => knownResumes(allJobs), [allJobs]);

  // Non-blocking: flags a company+role that already exists on another card.
  const duplicate = useMemo(() => {
    const c = form.company.trim().toLowerCase();
    const r = form.role.trim().toLowerCase();
    if (!c || !r) return null;
    return allJobs.find(
      (j) => j.id !== job?.id &&
        (j.company || '').trim().toLowerCase() === c &&
        (j.role || '').trim().toLowerCase() === r
    );
  }, [form.company, form.role, allJobs, job]);

  const set = (key) => (e) => {
    const value = e?.target?.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
    if (errors[key]) setErrors((x) => ({ ...x, [key]: undefined }));
  };

  function addTag() {
    const label = tagDraft.trim();
    if (!label) return;
    if (form.tags.some((t) => t.label.toLowerCase() === label.toLowerCase())) {
      setTagDraft('');
      return;
    }
    setForm((f) => ({ ...f, tags: [...f.tags, { label, color: tagColor }] }));
    setTagDraft('');
  }

  function validate() {
    const next = {};
    if (!form.company.trim()) next.company = 'Company is required.';
    if (!form.role.trim()) next.role = 'Role is required.';
    if (form.url && !/^https?:\/\//i.test(form.url.trim())) {
      next.url = 'Include http:// or https://';
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function submit(e) {
    e.preventDefault();
    if (!validate()) return;
    onSave({
      ...form,
      company: form.company.trim(),
      role: form.role.trim(),
      url: form.url.trim(),
      resume: form.resume.trim(),
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit application' : 'New application'}
      subtitle={isEdit ? `${job.company} · ${job.role}` : 'Track a role you have applied to or want to.'}
      width="max-w-2xl"
      footer={
        <>
          <button type="button" onClick={onClose} className="btn-outline">Cancel</button>
          <button type="submit" form="job-form" className="btn-primary">
            {isEdit ? 'Save changes' : 'Add application'}
          </button>
        </>
      }
    >
      <form id="job-form" onSubmit={submit} className="space-y-4" noValidate>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="f-company">Company *</label>
            <input
              id="f-company" className="field" value={form.company} onChange={set('company')}
              placeholder="Acme Corp" autoFocus
              aria-invalid={Boolean(errors.company)}
            />
            {errors.company && <p className="mt-1 text-xs text-rose-500">{errors.company}</p>}
          </div>
          <div>
            <label className="label" htmlFor="f-role">Role *</label>
            <input
              id="f-role" className="field" value={form.role} onChange={set('role')}
              placeholder="Senior QA Engineer"
              aria-invalid={Boolean(errors.role)}
            />
            {errors.role && <p className="mt-1 text-xs text-rose-500">{errors.role}</p>}
          </div>
        </div>

        {duplicate && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            <Warning size={14} />
            <span>
              You already have <strong>{duplicate.company} · {duplicate.role}</strong> in{' '}
              <strong>{COLUMNS.find((c) => c.id === duplicate.status)?.label}</strong>. Saving anyway is fine —
              just checking it isn't a slip.
            </span>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="f-url">Job URL</label>
            <input
              id="f-url" className="field" value={form.url} onChange={set('url')}
              placeholder="https://linkedin.com/jobs/..." inputMode="url"
              aria-invalid={Boolean(errors.url)}
            />
            {errors.url && <p className="mt-1 text-xs text-rose-500">{errors.url}</p>}
          </div>
          <div>
            <label className="label" htmlFor="f-resume">Resume used</label>
            <input
              id="f-resume" className="field" value={form.resume} onChange={set('resume')}
              placeholder="QA_Lead_Resume_v2" list="resume-options"
            />
            <datalist id="resume-options">
              {resumeOptions.map((r) => <option key={r} value={r} />)}
            </datalist>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="f-status">Status</label>
            <select id="f-status" className="field" value={form.status} onChange={set('status')}>
              {COLUMNS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="f-date">Date applied</label>
            <input
              id="f-date" type="date" className="field"
              value={toDateInput(form.dateApplied)}
              onChange={(e) => setForm((f) => ({ ...f, dateApplied: fromDateInput(e.target.value) || todayISO() }))}
            />
          </div>
          <div>
            <label className="label" htmlFor="f-followup">Follow up by</label>
            <input
              id="f-followup" type="date" className="field"
              value={toDateInput(form.followUpBy)}
              onChange={(e) => setForm((f) => ({ ...f, followUpBy: fromDateInput(e.target.value) }))}
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="f-salary">Salary range</label>
            <input id="f-salary" className="field" value={form.salary} onChange={set('salary')} placeholder="₹25-30 LPA" />
          </div>
          <div>
            <label className="label" htmlFor="f-rec-name">Recruiter</label>
            <input id="f-rec-name" className="field" value={form.recruiterName} onChange={set('recruiterName')} placeholder="Name" />
          </div>
          <div>
            <label className="label" htmlFor="f-rec-contact">Recruiter contact</label>
            <input id="f-rec-contact" className="field" value={form.recruiterContact} onChange={set('recruiterContact')} placeholder="email or LinkedIn" />
          </div>
        </div>

        <div>
          <span className="label">Tags</span>
          {form.tags.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {form.tags.map((t, i) => (
                <span
                  key={`${t.label}-${i}`}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium"
                  style={{ backgroundColor: `${t.color}1f`, color: t.color }}
                >
                  {t.label}
                  <button
                    type="button"
                    aria-label={`Remove ${t.label}`}
                    onClick={() => setForm((f) => ({ ...f, tags: f.tags.filter((_, j) => j !== i) }))}
                  >
                    <Close size={11} />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              className="field flex-1"
              value={tagDraft}
              onChange={(e) => setTagDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
              placeholder="Remote, Referral, Dream Company…"
            />
            <div className="flex items-center gap-1 rounded-lg border border-edge px-1.5">
              {TAG_COLORS.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  aria-label={`Tag colour ${c.id}`}
                  aria-pressed={tagColor === c.hex}
                  onClick={() => setTagColor(c.hex)}
                  className={`h-4 w-4 rounded-full transition-transform ${tagColor === c.hex ? 'scale-125 ring-2 ring-ink/40 ring-offset-1 ring-offset-surface' : ''}`}
                  style={{ backgroundColor: c.hex }}
                />
              ))}
            </div>
            <button type="button" onClick={addTag} className="btn-outline">Add</button>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="f-notes">Notes</label>
            <textarea id="f-notes" rows={4} className="field resize-y" value={form.notes} onChange={set('notes')}
              placeholder="Referral from…, recruiter said…" />
          </div>
          <div>
            <label className="label" htmlFor="f-jd">Job description snapshot</label>
            <textarea id="f-jd" rows={4} className="field resize-y" value={form.jdSnapshot} onChange={set('jdSnapshot')}
              placeholder="Paste the posting here in case it gets taken down." />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={form.priority} onChange={set('priority')} className="h-4 w-4 accent-amber-500" />
          Flag as a priority
        </label>
      </form>
    </Modal>
  );
}
