// Kanban columns. `id` is what gets stored on the card as `status`.
// Accents resolve through CSS variables so light and dark each get their own
// validated step (see the palette notes in index.css).
export const COLUMNS = [
  { id: 'wishlist',  label: 'Wishlist',  accent: 'var(--col-wishlist)',  empty: 'Nothing saved yet — add roles you want to go after.' },
  { id: 'applied',   label: 'Applied',   accent: 'var(--col-applied)',   empty: 'No applications out yet.' },
  { id: 'followup',  label: 'Follow-up', accent: 'var(--col-followup)',  empty: 'No follow-ups in flight.' },
  { id: 'interview', label: 'Interview', accent: 'var(--col-interview)', empty: 'No interviews scheduled — yet.' },
  { id: 'offer',     label: 'Offer',     accent: 'var(--col-offer)',     empty: 'No offers yet — keep going!' },
  { id: 'rejected',  label: 'Rejected',  accent: 'var(--col-rejected)',  empty: 'Nothing here. Long may it last.' },
];

export const COLUMN_BY_ID = Object.fromEntries(COLUMNS.map((c) => [c.id, c]));

export const DEFAULT_ROUNDS = ['Phone Screen', 'Technical', 'Onsite', 'HR', 'Final'];

// Tag chip colours. Stored per card as fixed hex (user data, so they can't be
// theme variables) — these are mid-lightness steps that stay readable as text
// on their own 12% tint in both light and dark.
export const TAG_COLORS = [
  { id: 'blue',   hex: '#2a78d6' },
  { id: 'orange', hex: '#eb6834' },
  { id: 'aqua',   hex: '#1baf7a' },
  { id: 'yellow', hex: '#eda100' },
  { id: 'pink',   hex: '#e87ba4' },
  { id: 'violet', hex: '#8b7cf0' },
];

// Thresholds that drive the nudge badges.
export const STALE_APPLIED_DAYS = 7;
export const STALE_WISHLIST_DAYS = 14;
export const BACKUP_REMINDER_DAYS = 30;

export const SORT_OPTIONS = [
  { id: 'date-desc', label: 'Newest first' },
  { id: 'date-asc',  label: 'Oldest first' },
  { id: 'priority',  label: 'Priority first' },
];
