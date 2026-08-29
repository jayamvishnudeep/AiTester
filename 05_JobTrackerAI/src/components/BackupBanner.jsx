import { Close, Download, Warning } from './Icons.jsx';

export default function BackupBanner({ daysSinceExport, onExport, onDismiss }) {
  return (
    <div className="flex items-center gap-3 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-800 dark:text-amber-300">
      <Warning size={15} />
      <p className="flex-1">
        {daysSinceExport === null
          ? "You haven't backed up yet. Everything lives in this browser only — an export keeps it safe."
          : `Last backup was ${daysSinceExport} days ago. Your data lives in this browser only.`}
      </p>
      <button onClick={onExport} className="btn px-2 py-1 text-xs font-semibold underline-offset-2 hover:underline">
        <Download size={13} /> Export now
      </button>
      <button onClick={onDismiss} aria-label="Dismiss backup reminder" className="rounded p-1 hover:bg-amber-500/20">
        <Close size={14} />
      </button>
    </div>
  );
}
