import { useMemo, useState } from 'react';
import { ChartCard, Funnel, RankedBars, StatTile, TimeBars } from './charts.jsx';
import {
  avgDaysPerStage, funnel, resumePerformance, submissionsOver, topCompanies,
} from '../lib/analytics.js';
import { overdueJobs } from '../lib/nudges.js';
import { COLUMN_BY_ID } from '../lib/constants.js';

export default function Insights({ jobs }) {
  const [grain, setGrain] = useState('week');
  const [showTable, setShowTable] = useState(false);

  const series = useMemo(() => submissionsOver(jobs, grain, grain === 'week' ? 12 : 6), [jobs, grain]);
  const stages = useMemo(() => funnel(jobs), [jobs]);
  const dwell = useMemo(() => avgDaysPerStage(jobs), [jobs]);
  const companies = useMemo(() => topCompanies(jobs), [jobs]);
  const resumes = useMemo(() => resumePerformance(jobs), [jobs]);
  const overdue = useMemo(() => overdueJobs(jobs), [jobs]);

  const active = jobs.filter((j) => !['rejected', 'offer'].includes(j.status)).length;
  const totalSubmitted = stages[0].count;

  if (jobs.length === 0) {
    return (
      <div className="grid h-full place-items-center px-6 py-16 text-center">
        <div>
          <p className="text-sm font-medium text-ink">Nothing to chart yet</p>
          <p className="mt-1 text-xs text-ink-muted">Add a few applications and the numbers will show up here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="scroll-slim h-full overflow-y-auto px-4 py-4">
      <div className="mx-auto max-w-5xl space-y-4">
        {/* Headline numbers — no plot, so no hover layer. */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile label="Tracked" value={jobs.length} sub={`${active} still open`} />
          <StatTile label="Submitted" value={totalSubmitted} sub="left the wishlist" />
          <StatTile label="Interviewing" value={stages[1].count} sub={`${stages[1].ofTop}% of submitted`} />
          <StatTile
            label="Overdue follow-ups"
            value={overdue.length}
            sub={overdue.length ? 'needs a nudge' : 'all clear'}
            tone={overdue.length ? 'text-rose-500' : 'text-ink'}
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title="Applications submitted"
            hint={grain === 'week' ? 'Last 12 weeks' : 'Last 6 months'}
          >
            <div className="mb-3 flex gap-1">
              {['week', 'month'].map((g) => (
                <button
                  key={g}
                  onClick={() => setGrain(g)}
                  aria-pressed={grain === g}
                  className={`btn px-2 py-0.5 text-xs ${grain === g ? 'bg-surface-sunken text-ink' : 'text-ink-muted'}`}
                >
                  {g === 'week' ? 'Weekly' : 'Monthly'}
                </button>
              ))}
            </div>
            <TimeBars data={series} />
          </ChartCard>

          <ChartCard
            title="Conversion funnel"
            hint="Counted from status history, so a card that skipped a column still counts."
            empty={totalSubmitted === 0 ? 'No applications submitted yet.' : null}
          >
            <Funnel stages={stages} />
          </ChartCard>

          <ChartCard
            title="Average days in each stage"
            hint="Only completed stages count — the stage a card sits in now has no end date yet."
            empty={dwell.length === 0 ? 'Cards need to move between columns before this can be measured.' : null}
          >
            <RankedBars
              rows={dwell.map((d) => ({
                name: d.stage,
                value: d.days,
                sub: `${d.samples} ${d.samples === 1 ? 'move' : 'moves'}`,
                color: COLUMN_BY_ID[d.id]?.accent,
              }))}
              unit="d"
            />
          </ChartCard>

          <ChartCard
            title="Most-applied companies"
            empty={companies.length === 0 ? 'No companies recorded yet.' : null}
          >
            <RankedBars rows={companies} />
          </ChartCard>
        </div>

        <ChartCard
          title="Response rate by resume"
          hint="A response means the card reached interview or offer. Low-volume rows are noisy — check the send count."
          empty={resumes.length === 0 ? 'Record which resume you used on each application to compare them.' : null}
        >
          <RankedBars
            rows={resumes.map((r) => ({
              name: r.name,
              value: r.rate,
              sub: `${r.responded} of ${r.sent} sent`,
            }))}
            unit="%"
            max={100}
          />

          <button
            onClick={() => setShowTable((s) => !s)}
            className="btn-ghost mt-3 px-0 text-xs underline-offset-2 hover:underline"
            aria-expanded={showTable}
          >
            {showTable ? 'Hide' : 'Show'} the numbers
          </button>

          {showTable && (
            <table className="mt-2 w-full text-xs">
              <thead>
                <tr className="border-b border-edge text-left text-ink-muted">
                  <th className="py-1 font-medium">Resume</th>
                  <th className="py-1 text-right font-medium">Sent</th>
                  <th className="py-1 text-right font-medium">Responses</th>
                  <th className="py-1 text-right font-medium">Rate</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {resumes.map((r) => (
                  <tr key={r.name} className="border-b border-edge/60">
                    <td className="py-1 text-ink">{r.name}</td>
                    <td className="py-1 text-right text-ink-muted">{r.sent}</td>
                    <td className="py-1 text-right text-ink-muted">{r.responded}</td>
                    <td className="py-1 text-right font-medium text-ink">{r.rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ChartCard>
      </div>
    </div>
  );
}
