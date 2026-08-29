import { openDB } from 'idb';
import { nowISO, todayISO } from '../lib/dates.js';
import { DEFAULT_ROUNDS } from '../lib/constants.js';

const DB_NAME = 'job-tracker';
const DB_VERSION = 1;
const JOBS = 'jobs';
const META = 'meta';

let dbPromise;

function getDB() {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(JOBS)) {
          const store = db.createObjectStore(JOBS, { keyPath: 'id' });
          store.createIndex('by-status', 'status');
          store.createIndex('by-company', 'company');
        }
        if (!db.objectStoreNames.contains(META)) {
          db.createObjectStore(META, { keyPath: 'key' });
        }
      },
    });
  }
  return dbPromise;
}

const newId = () =>
  (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`);

/**
 * Fill in every field a card is expected to have. Runs on create and on
 * import, so a partial record from an older export still loads cleanly.
 */
export function normalizeJob(input = {}) {
  const status = input.status || 'wishlist';
  const createdAt = input.createdAt || nowISO();
  return {
    id: input.id || newId(),
    company: (input.company || '').trim(),
    role: (input.role || '').trim(),
    url: input.url || '',
    resume: input.resume || '',
    dateApplied: input.dateApplied || todayISO(),
    salary: input.salary || '',
    notes: input.notes || '',
    status,
    recruiterName: input.recruiterName || '',
    recruiterContact: input.recruiterContact || '',
    tags: Array.isArray(input.tags) ? input.tags : [],
    priority: Boolean(input.priority),
    rounds: Array.isArray(input.rounds) && input.rounds.length
      ? input.rounds
      : DEFAULT_ROUNDS.map((label) => ({ label, done: false })),
    jdSnapshot: input.jdSnapshot || '',
    followUpBy: input.followUpBy || null,
    // History is append-only and never edited directly by the user.
    history: Array.isArray(input.history) && input.history.length
      ? input.history
      : [{ status, at: createdAt }],
    order: typeof input.order === 'number' ? input.order : Date.now(),
    createdAt,
    updatedAt: input.updatedAt || createdAt,
  };
}

export async function getAllJobs() {
  const db = await getDB();
  return db.getAll(JOBS);
}

export async function createJob(input) {
  const db = await getDB();
  const job = normalizeJob(input);
  await db.put(JOBS, job);
  return job;
}

/**
 * Patch a card. A status change appends to the history log automatically —
 * callers never write `history` themselves.
 */
export async function updateJob(id, patch) {
  const db = await getDB();
  const existing = await db.get(JOBS, id);
  if (!existing) return null;

  const next = { ...existing, ...patch, id, updatedAt: nowISO() };
  if (patch.status && patch.status !== existing.status) {
    next.history = [...(existing.history || []), { status: patch.status, at: nowISO() }];
  } else {
    next.history = existing.history || [];
  }
  await db.put(JOBS, next);
  return next;
}

export async function deleteJob(id) {
  const db = await getDB();
  await db.delete(JOBS, id);
}

/** Used by the undo toast to put a deleted card back exactly as it was. */
export async function restoreJob(job) {
  const db = await getDB();
  await db.put(JOBS, job);
  return job;
}

/** Import: `merge` keeps existing cards, `replace` wipes the store first. */
export async function bulkPut(jobs, mode = 'merge') {
  const db = await getDB();
  const tx = db.transaction(JOBS, 'readwrite');
  if (mode === 'replace') await tx.store.clear();
  for (const raw of jobs) await tx.store.put(normalizeJob(raw));
  await tx.done;
  return getAllJobs();
}

export async function getMeta(key, fallback = null) {
  const db = await getDB();
  const row = await db.get(META, key);
  return row ? row.value : fallback;
}

export async function setMeta(key, value) {
  const db = await getDB();
  await db.put(META, { key, value });
  return value;
}
