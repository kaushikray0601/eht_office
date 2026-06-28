const queueStatus = document.getElementById('conversionQueueStatus');
const jobList = document.getElementById('conversionJobList');
const watchedJobs = new Map();

function setQueueStatus(message) {
  if (queueStatus) queueStatus.textContent = message || '';
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char]);
}

function timingLine(data) {
  const rows = Array.isArray(data.timing_summary) ? data.timing_summary : [];
  if (!rows.length) return '';
  const text = rows
    .map(row => `${row.label || row.key}=${row.ms} ms`)
    .join(', ');
  return `<br>Timings: ${escapeHtml(text)}`;
}

function rawMetricsBlock(data) {
  if (!data.metrics || !Object.keys(data.metrics).length) return '';
  return `<details><summary>Raw metrics</summary><pre>${escapeHtml(JSON.stringify(data.metrics))}</pre></details>`;
}

function jobLine(data) {
  const packageLinks = data.package
    ? ` <a href="${escapeHtml(data.package.viewer_url)}">View</a> <a href="${escapeHtml(data.package.json_url)}">Package JSON</a>`
    : '';
  const processHint = !data.package && data.process_hint
    ? `<br>Worker command: <code>${escapeHtml(data.process_hint)}</code>`
    : '';
  const workerHint = !data.package && data.worker_hint
    ? `<br>Long-running worker: <code>${escapeHtml(data.worker_hint)}</code>`
    : '';
  const stage = data.metrics?.stage ? `<br>Stage: ${escapeHtml(data.metrics.stage)}` : '';
  const totalDuration = data.metrics?.conversion_duration_ms ? `<br>Total conversion: ${escapeHtml(data.metrics.conversion_duration_ms)} ms` : '';
  const timings = timingLine(data);
  const metrics = rawMetricsBlock(data);
  const error = data.error_message ? `<br>Error: ${escapeHtml(data.error_message)}` : '';
  return [
    `Job ${escapeHtml(data.id)} - ${escapeHtml(data.job_type || '')} - ${escapeHtml(data.status)} - ${escapeHtml(data.progress_percent)}%`,
    processHint,
    workerHint,
    stage,
    totalDuration,
    timings,
    metrics,
    error,
    ` <a href="${escapeHtml(data.url || `/plant3d/jobs/${data.id}/json/`)}">JSON</a>`,
    packageLinks,
  ].join('');
}

function upsertJobRow(data) {
  if (!jobList) return null;
  const emptyRow = document.getElementById('conversionJobEmpty');
  if (emptyRow) emptyRow.remove();
  const rowId = `plant3d-job-${data.id}`;
  let row = document.getElementById(rowId);
  if (!row) {
    row = document.createElement('li');
    row.id = rowId;
    jobList.prepend(row);
  }
  row.dataset.jobUrl = data.url || `/plant3d/jobs/${data.id}/json/`;
  row.innerHTML = jobLine(data);
  return row;
}

async function pollJob(jobUrl) {
  const response = await fetch(jobUrl, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error(`Job status failed: ${response.status}`);
  const data = await response.json();
  data.url = jobUrl;
  upsertJobRow(data);
  if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
    watchedJobs.delete(jobUrl);
    setQueueStatus(data.status === 'completed' ? 'Conversion completed.' : `Conversion ${data.status}.`);
    return;
  }
  const stage = data.metrics?.stage ? ` (${data.metrics.stage})` : '';
  const workerHint = data.worker_hint || data.process_hint || '';
  setQueueStatus(workerHint ? `Conversion ${data.status}${stage}. Worker: ${workerHint}` : `Conversion ${data.status}${stage}.`);
  window.setTimeout(() => {
    pollJob(jobUrl).catch(error => {
      watchedJobs.delete(jobUrl);
      setQueueStatus(error.message || 'Unable to poll job.');
    });
  }, 2000);
}

function watchJob(jobUrl) {
  if (!jobUrl || watchedJobs.has(jobUrl)) return;
  watchedJobs.set(jobUrl, true);
  pollJob(jobUrl).catch(error => {
    watchedJobs.delete(jobUrl);
    setQueueStatus(error.message || 'Unable to poll job.');
  });
}

async function queueConversion(form) {
  setQueueStatus('Queuing conversion...');
  const response = await fetch(form.action, {
    method: 'POST',
    body: new FormData(form),
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error(`Queue request failed: ${response.status}`);
  const data = await response.json();
  const job = {
    ...(data.job || {}),
    job_type: data.job?.job_type || '',
    url: data.job?.url,
    process_hint: data.process_hint,
    worker_hint: data.worker_hint,
  };
  upsertJobRow(job);
  setQueueStatus(data.worker_hint ? `Queued. Keep worker running: ${data.worker_hint}` : 'Queued.');
  watchJob(job.url);
}

document.querySelectorAll('[data-conversion-form]').forEach(form => {
  form.addEventListener('submit', event => {
    event.preventDefault();
    queueConversion(form).catch(error => {
      setQueueStatus(error.message || 'Unable to queue conversion.');
    });
  });
});

document.querySelectorAll('[data-watch-job]').forEach(row => {
  watchJob(row.dataset.jobUrl);
});
