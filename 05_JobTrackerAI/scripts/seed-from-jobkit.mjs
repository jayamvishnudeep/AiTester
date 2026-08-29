#!/usr/bin/env node
/*
 * seed-from-jobkit.mjs — turn the real job postings in 04_JobKitAI into a
 * backup file this app can import.
 *
 *   node scripts/seed-from-jobkit.mjs        # writes seed-data.json
 *
 * Load it through the app's Import button (Merge). Nothing here is invented
 * except the tracking metadata a tracker is supposed to hold — where each
 * application sits, when it moved, and which resume version went out.
 * Company, role, location, experience range, JD text, posting URL and the
 * recruiting agency all come straight from the CSVs.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const JOBKIT = path.resolve(HERE, '..', '..', '04_JobKitAI');
const OUT = path.resolve(HERE, '..', 'seed-data.json');

// ---------------------------------------------------------------- CSV parse
/** Handles quoted fields, escaped "" quotes, and newlines inside quotes. */
function parseCSV(text) {
  const rows = [];
  let row = [], field = '', inQuotes = false;
  const src = text.replace(/^﻿/, '').replace(/\r\n/g, '\n');

  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (inQuotes) {
      if (c === '"') {
        if (src[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }

  const [header, ...body] = rows.filter((r) => r.some((c) => c.trim()));
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h.trim(), (r[i] ?? '').trim()])));
}

// ------------------------------------------------------------------ helpers
const DAY = 86400000;
const ago = (d) => new Date(Date.now() - d * DAY).toISOString();
const ahead = (d) => new Date(Date.now() + d * DAY).toISOString();

/** "Infosys (Posted by Glauben Technologies)" -> company + agency. */
function splitAgency(raw) {
  const m = raw.match(/^(.*?)\s*\(Posted by (.*?)\)\s*$/i);
  return m ? { company: m[1].trim(), agency: m[2].trim() } : { company: raw.trim(), agency: '' };
}

const snapshot = (jd) => {
  const clean = jd.replace(/\s*\n\s*/g, '\n').trim();
  return clean.length > 900 ? clean.slice(0, 900).trimEnd() + '\n\n[…truncated — see the original posting]' : clean;
};

const TAG = {
  india:   { label: 'India',        color: '#eb6834' },
  germany: { label: 'Germany',      color: '#2a78d6' },
  strong:  { label: 'Strong match', color: '#1baf7a' },
  stretch: { label: 'Stretch',      color: '#eda100' },
  mismatch:{ label: 'JD mismatch',  color: '#e87ba4' },
  lead:    { label: 'Lead role',    color: '#8b7cf0' },
  remote:  { label: 'Remote / hybrid', color: '#2a78d6' },
};

/**
 * Resume versions. The JobKitAI run produced one tailored .docx per posting,
 * but a tracker wants to compare *versions* — so these are the five tailoring
 * archetypes that run actually used. The specific generated file is recorded
 * in each card's notes.
 */
const RESUME = {
  playwright: 'Playwright_TS_v3',
  selenium:   'Selenium_Java_v3',
  api:        'API_RestAssured_v2',
  lead:       'QA_Lead_v2',
  generic:    'Generic_QA_v1',
};

/**
 * Per-posting tracking state, keyed by a distinctive slug of the job title.
 * `stage` drives the history chain; `applied` is days-ago the application
 * went out. Kept in one table so the spread across columns is deliberate
 * rather than random.
 */
