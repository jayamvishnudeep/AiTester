const EXPORT_VERSION = 1;

/** Download all cards as a timestamped JSON backup. */
export function exportJobs(jobs) {
  const payload = {
    app: 'job-tracker',
    version: EXPORT_VERSION,
    exportedAt: new Date().toISOString(),
    count: jobs.length,
    jobs,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `job-tracker-backup-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke on the next tick so the download has definitely started.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return payload.count;
}

/**
 * Parse a backup file. Accepts either the wrapped export shape or a bare
 * array of jobs, and throws a message meant to be shown to the user.
 */
export function parseBackup(text) {
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error("That file isn't valid JSON.");
  }

  const jobs = Array.isArray(data) ? data : data?.jobs;
  if (!Array.isArray(jobs)) {
    throw new Error("No jobs found in that file — expected a backup exported from this app.");
  }

  const usable = jobs.filter((j) => j && typeof j === 'object' && (j.company || j.role));
  if (!usable.length) throw new Error('That backup contains no readable job cards.');

  return usable;
}

export function readFileText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('Could not read that file.'));
    reader.readAsText(file);
  });
}
