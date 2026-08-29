import { Check, Close, Warning } from './Icons.jsx';

const TONES = {
  info: 'border-edge',
  success: 'border-emerald-500/40',
  error: 'border-rose-500/50',
};

export default function ToastStack({ toasts, onUndo, onDismiss }) {
  if (!toasts.length) return null;
  return (
    <div className="pointer-events-none fixed bottom-4 left-1/2 z-50 flex w-[min(92vw,26rem)] -translate-x-1/2 flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`card-surface pointer-events-auto flex items-center gap-3 px-3 py-2.5 shadow-lg
                      animate-slide-up ${TONES[t.tone] || TONES.info}`}
        >
          <span className={t.tone === 'error' ? 'text-rose-500' : 'text-emerald-500'}>
            {t.tone === 'error' ? <Warning /> : <Check />}
          </span>
          <p className="flex-1 text-sm text-ink">{t.message}</p>
          {t.onUndo && (
            <button onClick={() => onUndo(t.id)} className="btn-ghost px-2 py-1 text-xs font-semibold text-brand">
              Undo
            </button>
          )}
          <button
            onClick={() => onDismiss(t.id, { runExpire: true })}
            aria-label="Dismiss"
            className="rounded p-1 text-ink-faint hover:bg-surface-sunken hover:text-ink"
          >
            <Close size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
