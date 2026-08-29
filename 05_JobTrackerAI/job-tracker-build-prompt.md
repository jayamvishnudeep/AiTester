# Prompt: Build a Local-First Job Tracker AI (React + Vite + IndexedDB)

Create a local-first Job Tracker as a single-page React application scaffolded with Vite. All data must persist in the browser using IndexedDB (use the `idb` library for a cleaner async API). No backend or authentication is needed — everything runs on localhost / fully client-side.

## Tech Stack & Constraints

- React 18+ with functional components and hooks
- Vite for build tooling
- Tailwind CSS for styling (clean, minimal UI)
- `idb` npm package for IndexedDB wrapper
- `@dnd-kit/core` for drag-and-drop
- No external database, no API calls, no auth — 100% local and offline-capable
- Responsive layout (usable on laptop + tablet)
- Optional: browser Notifications API for follow-up reminders

## Data Model

Each job card stores:

- Company name (text, required)
- Job title / role (text, required)
- LinkedIn job URL (URL, clickable)
- Resume used (text / dropdown of previously used resume names, e.g., "SDE_Resume_v3", "QA_Lead_Resume")
- Date applied (auto-set on creation, editable)
- Salary range (optional text, e.g., "₹25-30 LPA" or "$150-180K")
- Notes (optional textarea for recruiter name, referral info, etc.)
- Status (maps to Kanban column)
- Recruiter contact (optional: name + email/LinkedIn, separate field from Notes)
- Tags/labels (optional array, e.g. "Remote", "Referral", "Dream Company" — each with a assignable color)
- Priority flag (optional boolean/star)
- Interview round checklist (optional subtasks: Phone Screen → Technical → Onsite → HR → Final, each with a done/not-done state)
- Job description snapshot (optional pasted text, in case the original posting is taken down)
- Follow-up-by date (optional, used for reminders)
- Status history log (auto-generated array of {status, timestamp} entries every time the card's status changes — do not let the user edit this directly)

## Kanban Columns (drag-and-drop between them)

1. Wishlist — Saved jobs I haven't applied to yet
2. Applied — Application submitted
3. Follow-up — Followed up with recruiter / referral
4. Interview — Currently in interview rounds
5. Offer — Received an offer
6. Rejected — Got a rejection

## Core Features

- Drag-and-drop cards between columns using `@dnd-kit/core`
- Add new job via a modal/slide-over form, with validation on required fields before saving
- Edit any card inline or via modal
- Delete a card with a confirmation dialog, followed by a 5-second "Undo" toast before the delete is finalized
- Card shows: company name, role, resume tag, days since applied, tags/labels as color chips, priority star if flagged, and a clickable LinkedIn icon/link
- Column headers show the count of cards in each column
- Search/filter bar to find jobs by company name, role, or tag
- Sort cards within a column by date applied (newest/oldest) or by priority
- All CRUD operations persist instantly to IndexedDB
- Warn (non-blocking) if a new card's company + role combination already exists, to catch accidental duplicates

## Analytics & Insights Dashboard

Add a separate "Insights" view/tab showing:

- Applications submitted per week/month (line or bar chart)
- Conversion funnel: Applied → Interview → Offer (percentages at each stage)
- Average days spent in each column/stage (to highlight where applications tend to stall)
- Top companies/roles applied to (simple bar chart or tag list)
- Response rate broken down by resume version used

Use a lightweight charting approach (e.g. simple SVG/CSS bars, or a small library like `recharts` if dependencies are acceptable) — keep it clean and minimal, not enterprise-dashboard heavy.

## Reminders & Follow-up Nudges

- If a card has been in "Applied" with no status change for 7+ days, visually flag it (e.g. subtle badge or border color)
- If a card has a "follow-up-by" date and that date has passed, show an overdue badge
- On app load, optionally trigger a browser notification (via Notifications API, with permission request) listing any overdue follow-ups
- Visually flag "Wishlist" items that have sat untouched for 2+ weeks without being moved to Applied

## Interview Round Tracker

- Within a card's detail view, allow adding/checking off interview rounds as a simple checklist (Phone Screen, Technical, Onsite, HR, Final — customizable labels)
- Show progress (e.g. "2/4 rounds complete") on the card face when in the Interview column

## Data Robustness

- Export all data as a JSON file for backup
- Import a JSON file to restore/merge data
- Show a dismissible banner reminding the user to back up if no export has been performed in 30+ days
- Maintain the auto-generated status history log per card and display it as a simple timeline in the card detail view (e.g. "Moved to Interview — Aug 12")

## UI/UX Requirements

- Clean, professional look — think Linear or Trello-minimal
- Light/dark mode toggle, persisted across sessions
- Each column should scroll independently
- Cards should have a subtle left-border color accent per status, plus optional tag color chips
- Toast notifications for save/delete/import/export confirmations rather than silent state changes
- Empty-state messaging per column (e.g. "No offers yet — keep going!")
- Keyboard shortcuts: `N` to open the new-job modal, `/` to focus the search bar, `Esc` to close any open modal
- Card detail view should open as a full side-panel (not just a small modal), showing all fields, the interview checklist, and the status history timeline
- Compact vs. comfortable card density toggle in settings

## Build Order (suggested phases)

1. Scaffold Vite + React + Tailwind, set up IndexedDB schema via `idb`
2. Build core Kanban board with static columns and card CRUD (no drag-and-drop yet)
3. Add drag-and-drop between columns, wire status changes to update the status history log
4. Add search/filter/sort
5. Add tags, priority flag, recruiter contact, interview checklist, JD snapshot fields
6. Add Insights/Analytics tab
7. Add reminders/follow-up flagging and optional browser notifications
8. Add JSON export/import and the backup-reminder banner
9. Add light/dark mode, keyboard shortcuts, toasts, empty states, and density toggle
10. Final responsive pass for tablet/laptop widths
