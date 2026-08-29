import { useRef } from 'react';
import { Board, Chart, Download, Moon, Plus, Rows, Search, Sun, Upload } from './Icons.jsx';
import { SORT_OPTIONS } from '../lib/constants.js';

export default function Toolbar({
  view, onView,
  query, onQuery, searchRef,
  sort, onSort,
  theme, onToggleTheme,
  compact, onToggleDensity,
  onNew, onExport, onImportFile,
  counts,
}) {
  const fileRef = useRef(null);

  return (
    <header className="sticky top-0 z-30 border-b border-edge bg-surface/85 backdrop-blur">
      <div className="flex flex-wrap items-center gap-2 px-4 py-2.5">
        <h1 className="mr-1 text-sm font-semibold tracking-tight text-ink">Job Tracker</h1>
        <span className="hidden text-xs text-ink-faint sm:inline">
          {counts.total} {counts.total === 1 ? 'role' : 'roles'}
          {counts.overdue > 0 && <span className="text-rose-500"> · {counts.overdue} overdue</span>}
        </span>

        {/* View switch */}
        <div className="ml-auto flex items-center rounded-lg border border-edge p-0.5">
          <button
            onClick={() => onView('board')}
            aria-pressed={view === 'board'}
            className={`btn px-2 py-1 text-xs ${view === 'board' ? 'bg-surface-sunken text-ink' : 'text-ink-muted'}`}
          >
            <Board size={14} /> Board
          </button>
          <button
            onClick={() => onView('insights')}
            aria-pressed={view === 'insights'}
            className={`btn px-2 py-1 text-xs ${view === 'insights' ? 'bg-surface-sunken text-ink' : 'text-ink-muted'}`}
          >
            <Chart size={14} /> Insights
          </button>
        </div>

        <button onClick={onToggleDensity} className="btn-ghost p-1.5" title={compact ? 'Comfortable rows' : 'Compact rows'}
          aria-label={compact ? 'Switch to comfortable density' : 'Switch to compact density'}>
          <Rows size={16} />
        </button>

        <button onClick={onToggleTheme} className="btn-ghost p-1.5"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        <button onClick={onExport} className="btn-ghost p-1.5" title="Export backup" aria-label="Export backup">
          <Download size={16} />
        </button>

        <button onClick={() => fileRef.current?.click()} className="btn-ghost p-1.5" title="Import backup" aria-label="Import backup">
          <Upload size={16} />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onImportFile(file);
            e.target.value = '';
          }}
        />

        <button onClick={onNew} className="btn-primary">
          <Plus size={15} /> New
          <kbd className="ml-1 hidden rounded bg-white/20 px-1 text-[10px] sm:inline">N</kbd>
        </button>
      </div>

      {view === 'board' && (
        <div className="flex flex-wrap items-center gap-2 border-t border-edge px-4 py-2">
          <div className="relative min-w-[12rem] flex-1 sm:max-w-sm">
            <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint">
              <Search size={15} />
            </span>
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => onQuery(e.target.value)}
              placeholder="Search company, role or tag…"
              aria-label="Search applications"
              className="field py-1.5 pl-8 pr-8 text-sm"
            />
            <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-edge px-1 text-[10px] text-ink-faint sm:block">
              /
            </kbd>
          </div>

          <label className="flex items-center gap-1.5 text-xs text-ink-muted">
            Sort
            <select value={sort} onChange={(e) => onSort(e.target.value)} className="field w-auto py-1 text-xs">
              {SORT_OPTIONS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select>
          </label>
        </div>
      )}
    </header>
  );
}
