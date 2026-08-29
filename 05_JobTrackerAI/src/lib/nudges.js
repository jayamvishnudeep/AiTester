import { daysSince, isOverdue } from './dates.js';
import { STALE_APPLIED_DAYS, STALE_WISHLIST_DAYS } from './constants.js';

/** When the card last moved — falls back to creation for never-moved cards. */
export function lastMovedAt(job) {
  const h = job.history || [];
  return h.length ? h[h.length - 1].at : job.createdAt;
}

export function daysInCurrentStage(job) {
  return daysSince(lastMovedAt(job));
}

/** Sitting in Applied with no movement for a week or more. */
export function isStaleApplied(job) {
  return job.status === 'applied' && (daysInCurrentStage(job) ?? 0) >= STALE_APPLIED_DAYS;
}

/** Saved to Wishlist a fortnight ago and never actually applied to. */
export function isStaleWishlist(job) {
  return job.status === 'wishlist' && (daysInCurrentStage(job) ?? 0) >= STALE_WISHLIST_DAYS;
}

/** The follow-up-by date has passed and the card is still open. */
export function isFollowUpOverdue(job) {
  if (job.status === 'rejected' || job.status === 'offer') return false;
  return isOverdue(job.followUpBy);
}

export function overdueJobs(jobs) {
  return jobs.filter(isFollowUpOverdue);
}

/** Every nudge that applies to a card, as small renderable descriptors. */
export function nudgesFor(job) {
  const out = [];
  if (isFollowUpOverdue(job)) {
    out.push({ id: 'overdue', label: 'Follow-up overdue', tone: 'rose' });
  }
  if (isStaleApplied(job)) {
    out.push({ id: 'stale', label: `${daysInCurrentStage(job)}d no reply`, tone: 'amber' });
  }
  if (isStaleWishlist(job)) {
    out.push({ id: 'idle', label: 'Sitting idle', tone: 'slate' });
  }
  return out;
}

/** Interview progress for the card face, e.g. "2/4 rounds". */
export function roundProgress(job) {
  const rounds = job.rounds || [];
  const done = rounds.filter((r) => r.done).length;
  return { done, total: rounds.length };
}
