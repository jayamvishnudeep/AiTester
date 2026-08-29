import { COLUMNS } from './constants.js';
import { monthKey, monthLabel, weekKey, weekLabel } from './dates.js';

/** A card counts as "applied" once it has ever left the wishlist. */
const everReached = (job, statuses) =>
  (job.history || []).some((h) => statuses.includes(h.status));

const APPLIED_ONWARD = ['applied', 'followup', 'interview', 'offer', 'rejected'];
const INTERVIEW_ONWARD = ['interview', 'offer'];

/** The timestamp a card first entered `status`, or null. */
function firstEntry(job, status) {
  const hit = (job.history || []).find((h) => h.status === status);
  return hit ? hit.at : null;
}

/**
 * Applications submitted per period. Uses the moment the card first reached
 * an applied-or-later status, not `dateApplied`, so wishlist edits don't
 * shift the history.
 */
export function submissionsOver(jobs, granularity = 'week', buckets = 12) {
  const keyOf = granularity === 'month' ? monthKey : weekKey;
  const labelOf = granularity === 'month' ? monthLabel : weekLabel;

  const counts = new Map();
  for (const job of jobs) {
    const at = APPLIED_ONWARD.map((s) => firstEntry(job, s)).filter(Boolean).sort()[0];
    if (!at) continue;
    const k = keyOf(at);
    counts.set(k, (counts.get(k) || 0) + 1);
  }

  // Build a continuous axis so gaps read as zero rather than disappearing.
  const series = [];
  const cursor = new Date();
  for (let i = buckets - 1; i >= 0; i--) {
    const d = new Date(cursor);
    if (granularity === 'month') d.setMonth(d.getMonth() - i);
    else d.setDate(d.getDate() - i * 7);
    const k = keyOf(d.toISOString());
    series.push({ key: k, label: labelOf(k), value: counts.get(k) || 0 });
  }
  return series;
}

/** Applied → Interview → Offer, with conversion rates between stages. */
export function funnel(jobs) {
  const applied = jobs.filter((j) => everReached(j, APPLIED_ONWARD)).length;
  const interviewed = jobs.filter((j) => everReached(j, INTERVIEW_ONWARD)).length;
  const offered = jobs.filter((j) => everReached(j, ['offer'])).length;

  const pct = (n, d) => (d > 0 ? Math.round((n / d) * 100) : 0);
  return [
    { stage: 'Applied', count: applied, ofPrev: 100, ofTop: 100 },
    { stage: 'Interview', count: interviewed, ofPrev: pct(interviewed, applied), ofTop: pct(interviewed, applied) },
    { stage: 'Offer', count: offered, ofPrev: pct(offered, interviewed), ofTop: pct(offered, applied) },
  ];
}

/**
 * Mean days a card sits in each stage. Only closed intervals count — the
 * stage a card currently occupies has no end yet, so counting it would
 * understate the average.
 */
export function avgDaysPerStage(jobs) {
  const totals = new Map();
  for (const job of jobs) {
    const h = [...(job.history || [])].sort((a, b) => new Date(a.at) - new Date(b.at));
    for (let i = 0; i < h.length - 1; i++) {
      const days = (new Date(h[i + 1].at) - new Date(h[i].at)) / 86400000;
      if (!Number.isFinite(days) || days < 0) continue;
      const prev = totals.get(h[i].status) || { sum: 0, n: 0 };
      totals.set(h[i].status, { sum: prev.sum + days, n: prev.n + 1 });
    }
  }
  return COLUMNS.map((c) => {
    const t = totals.get(c.id);
    return {
      stage: c.label,
      id: c.id,
      accent: c.accent,
      days: t && t.n ? Math.round((t.sum / t.n) * 10) / 10 : 0,
      samples: t ? t.n : 0,
    };
  }).filter((r) => r.samples > 0);
}

/** Most-applied-to companies. */
export function topCompanies(jobs, limit = 6) {
  const counts = new Map();
  for (const j of jobs) {
    const name = (j.company || '').trim();
    if (name) counts.set(name, (counts.get(name) || 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name))
    .slice(0, limit);
}

/**
 * Response rate per resume version. "Response" means the card reached
 * interview or offer — a rejection is an outcome, not a response worth
 * crediting to a resume.
 */
export function resumePerformance(jobs) {
  const byResume = new Map();
  for (const j of jobs) {
    const name = (j.resume || '').trim() || 'No resume recorded';
    if (!everReached(j, APPLIED_ONWARD)) continue;
    const row = byResume.get(name) || { name, sent: 0, responded: 0 };
    row.sent += 1;
    if (everReached(j, INTERVIEW_ONWARD)) row.responded += 1;
    byResume.set(name, row);
  }
  return [...byResume.values()]
    .map((r) => ({ ...r, rate: r.sent ? Math.round((r.responded / r.sent) * 100) : 0 }))
    .sort((a, b) => b.sent - a.sent || a.name.localeCompare(b.name));
}

/** Distinct resume names already used, for the form's datalist. */
export function knownResumes(jobs) {
  return [...new Set(jobs.map((j) => (j.resume || '').trim()).filter(Boolean))].sort();
}

/** Distinct tag labels in use, for the search filter. */
export function knownTags(jobs) {
  const set = new Map();
  for (const j of jobs) for (const t of j.tags || []) if (t?.label) set.set(t.label, t);
  return [...set.values()];
}
