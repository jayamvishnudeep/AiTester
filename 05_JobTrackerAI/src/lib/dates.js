// Date helpers. Everything is stored as an ISO string; these keep the
// formatting and "how long ago" logic in one place.

export const nowISO = () => new Date().toISOString();

/** ISO string for today at local midnight — the default for date inputs. */
export function todayISO() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

/** `YYYY-MM-DD` for <input type="date">, in local time (not UTC). */
export function toDateInput(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Parse `YYYY-MM-DD` from a date input back to an ISO string at local midnight. */
export function fromDateInput(value) {
  if (!value) return null;
  const [y, m, d] = value.split('-').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d).toISOString();
}

/** Whole days elapsed since `iso`. Negative means the date is in the future. */
export function daysSince(iso) {
  if (!iso) return null;
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return null;
  const a = new Date(then.getFullYear(), then.getMonth(), then.getDate());
  const n = new Date();
  const b = new Date(n.getFullYear(), n.getMonth(), n.getDate());
  return Math.round((b - a) / 86400000);
}

/** "today" / "3d ago" / "2mo ago" — compact enough for a card face. */
export function relativeDays(iso) {
  const d = daysSince(iso);
  if (d === null) return '';
  if (d === 0) return 'today';
  if (d === 1) return 'yesterday';
  if (d < 0) return `in ${Math.abs(d)}d`;
  if (d < 30) return `${d}d ago`;
  if (d < 365) return `${Math.floor(d / 30)}mo ago`;
  return `${Math.floor(d / 365)}y ago`;
}

/** "12 Aug 2025" */
export function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

/** "12 Aug, 14:30" — for the status history timeline. */
export function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) +
    ', ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

/** A follow-up date is overdue once the day itself has passed. */
export function isOverdue(iso) {
  if (!iso) return false;
  const d = daysSince(iso);
  return d !== null && d > 0;
}

/** ISO week key like `2025-W34`, used to bucket applications per week. */
export function weekKey(iso) {
  const d = new Date(iso);
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((t - yearStart) / 86400000 + 1) / 7);
  return `${t.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

/** `2025-08` month key. */
export function monthKey(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** Short label for a month key: "Aug 25". */
export function monthLabel(key) {
  const [y, m] = key.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: 'short', year: '2-digit' });
}

/** Short label for a week key: "W34". */
export function weekLabel(key) {
  return key.split('-')[1];
}