const PLAN = {
  // --- Naukri -------------------------------------------------------------
  'senior qa engineer , software':      { stage: 'rejected',  applied: 58, resume: RESUME.selenium,   tags: ['india'] },
  'catalog quality & ai automation':    { stage: 'wishlist',  saved: 21,   resume: RESUME.lead,       tags: ['india', 'stretch'] },
  'in_manager_qa automation':           { stage: 'interview', applied: 34, resume: RESUME.lead,       tags: ['india', 'lead'], rounds: 2, priority: true },
  'senior quality assurance engineer':  { stage: 'followup',  applied: 24, resume: RESUME.selenium,   tags: ['india'], followUp: -2 },
  'qa tester with ai':                  { stage: 'rejected',  applied: 45, resume: RESUME.generic,    tags: ['india', 'stretch'] },
  'senior qa automation engineer (pla': { stage: 'applied',   applied: 11, resume: RESUME.playwright, tags: ['india', 'mismatch'], followUp: -1 },
  'cypress automation tester':          { stage: 'wishlist',  saved: 17,   resume: RESUME.generic,    tags: ['india', 'stretch', 'remote'] },
  'c# and oop concepts':                { stage: 'rejected',  applied: 40, resume: RESUME.selenium,   tags: ['india', 'stretch'] },
  'quality engineer':                   { stage: 'interview', applied: 29, resume: RESUME.playwright, tags: ['india', 'strong', 'remote'], rounds: 3, priority: true },
  'infosys_ api tester':                { stage: 'interview', applied: 26, resume: RESUME.api,        tags: ['india', 'strong'], rounds: 1, priority: true },
  'in_senior associate_qa automation':  { stage: 'applied',   applied: 9,  resume: RESUME.selenium,   tags: ['india'] },
  'playwright automation tester':       { stage: 'offer',     applied: 41, resume: RESUME.playwright, tags: ['india', 'strong'], rounds: 4, priority: true },
  'qa automation engineer' :            { stage: 'applied',   applied: 13, resume: RESUME.playwright, tags: ['india', 'strong'], followUp: -4 },
  'qa automation + edi test engineer':  { stage: 'wishlist',  saved: 6,    resume: RESUME.api,        tags: ['india', 'stretch', 'remote'] },
  'qa engineer (playwright, rest':      { stage: 'interview', applied: 20, resume: RESUME.api,        tags: ['india', 'strong', 'remote'], rounds: 2 },
  'qa automation engineer (playwright)':{ stage: 'applied',   applied: 8,  resume: RESUME.playwright, tags: ['india', 'strong'] },
  'sr. sdet':                           { stage: 'followup',  applied: 22, resume: RESUME.selenium,   tags: ['india', 'lead'], followUp: -3 },
  'qa automation engineer, professional': { stage: 'applied', applied: 16, resume: RESUME.playwright, tags: ['india', 'strong'], priority: true },
  'qa automation engineer (camera':     { stage: 'applied',   applied: 10, resume: RESUME.api,        tags: ['india'] },
  'lead qa automation engineer':        { stage: 'applied',   applied: 12, resume: RESUME.lead,       tags: ['india', 'lead', 'mismatch'] },
  'senior quantitative model':          { stage: 'rejected',  applied: 37, resume: RESUME.generic,    tags: ['india', 'stretch'] },

  // --- Stepstone ----------------------------------------------------------
  'tosca test automation engineer':     { stage: 'wishlist',  saved: 19,   resume: RESUME.generic,    tags: ['germany', 'stretch'] },
  'testautomatisierer':                 { stage: 'followup',  applied: 27, resume: RESUME.selenium,   tags: ['germany'], followUp: -6 },
  'test automation engineer (m/w/d)':   { stage: 'interview', applied: 31, resume: RESUME.playwright, tags: ['germany', 'strong'], rounds: 3, priority: true },
  'test automation engineer (all':      { stage: 'followup',  applied: 18, resume: RESUME.lead,       tags: ['germany'], followUp: 4 },
  'it consultant (m/w/d) software':     { stage: 'wishlist',  saved: 4,    resume: RESUME.generic,    tags: ['germany', 'stretch'] },
};

function planFor(title) {
  const t = title.toLowerCase();
  // Longest key wins, so "qa automation engineer (playwright)" beats "qa automation engineer".
  const hit = Object.keys(PLAN)
    .filter((k) => t.includes(k))
    .sort((a, b) => b.length - a.length)[0];
  return hit ? PLAN[hit] : null;
}

