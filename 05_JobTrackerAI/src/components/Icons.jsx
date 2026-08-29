// Inline icons — a handful of 16px strokes, cheaper than pulling in a set.
const base = {
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

const Svg = ({ children, size = 16, ...rest }) => (
  <svg {...base} width={size} height={size} aria-hidden="true" {...rest}>
    {children}
  </svg>
);

export const Plus = (p) => (
  <Svg {...p}><path d="M12 5v14M5 12h14" /></Svg>
);
export const Search = (p) => (
  <Svg {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Svg>
);
export const Star = ({ filled, ...p }) => (
  <Svg {...p} fill={filled ? 'currentColor' : 'none'}>
    <path d="m12 3 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.2l5.9-.9z" />
  </Svg>
);
export const Link = (p) => (
  <Svg {...p}>
    <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
    <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
  </Svg>
);
export const Trash = (p) => (
  <Svg {...p}><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" /></Svg>
);
export const Close = (p) => (
  <Svg {...p}><path d="M18 6 6 18M6 6l12 12" /></Svg>
);
export const Sun = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </Svg>
);
export const Moon = (p) => (
  <Svg {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></Svg>
);
export const Download = (p) => (
  <Svg {...p}><path d="M12 3v12m0 0 4-4m-4 4-4-4M3 17v2a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2" /></Svg>
);
export const Upload = (p) => (
  <Svg {...p}><path d="M12 21V9m0 0 4 4M12 9 8 13M3 7V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2" /></Svg>
);
export const Board = (p) => (
  <Svg {...p}><rect x="3" y="3" width="6" height="18" rx="1" /><rect x="11" y="3" width="6" height="12" rx="1" /><rect x="19" y="3" width="2" height="8" rx="1" /></Svg>
);
export const Chart = (p) => (
  <Svg {...p}><path d="M3 21h18M7 21V10M12 21V4M17 21v-7" /></Svg>
);
export const Bell = (p) => (
  <Svg {...p}><path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8M13.7 21a2 2 0 0 1-3.4 0" /></Svg>
);
export const Check = (p) => (
  <Svg {...p}><path d="m20 6-11 11-5-5" /></Svg>
);
export const Rows = (p) => (
  <Svg {...p}><path d="M3 6h18M3 12h18M3 18h18" /></Svg>
);
export const Warning = (p) => (
  <Svg {...p}><path d="M12 9v4M12 17h.01M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></Svg>
);
