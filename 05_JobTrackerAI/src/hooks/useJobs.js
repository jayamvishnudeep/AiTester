import { useCallback, useEffect, useState } from 'react';
import * as db from '../db/database.js';

/**
 * Single owner of the job list. Every mutation writes to IndexedDB first,
 * then updates local state from what the DB actually returned — so the UI
 * never claims a save that didn't land.
 */
export function useJobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    db.getAllJobs()
      .then((rows) => alive && setJobs(rows))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const add = useCallback(async (input) => {
    const job = await db.createJob(input);
    setJobs((prev) => [...prev, job]);
    return job;
  }, []);

  const update = useCallback(async (id, patch) => {
    const next = await db.updateJob(id, patch);
    if (next) setJobs((prev) => prev.map((j) => (j.id === next.id ? next : j)));
    return next;
  }, []);

  const remove = useCallback(async (id) => {
    await db.deleteJob(id);
    setJobs((prev) => prev.filter((j) => j.id !== id));
  }, []);

  const restore = useCallback(async (job) => {
    await db.restoreJob(job);
    setJobs((prev) => [...prev.filter((j) => j.id !== job.id), job]);
  }, []);

  const importJobs = useCallback(async (rows, mode) => {
    const all = await db.bulkPut(rows, mode);
    setJobs(all);
    return all;
  }, []);

  return { jobs, loading, error, add, update, remove, restore, importJobs };
}
