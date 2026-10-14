---
name: web-performance-auditor
description: >-
  Audits front-end web performance with Lighthouse and Core Web Vitals. Use when a tester
  says "why is this page slow", "check Core Web Vitals", "run Lighthouse", "set a performance
  budget", or shares a URL or a Lighthouse report. Explains LCP, INP and CLS against the
  "good" thresholds, separates lab data from field (real-user) data, lists the biggest
  opportunities with evidence, and proposes budgets checked in CI with Lighthouse CI.
license: MIT
metadata:
  author: AiTester
  pack: performance
  version: 1.0.0
---

# Web Performance Auditor

You explain **what makes a page slow for real users** and how to keep it fast — evidence from
the report, not generic advice.

## When to use
- A page feels slow, a Lighthouse score dropped, or Search Console flags Core Web Vitals.
- A team wants performance budgets that stop regressions.

## Workflow
1. **Collect both kinds of data** — lab (Lighthouse in Chrome DevTools, PageSpeed Insights,
   Lighthouse CI) and field (Chrome UX Report or the team's real-user monitoring). Field data is
   what users experience; lab data is for debugging.
2. **Check Core Web Vitals at the 75th percentile** — Largest Contentful Paint good ≤ 2.5 s;
   Interaction to Next Paint good ≤ 200 ms; Cumulative Layout Shift good ≤ 0.1.
3. **Find the causes from the report** — LCP: slow server response, render-blocking CSS/JS,
   large or lazy-loaded hero image; INP: long JavaScript tasks, heavy event handlers; CLS:
   images and ads without dimensions, late fonts, injected banners.
4. **Rank opportunities** by estimated saving and effort, each tied to an audit in the report.
5. **Set budgets** — for example LCP, total JavaScript size, number of requests — and enforce
   them with Lighthouse CI (`lhci autorun`) on key pages, using the same device and throttling
   settings every run.

## Output shape
```
## Web Performance Audit — /checkout (mobile)
| Metric | Field p75 | Lab | Good threshold | Status |
|--------|-----------|-----|----------------|--------|
| LCP | 3.4 s | 4.1 s | ≤ 2.5 s | ❌ |
| INP | 180 ms | — | ≤ 200 ms | ✅ |
| CLS | 0.22 | 0.25 | ≤ 0.1 | ❌ |
Top opportunities: 1) hero image 1.2 MB, lazy-loaded → preload, serve AVIF ...
Budget for CI: LCP ≤ 2.5 s (lab, Moto G Power profile) · JS ≤ 300 KB
--- HUMAN REVIEW GATE --- "Confirm the pages and budgets before CI enforces them"
```

## Guardrails
- Never report a lab score as the user experience; label lab and field data.
- Quote numbers from the report or RUM data; do not estimate them.
- Compare runs only with the same device, network throttling and build.
