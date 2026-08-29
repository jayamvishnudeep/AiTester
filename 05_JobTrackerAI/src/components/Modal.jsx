import { useEffect, useRef } from 'react';
import { Close } from './Icons.jsx';

/**
 * Shared overlay. `variant="panel"` slides in from the right for the card
 * detail view; `variant="dialog"` centres for forms and confirmations.
 * Esc closes, focus moves in on open and the page behind stops scrolling.
 */
export default function Modal({ open, onClose, title, subtitle, children, footer, variant = 'dialog', width = 'max-w-lg' }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    // Focus the panel so Esc works without a click first.
    const t = setTimeout(() => ref.current?.focus(), 0);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
      clearTimeout(t);
    };
  }, [open, onClose]);

  if (!open) return null;

  const isPanel = variant === 'panel';

  return (
    <div className="fixed inset-0 z-40 flex animate-fade-in" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={onClose} />
      <div
        ref={ref}
        tabIndex={-1}
        className={
          isPanel
            ? 'relative ml-auto flex h-full w-full max-w-xl flex-col bg-surface shadow-2xl animate-slide-left outline-none'
            : `relative m-auto flex max-h-[90vh] w-[92vw] ${width} flex-col card-surface shadow-2xl animate-slide-up outline-none`
        }
      >
        <header className="flex items-start gap-3 border-b border-edge px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-base font-semibold text-ink">{title}</h2>
            {subtitle && <p className="mt-0.5 truncate text-sm text-ink-muted">{subtitle}</p>}
          </div>
          <button onClick={onClose} aria-label="Close" className="btn-ghost -mr-1 p-1.5">
            <Close size={18} />
          </button>
        </header>

        <div className="scroll-slim flex-1 overflow-y-auto px-5 py-4">{children}</div>

        {footer && <footer className="flex items-center justify-end gap-2 border-t border-edge px-5 py-3">{footer}</footer>}
      </div>
    </div>
  );
}
