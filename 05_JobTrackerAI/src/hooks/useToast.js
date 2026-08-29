import { useCallback, useRef, useState } from 'react';

let seq = 0;

/**
 * Toasts. A toast may carry an `onUndo` plus a `timeout`; when it expires
 * without being undone, `onExpire` fires — that's how deletes are finalised
 * only after the undo window closes.
 */
export function useToast() {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());

  const dismiss = useCallback((id, { runExpire = false } = {}) => {
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((prev) => {
      const t = prev.find((x) => x.id === id);
      if (t && runExpire && t.onExpire) t.onExpire();
      return prev.filter((x) => x.id !== id);
    });
  }, []);

  const push = useCallback(
    ({ message, tone = 'info', timeout = 3500, onUndo, onExpire }) => {
      const id = ++seq;
      setToasts((prev) => [...prev, { id, message, tone, onUndo, onExpire }]);
      const timer = setTimeout(() => dismiss(id, { runExpire: true }), timeout);
      timers.current.set(id, timer);
      return id;
    },
    [dismiss]
  );

  /** Undo cancels the pending expiry, so `onExpire` never runs. */
  const undo = useCallback(
    (id) => {
      setToasts((prev) => {
        const t = prev.find((x) => x.id === id);
        if (t && t.onUndo) t.onUndo();
        return prev.filter((x) => x.id !== id);
      });
      const timer = timers.current.get(id);
      if (timer) {
        clearTimeout(timer);
        timers.current.delete(id);
      }
    },
    []
  );

  return { toasts, push, dismiss, undo };
}