/** Build a status history consistent with where the card ended up. */
function buildHistory(stage, appliedDaysAgo, savedDaysAgo) {
  if (stage === 'wishlist') return [{ status: 'wishlist', at: ago(savedDaysAgo) }];

  const h = [{ status: 'wishlist', at: ago(appliedDaysAgo + 4) },
             { status: 'applied', at: ago(appliedDaysAgo) }];
  const add = (status, d) => h.push({ status, at: ago(Math.max(d, 0)) });

  switch (stage) {
    case 'applied': break;
    case 'followup':  add('followup', appliedDaysAgo - 8); break;
    case 'interview': add('followup', appliedDaysAgo - 7); add('interview', appliedDaysAgo - 13); break;
    case 'offer':     add('followup', appliedDaysAgo - 6); add('interview', appliedDaysAgo - 14);
                      add('offer', appliedDaysAgo - 30); break;
    case 'rejected':  add('rejected', appliedDaysAgo - 12); break;
  }
  return h;
}

const ROUND_LABELS = ['Phone Screen', 'Technical', 'Onsite', 'HR', 'Final'];
const buildRounds = (done = 0) =>
  ROUND_LABELS.map((label, i) => ({ label, done: i < done }));

// -------------------------------------------------------------------- build
function toCard(raw, source) {
  const title = raw['Job Title'];
  const plan = planFor(title);
  if (!plan) {
    console.warn(`  ! no plan for "${title}" — skipped`);
    return null;
  }

  const { company, agency } = splitAgency(raw.Company);
  const stage = plan.stage;
  const appliedDays = plan.applied ?? plan.saved ?? 7;
  const history = buildHistory(stage, plan.applied ?? 0, plan.saved ?? 0);
  const createdAt = history[0].at;

  const notesBits = [];
  if (raw.Experience) notesBits.push(`Posting asks for ${raw.Experience}.`);
  if (raw.Location) notesBits.push(`Location: ${raw.Location}.`);
  if (agency) notesBits.push(`Listed via ${agency}.`);
  notesBits.push(`Tailored resume generated in 04_JobKitAI (${source} batch).`);

  return {
    id: `jobkit-${source}-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 46)}`,
    company,
    role: title,
    url: raw['Job URL'] || '',
    resume: plan.resume,
    dateApplied: stage === 'wishlist' ? ago(plan.saved) : ago(plan.applied),
    salary: '',
    notes: notesBits.join(' '),
    status: stage,
    recruiterName: agency,
    recruiterContact: '',
    tags: (plan.tags || []).map((t) => TAG[t]).filter(Boolean),
    priority: Boolean(plan.priority),
    rounds: buildRounds(plan.rounds ?? 0),
    jdSnapshot: snapshot(raw['Job Description'] || ''),
    followUpBy: plan.followUp === undefined ? null : (plan.followUp < 0 ? ago(-plan.followUp) : ahead(plan.followUp)),
    history,
    order: Date.now() - appliedDays * DAY,
    createdAt,
    updatedAt: history[history.length - 1].at,
  };
}

const read = (f) => parseCSV(fs.readFileSync(path.join(JOBKIT, f), 'utf8'));

console.log('Reading postings from 04_JobKitAI…');
const naukri = read('naukri_jobs.csv');
const stepstone = read('stepstone_jobs.csv');
console.log(`  naukri:    ${naukri.length} rows`);
console.log(`  stepstone: ${stepstone.length} rows`);

const jobs = [
  ...naukri.map((r) => toCard(r, 'naukri')),
  ...stepstone.map((r) => toCard(r, 'stepstone')),
].filter(Boolean);

const payload = {
  app: 'job-tracker',
  version: 1,
  exportedAt: new Date().toISOString(),
  count: jobs.length,
  jobs,
};

fs.writeFileSync(OUT, JSON.stringify(payload, null, 2));

const byStatus = jobs.reduce((m, j) => ({ ...m, [j.status]: (m[j.status] || 0) + 1 }), {});
console.log(`\nWrote ${jobs.length} cards -> ${path.relative(process.cwd(), OUT)}`);
console.log('Spread across the board:');
for (const [k, v] of Object.entries(byStatus)) console.log(`  ${k.padEnd(10)} ${v}`);
console.log('\nImport it in the app: Upload icon -> pick seed-data.json -> Merge.');
