import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { DndContext, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';

import Toolbar from './components/Toolbar.jsx';
import Column from './components/Column.jsx';
import JobForm from './components/JobForm.jsx';
import JobDetailPanel from './components/JobDetailPanel.jsx';
import Insights from './components/Insights.jsx';
import ToastStack from './components/Toast.jsx';
import BackupBanner from './components/BackupBanner.jsx';
import Modal from './components/Modal.jsx';
import { Plus, Upload } from './components/Icons.jsx';

import { useJobs } from './hooks/useJobs.js';
import { useToast } from './hooks/useToast.js';
import { useDensity, useTheme } from './hooks/useSettings.js';
import { getMeta, setMeta } from './db/database.js';
import { COLUMNS } from './lib/constants.js';
import { BACKUP_REMINDER_DAYS } from './lib/constants.js';
import { daysSince, nowISO } from './lib/dates.js';
import { overdueJobs } from './lib/nudges.js';
import { exportJobs, parseBackup, readFileText } from './lib/exportImport.js';

export default function App() {
  const { jobs, loading, add, update, remove, restore, importJobs } = useJobs();
  const { toasts, push, dismiss, undo } = useToast();
  const { theme, toggle: toggleTheme } = useTheme();
  const { compact, toggle: toggleDensity } = useDensity();

  const [view, setView] = useState('board');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('date-desc');

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [detail, setDetail] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [pendingImport, setPendingImport] = useState(null);

  const [lastExport, setLastExport] = useState(undefined); // undefined = not loaded
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const searchRef = useRef(null);
  const emptyImportRef = useRef(null);

  // ---- backup bookkeeping -------------------------------------------------
  useEffect(() => {
    getMeta('lastExportAt', null).then(setLastExport);
  }, []);

  const daysSinceExport = lastExport ? daysSince(lastExport) : null;
  const showBackupBanner =
    !bannerDismissed &&
    lastExport !== undefined &&
    jobs.length > 0 &&
    (lastExport === null || (daysSinceExport ?? 0) >= BACKUP_REMINDER_DAYS);

  // ---- one-time overdue notification -------------------------------------
  useEffect(() => {
    if (loading || !jobs.length) return;
    const overdue = overdueJobs(jobs);
    if (!overdue.length) return;

    let cancelled = false;
    (async () => {
      const alreadyToday = await getMeta('notifiedOn', null);
      const today = new Date().toDateString();
      if (alreadyToday === today || cancelled) return;
      if (!('Notification' in window)) return;

      let permission = Notification.permission;
      if (permission === 'default') permission = await Notification.requestPermission();
      if (permission !== 'granted' || cancelled) return;

      new Notification(`${overdue.length} follow-up${overdue.length > 1 ? 's' : ''} overdue`, {
        body: overdue.slice(0, 4).map((j) => `${j.company} — ${j.role}`).join('\n'),
        tag: 'job-tracker-overdue',
      });
      await setMeta('notifiedOn', today);
    })();

    return () => { cancelled = true; };
    // Runs once per load, after jobs settle.
  }, [loading]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- filtering & sorting ------------------------------------------------
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return jobs;
    return jobs.filter((j) =>
      (j.company || '').toLowerCase().includes(q) ||
      (j.role || '').toLowerCase().includes(q) ||
      (j.resume || '').toLowerCase().includes(q) ||
      (j.tags || []).some((t) => (t.label || '').toLowerCase().includes(q))
    );
  }, [jobs, query]);

  const byColumn = useMemo(() => {
    const cmp = {
      'date-desc': (a, b) => new Date(b.dateApplied) - new Date(a.dateApplied),
      'date-asc': (a, b) => new Date(a.dateApplied) - new Date(b.dateApplied),
      priority: (a, b) =>
        Number(b.priority) - Number(a.priority) || new Date(b.dateApplied) - new Date(a.dateApplied),
    }[sort];

    const map = Object.fromEntries(COLUMNS.map((c) => [c.id, []]));
    for (const job of filtered) (map[job.status] || map.wishlist).push(job);
    for (const id of Object.keys(map)) map[id].sort(cmp);
    return map;
  }, [filtered, sort]);

  // ---- mutations ----------------------------------------------------------
  const handleSave = useCallback(
    async (data) => {
      if (editing) {
        await update(editing.id, data);
        push({ message: 'Application updated.', tone: 'success' });
        setDetail((d) => (d && d.id === editing.id ? { ...d, ...data } : d));
      } else {
        await add(data);
        push({ message: `${data.company} added.`, tone: 'success' });
      }
      setFormOpen(false);
      setEditing(null);
    },
    [editing, add, update, push]
  );

  /** Delete is deferred: the row leaves the board, but the record is only
   *  dropped from IndexedDB once the 5s undo window closes. */
  const handleDelete = useCallback(
    async (job) => {
      setConfirmDelete(null);
      setDetail(null);
      const snapshot = { ...job };
      await remove(job.id);
      push({
        message: `${job.company} deleted.`,
        tone: 'info',
        timeout: 5000,
        onUndo: async () => {
          await restore(snapshot);
          push({ message: 'Restored.', tone: 'success' });
        },
      });
    },
    [remove, restore, push]
  );

  const handleDragEnd = useCallback(
    async ({ active, over }) => {
      if (!over) return;
      const job = jobs.find((j) => j.id === active.id);
      if (!job || job.status === over.id) return;
      const next = await update(job.id, { status: over.id });
      setDetail((d) => (d && d.id === job.id ? next : d));
      const label = COLUMNS.find((c) => c.id === over.id)?.label;
      push({ message: `${job.company} → ${label}`, tone: 'success', timeout: 2000 });
    },
    [jobs, update, push]
  );

  const handleExport = useCallback(async () => {
    const n = exportJobs(jobs);
    const at = nowISO();
    await setMeta('lastExportAt', at);
    setLastExport(at);
    setBannerDismissed(false);
    push({ message: `Exported ${n} ${n === 1 ? 'card' : 'cards'}.`, tone: 'success' });
  }, [jobs, push]);

  const handleImportFile = useCallback(
    async (file) => {
      try {
        const rows = parseBackup(await readFileText(file));
        setPendingImport(rows);
      } catch (e) {
        push({ message: e.message, tone: 'error', timeout: 6000 });
      }
    },
    [push]
  );

  const runImport = useCallback(
    async (mode) => {
      const rows = pendingImport;
      setPendingImport(null);
      const all = await importJobs(rows, mode);
      push({
        message: `Imported ${rows.length} ${rows.length === 1 ? 'card' : 'cards'} — ${all.length} total.`,
        tone: 'success',
      });
    },
    [pendingImport, importJobs, push]
  );

  // ---- keyboard shortcuts -------------------------------------------------
  useEffect(() => {
    const onKey = (e) => {
      const el = e.target;
      const typing = el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA' || el?.tagName === 'SELECT' || el?.isContentEditable;
      const busy = formOpen || detail || confirmDelete || pendingImport;

      if (e.key === '/' && !typing && !busy) {
        e.preventDefault();
        setView('board');
        searchRef.current?.focus();
      }
      if ((e.key === 'n' || e.key === 'N') && !typing && !busy && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setEditing(null);
        setFormOpen(true);
      }
      if (e.key === 'Escape' && typing && el === searchRef.current) {
        setQuery('');
        el.blur();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [formOpen, detail, confirmDelete, pendingImport]);

  const sensors = useSensors(
    // A small drag threshold so a click on the card still opens the panel.
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const counts = { total: jobs.length, overdue: overdueJobs(jobs).length };

  return (
    <div className="flex h-full flex-col bg-surface-sunken">
      <Toolbar
        view={view} onView={setView}
        query={query} onQuery={setQuery} searchRef={searchRef}
        sort={sort} onSort={setSort}
        theme={theme} onToggleTheme={toggleTheme}
        compact={compact} onToggleDensity={toggleDensity}
        onNew={() => { setEditing(null); setFormOpen(true); }}
        onExport={handleExport}
        onImportFile={handleImportFile}
        counts={counts}
      />

      {showBackupBanner && (
        <BackupBanner
          daysSinceExport={daysSinceExport}
          onExport={handleExport}
          onDismiss={() => setBannerDismissed(true)}
        />
      )}

      <main className="min-h-0 flex-1">
        {loading ? (
          <p className="grid h-full place-items-center text-sm text-ink-faint">Loading…</p>
        ) : view === 'insights' ? (
          <Insights jobs={jobs} />
        ) : jobs.length === 0 ? (
          /* First run: six empty columns give no hint that Import exists. */
          <div className="grid h-full place-items-center px-6">
            <div className="max-w-sm text-center">
              <h2 className="text-base font-semibold text-ink">Your board is empty</h2>
              <p className="mt-1.5 text-sm text-ink-muted">
                Add your first application, or import a backup — including the
                <code className="mx-1 rounded bg-surface-sunken px-1 py-0.5 text-xs">seed-data.json</code>
                built from your JobKitAI postings.
              </p>
              <div className="mt-4 flex justify-center gap-2">
                <button onClick={() => { setEditing(null); setFormOpen(true); }} className="btn-primary">
                  <Plus size={15} /> New application
                </button>
                <button onClick={() => emptyImportRef.current?.click()} className="btn-outline">
                  <Upload size={15} /> Import backup
                </button>
                <input
                  ref={emptyImportRef}
                  type="file"
                  accept="application/json,.json"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleImportFile(f);
                    e.target.value = '';
                  }}
                />
              </div>
            </div>
          </div>
        ) : (
          <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
            <div className="scroll-slim flex h-full gap-3 overflow-x-auto px-4 py-3">
              {COLUMNS.map((c) => (
                <Column
                  key={c.id}
                  column={c}
                  jobs={byColumn[c.id] || []}
                  compact={compact}
                  onOpenJob={setDetail}
                  onTogglePriority={(job) => update(job.id, { priority: !job.priority })}
                />
              ))}
            </div>
          </DndContext>
        )}
      </main>

      <JobForm
        open={formOpen}
        job={editing}
        allJobs={jobs}
        onClose={() => { setFormOpen(false); setEditing(null); }}
        onSave={handleSave}
      />

      <JobDetailPanel
        open={Boolean(detail)}
        job={detail}
        onClose={() => setDetail(null)}
        onUpdate={async (id, patch) => {
          const next = await update(id, patch);
          setDetail(next);
        }}
        onEdit={(job) => { setDetail(null); setEditing(job); setFormOpen(true); }}
        onDelete={(job) => setConfirmDelete(job)}
      />

      <Modal
        open={Boolean(confirmDelete)}
        onClose={() => setConfirmDelete(null)}
        title="Delete this application?"
        width="max-w-sm"
        footer={
          <>
            <button onClick={() => setConfirmDelete(null)} className="btn-outline">Cancel</button>
            <button onClick={() => handleDelete(confirmDelete)} className="btn-danger">Delete</button>
          </>
        }
      >
        <p className="text-sm text-ink-muted">
          <strong className="text-ink">{confirmDelete?.company}</strong> — {confirmDelete?.role} will be removed.
          You'll get five seconds to undo it.
        </p>
      </Modal>

      <Modal
        open={Boolean(pendingImport)}
        onClose={() => setPendingImport(null)}
        title="Import backup"
        subtitle={`${pendingImport?.length ?? 0} cards found in that file`}
        width="max-w-md"
        footer={
          <>
            <button onClick={() => setPendingImport(null)} className="btn-outline">Cancel</button>
            <button onClick={() => runImport('replace')} className="btn-danger">Replace all</button>
            <button onClick={() => runImport('merge')} className="btn-primary">Merge</button>
          </>
        }
      >
        <p className="text-sm text-ink-muted">
          <strong className="text-ink">Merge</strong> keeps your current {jobs.length} cards and adds these,
          overwriting any that share an id.{' '}
          <strong className="text-ink">Replace all</strong> deletes everything currently on the board first —
          that cannot be undone.
        </p>
      </Modal>

      <ToastStack toasts={toasts} onUndo={undo} onDismiss={dismiss} />
    </div>
  );
}
