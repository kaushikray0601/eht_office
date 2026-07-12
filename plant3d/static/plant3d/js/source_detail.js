const queueStatus = document.getElementById('conversionQueueStatus');
const jobList = document.getElementById('conversionJobList');
const primaryProgress = document.getElementById('primaryConversionProgress');
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

function resourceLine(data) {
  const metrics = data.metrics || {};
  if (!metrics.process_cpu_time_ms && !metrics.process_cpu_to_wall_ratio) return '';
  const ratio = metrics.process_cpu_to_wall_ratio ?? 'n/a';
  return `<br>CPU time: ${escapeHtml(metrics.process_cpu_time_ms ?? 'n/a')} ms, CPU/wall ratio=${escapeHtml(ratio)}`;
}

function rawMetricsBlock(data) {
  if (!data.metrics || !Object.keys(data.metrics).length) return '';
  return `<details><summary>Raw metrics</summary><pre>${escapeHtml(JSON.stringify(data.metrics))}</pre></details>`;
}

function progressBar(percent, label = 'Conversion progress') {
  const width = Math.max(0, Math.min(100, Number(percent) || 0));
  return `<div class="p3d-progress" aria-label="${escapeHtml(label)}"><div class="p3d-progress-bar" style="width: ${width}%;"></div></div>`;
}

function updatePrimaryProgress(data) {
  if (!primaryProgress || !data?.id) return;
  primaryProgress.hidden = false;
  primaryProgress.dataset.primaryJobId = String(data.id);
  primaryProgress.innerHTML = [
    `<div class="p3d-list-title"><span>Latest conversion - ${escapeHtml(data.job_type || '')}</span><span>${escapeHtml(data.status)} - ${escapeHtml(data.progress_percent)}%</span></div>`,
    progressBar(data.progress_percent, 'Latest conversion progress'),
  ].join('');
}

function jobLine(data) {
  const packageLinks = data.package
    ? `<div class="p3d-list-actions"><a class="p3d-button p3d-button-primary" href="${escapeHtml(data.package.viewer_url)}">View</a> <a class="p3d-button p3d-button-quiet" href="${escapeHtml(data.package.json_url)}">Package JSON</a></div>`
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
  const resources = resourceLine(data);
  const metrics = rawMetricsBlock(data);
  const error = data.error_message ? `<br>Error: ${escapeHtml(data.error_message)}` : '';
  return [
    `<div class="p3d-list-title"><span>Job ${escapeHtml(data.id)} - ${escapeHtml(data.job_type || '')}</span><span>${escapeHtml(data.status)} - ${escapeHtml(data.progress_percent)}%</span></div>`,
    progressBar(data.progress_percent),
    processHint,
    workerHint,
    stage,
    totalDuration,
    timings,
    resources,
    metrics,
    error,
    `<div class="p3d-list-actions"><a class="p3d-button p3d-button-quiet" href="${escapeHtml(data.url || `/plant3d/jobs/${data.id}/json/`)}">Job JSON</a></div>`,
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
    row.className = 'p3d-list-item';
    jobList.prepend(row);
  }
  row.dataset.jobUrl = data.url || `/plant3d/jobs/${data.id}/json/`;
  row.innerHTML = jobLine(data);
  updatePrimaryProgress(data);
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
