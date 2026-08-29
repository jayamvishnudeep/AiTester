import { useCallback, useEffect, useState } from 'react';

/**
 * Small localStorage-backed settings (theme, card density). These are
 * per-browser display preferences, not data — IndexedDB holds the data.
 * Every access is guarded: private windows and blocked site data throw.
 */
function read(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : v;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable — preference just won't persist */
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    const stored = read('jt.theme', null);
    if (stored) return stored;
    try {
      return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    write('jt.theme', theme);
  }, [theme]);

  const toggle = useCallback(() => setTheme((t) => (t === 'dark' ? 'light' : 'dark')), []);
  return { theme, toggle };
}

export function useDensity() {
  const [density, setDensity] = useState(() => read('jt.density', 'comfortable'));
  useEffect(() => write('jt.density', density), [density]);
  const toggle = useCallback(
    () => setDensity((d) => (d === 'compact' ? 'comfortable' : 'compact')),
    []
  );
  return { density, toggle, compact: density === 'compact' };
}
