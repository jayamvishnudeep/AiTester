import { useId, useState } from 'react';

/**
 * Small chart primitives built from divs and SVG — no charting dependency.
 * Shared rules: thin marks, 4px rounded data-ends anchored to the baseline,
 * a 2px surface gap between adjacent fills, recessive axes, and a hover
 * tooltip on every mark.
 */

function Tooltip({ text, x, y }) {
  if (!text) return null;
  return (
    <div
      className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap
                 rounded-md border border-edge bg-surface-raised px-2 py-1 text-xs font-medium text-ink shadow-lg"
      style={{ left: x, top: y - 6 }}
    >
      {text}
    </div>
  );
}

export function ChartCard({ title, hint, children, empty }) {
  return (
    <section className="card-surface p-4">
      <header className="mb-3">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {hint && <p className="mt-0.5 text-xs text-ink-muted">{hint}</p>}
      </header>
      {empty ? <p className="py-8 text-center text-xs text-ink-faint">{empty}</p> : children}
    </section>
  );
}

/**
 * Vertical bars over time. Single series, so one hue and no legend — the
 * title names it. Only the peak and the latest bar get a value label, to
 * avoid a number on every mark.
 */
export function TimeBars({ data, label = 'applications' }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  const gridId = useId();

  return (
    <div className="relative">
      <Tooltip text={hover?.text} x={hover?.x} y={hover?.y} />
      <div className="flex h-36 items-end gap-[2px]" role="img"
        aria-label={`${label} per period, ${data.length} periods, peak ${max}`}>
        {data.map((d, i) => {
          const pct = (d.value / max) * 100;
          const isPeak = d.value === max && d.value > 0;
          const isLast = i === data.length - 1;
          return (
            <div key={d.key} className="group relative flex h-full flex-1 flex-col justify-end">
              {(isPeak || (isLast && d.value > 0)) && (
                <span className="mb-0.5 text-center text-[10px] font-semibold tabular-nums text-ink-muted">
                  {d.value}
                </span>
              )}
              <div
                onMouseEnter={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  const p = e.currentTarget.closest('.relative').getBoundingClientRect();
                  setHover({ text: `${d.label}: ${d.value} ${label}`, x: r.left - p.left + r.width / 2, y: r.top - p.top });
                }}
                onMouseLeave={() => setHover(null)}
                className="w-full rounded-t transition-opacity hover:opacity-80"
                style={{
                  height: `${Math.max(pct, d.value > 0 ? 3 : 0)}%`,
                  minHeight: d.value > 0 ? 3 : 0,
                  background: 'var(--series-1)',
                  borderRadius: '4px 4px 0 0',
                }}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex gap-[2px] border-t pt-1" style={{ borderColor: 'var(--axis)' }}>
        {data.map((d, i) => (
          <span key={d.key} className="flex-1 text-center text-[9px] tabular-nums text-ink-faint">
            {i % 2 === 0 || data.length <= 8 ? d.label : ''}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Applied → Interview → Offer. An ordinal blue ramp reinforces the narrowing;
 * each stage is directly labelled, so colour is never the only cue.
 */
export function Funnel({ stages }) {
  const top = Math.max(1, stages[0]?.count || 0);
  const ramp = ['var(--funnel-1)', 'var(--funnel-2)', 'var(--funnel-3)'];

  return (
    <div className="space-y-2.5">
      {stages.map((s, i) => (
        <div key={s.stage}>
          <div className="mb-1 flex items-baseline justify-between text-xs">
            <span className="font-medium text-ink">{s.stage}</span>
            <span className="tabular-nums text-ink-muted">
              <strong className="text-ink">{s.count}</strong>
              {i > 0 && <span className="ml-1.5 text-ink-faint">{s.ofPrev}% of previous</span>}
            </span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-surface-sunken">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${(s.count / top) * 100}%`, background: ramp[i] }}
            />
          </div>
        </div>
      ))}
      {stages[0]?.count > 0 && (
        <p className="pt-1 text-xs text-ink-muted">
          Overall: <strong className="text-ink">{stages[2]?.ofTop ?? 0}%</strong> of applications reached an offer.
        </p>
      )}
    </div>
  );
}

/**
 * Horizontal bars for a named list — stages, companies, resumes. Each row
 * carries its own label and value, so a single hue is correct here; where a
 * per-row colour is passed (stage identity) the label still does the work.
 */
export function RankedBars({ rows, unit = '', max: maxOverride }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, maxOverride ?? Math.max(...rows.map((r) => r.value)));

  return (
    <div className="relative space-y-2">
      <Tooltip text={hover?.text} x={hover?.x} y={hover?.y} />
      {rows.map((r) => (
        <div key={r.name} className="grid grid-cols-[7.5rem_1fr_auto] items-center gap-2">
          <span className="truncate text-xs text-ink-muted" title={r.name}>{r.name}</span>
          <div className="h-2.5 overflow-hidden rounded-full bg-surface-sunken">
            <div
              onMouseEnter={(e) => {
                const b = e.currentTarget.getBoundingClientRect();
                const p = e.currentTarget.closest('.relative').getBoundingClientRect();
                setHover({ text: `${r.name}: ${r.value}${unit}${r.sub ? ` · ${r.sub}` : ''}`, x: b.left - p.left + b.width / 2, y: b.top - p.top });
              }}
              onMouseLeave={() => setHover(null)}
              className="h-full rounded-full transition-all hover:opacity-80"
              style={{ width: `${(r.value / max) * 100}%`, background: r.color || 'var(--series-1)' }}
            />
          </div>
          <span className="w-12 text-right text-xs font-medium tabular-nums text-ink">
            {r.value}{unit}
          </span>
        </div>
      ))}
    </div>
  );
}

/** A single headline number — no plot, so no hover layer. */
export function StatTile({ label, value, sub, tone }) {
  return (
    <div className="card-surface px-3 py-2.5">
      <p className="text-xs text-ink-muted">{label}</p>
      <p className={`mt-0.5 text-xl font-semibold ${tone || 'text-ink'}`}>{value}</p>
      {sub && <p className="text-[11px] text-ink-faint">{sub}</p>}
    </div>
  );
}
