"""
Memory Inspector Dashboard — HTML/CSS/JS for the Inspector Web UI.
"""

INSPECTOR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenMemo Memory Inspector</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; }
.header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
.header h1 { font-size: 20px; color: #58a6ff; }
.header .version { font-size: 13px; color: #8b949e; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
.card.full { grid-column: 1 / -1; }
.card h2 { font-size: 15px; color: #f0f6fc; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.card h2 .icon { font-size: 16px; }
.checklist-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 14px; }
.status-ok { color: #3fb950; }
.status-warn { color: #d29922; }
.status-fail { color: #f85149; }
.status-cold { color: #8b949e; }
.stat-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; border-bottom: 1px solid #21262d; }
.stat-row:last-child { border-bottom: none; }
.stat-value { color: #58a6ff; font-weight: 600; }
.dist-bar { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 13px; }
.dist-bar .bar { height: 8px; border-radius: 4px; background: #58a6ff; min-width: 4px; }
.dist-bar .label { min-width: 100px; color: #8b949e; }
.dist-bar .count { color: #c9d1d9; min-width: 30px; text-align: right; }
.memory-item { padding: 10px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
.memory-item:last-child { border-bottom: none; }
.memory-item .content { color: #c9d1d9; margin-bottom: 4px; }
.memory-item .meta { font-size: 12px; color: #8b949e; display: flex; gap: 12px; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; background: #21262d; color: #8b949e; }
.tag.scene { background: #0d419d; color: #a5d6ff; }
.tag.type { background: #1a4731; color: #56d364; }
.search-box { width: 100%; padding: 10px 14px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 14px; outline: none; }
.search-box:focus { border-color: #58a6ff; }
.search-results { margin-top: 12px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.badge.ok { background: #1a4731; color: #3fb950; }
.badge.update { background: #3d2e00; color: #d29922; }
.refresh-note { font-size: 12px; color: #484f58; }
.empty { color: #484f58; font-size: 13px; font-style: italic; padding: 8px 0; }
.scene-badge { display: inline-block; padding: 4px 12px; background: #0d419d; color: #a5d6ff; border-radius: 16px; font-size: 14px; font-weight: 600; }
</style>
</head>
<body>
<div class="header">
  <h1>OpenMemo Memory Inspector</h1>
  <div>
    <span class="version" id="header-version"></span>
    <span class="refresh-note"> &middot; auto-refresh 5s</span>
  </div>
</div>

<div class="container">
  <!-- Checklist -->
  <div class="card">
    <h2><span class="icon">🔍</span> Memory System Checklist</h2>
    <div id="checklist"></div>
  </div>

  <!-- System Status -->
  <div class="card">
    <h2><span class="icon">⚙️</span> System Status</h2>
    <div id="system-status"></div>
  </div>

  <!-- Memory Records -->
  <div class="card">
    <h2><span class="icon">📊</span> Memory Records</h2>
    <div id="memory-records"></div>
  </div>

  <!-- Scene & Type Distribution -->
  <div class="card">
    <h2><span class="icon">🏷️</span> Distribution</h2>
    <div id="distribution"></div>
  </div>

  <!-- Recent Writes -->
  <div class="card full">
    <h2><span class="icon">📝</span> Recent Writes</h2>
    <div id="recent-writes"></div>
  </div>

  <!-- Memory Search -->
  <div class="card full">
    <h2><span class="icon">🔎</span> Memory Search</h2>
    <input type="text" class="search-box" id="search-input" placeholder="Search memories..." />
    <div class="search-results" id="search-results"></div>
  </div>

  <!-- Update Status -->
  <div class="card">
    <h2><span class="icon">📦</span> Update Status</h2>
    <div id="update-status"></div>
  </div>
</div>

<script>
const API = '';

function statusIcon(s) {
  if (s === 'ok') return '<span class="status-ok">✓</span>';
  if (s === 'warning') return '<span class="status-warn">!</span>';
  if (s === 'cold_start') return '<span class="status-cold">○</span>';
  return '<span class="status-fail">✕</span>';
}

async function fetchJSON(url) {
  try {
    const r = await fetch(API + url);
    return await r.json();
  } catch (e) { return null; }
}

async function loadChecklist() {
  const d = await fetchJSON('/api/inspector/checklist');
  if (!d) { document.getElementById('checklist').innerHTML = '<div class="empty">Could not load checklist</div>'; return; }
  const el = document.getElementById('checklist');
  el.innerHTML = d.checks.map(c =>
    '<div class="checklist-item">' + statusIcon(c.status) + ' ' + c.name + '</div>'
  ).join('');
}

async function loadHealth() {
  const d = await fetchJSON('/api/inspector/health');
  if (!d) return;
  const el = document.getElementById('system-status');
  el.innerHTML = [
    ['Memory Backend', d.backend || 'openmemo'],
    ['API Version', d.api_version || '-'],
    ['Engine Version', d.engine_version || '-'],
    ['Status', d.status || '-'],
    ['Total Memories', d.total_memories || 0],
    ['Total Scenes', d.total_scenes || 0],
  ].map(([k,v]) => '<div class="stat-row"><span>' + k + '</span><span class="stat-value">' + v + '</span></div>').join('');
}

async function loadSummary() {
  const d = await fetchJSON('/api/inspector/memory-summary');
  if (!d) return;

  document.getElementById('memory-records').innerHTML = [
    ['Total Memories', d.total_memories],
    ['Total Cells', d.total_cells],
    ['Scenes', d.total_scenes],
  ].map(([k,v]) => '<div class="stat-row"><span>' + k + '</span><span class="stat-value">' + v + '</span></div>').join('');

  let distHtml = '';
  if (d.type_distribution && Object.keys(d.type_distribution).length > 0) {
    const maxT = Math.max(...Object.values(d.type_distribution), 1);
    distHtml += '<div style="margin-bottom:12px"><div style="font-size:13px;color:#8b949e;margin-bottom:6px">By Type</div>';
    for (const [k,v] of Object.entries(d.type_distribution)) {
      const w = Math.max(4, (v/maxT)*100);
      distHtml += '<div class="dist-bar"><span class="label">' + k + '</span><div class="bar" style="width:' + w + 'px"></div><span class="count">' + v + '</span></div>';
    }
    distHtml += '</div>';
  }
  if (d.scene_distribution && Object.keys(d.scene_distribution).length > 0) {
    const maxS = Math.max(...Object.values(d.scene_distribution), 1);
    distHtml += '<div><div style="font-size:13px;color:#8b949e;margin-bottom:6px">By Scene</div>';
    for (const [k,v] of Object.entries(d.scene_distribution)) {
      const w = Math.max(4, (v/maxS)*100);
      distHtml += '<div class="dist-bar"><span class="label">' + (k||'(none)') + '</span><div class="bar" style="width:' + w + 'px;background:#3fb950"></div><span class="count">' + v + '</span></div>';
    }
    distHtml += '</div>';
  }
  document.getElementById('distribution').innerHTML = distHtml || '<div class="empty">No distribution data</div>';
}

function renderMemory(m) {
  const content = m.content || m.text || '';
  const scene = m.scene || '';
  const mtype = m.memory_type || m.cell_type || m.type || '';
  const score = m.score != null ? m.score.toFixed(2) : '';
  let meta = '';
  if (scene) meta += '<span class="tag scene">' + scene + '</span>';
  if (mtype) meta += '<span class="tag type">' + mtype + '</span>';
  if (score) meta += '<span class="tag">score: ' + score + '</span>';
  return '<div class="memory-item"><div class="content">' + escapeHtml(content.substring(0, 200)) + '</div><div class="meta">' + meta + '</div></div>';
}

function escapeHtml(t) {
  const d = document.createElement('div'); d.textContent = t; return d.innerHTML;
}

async function loadRecent() {
  const d = await fetchJSON('/api/inspector/recent');
  const el = document.getElementById('recent-writes');
  if (!d || !d.recent || d.recent.length === 0) { el.innerHTML = '<div class="empty">No recent writes (cold start)</div>'; return; }
  el.innerHTML = d.recent.map(renderMemory).join('');
}

async function loadVersion() {
  const d = await fetchJSON('/version');
  if (!d) return;
  const el = document.getElementById('update-status');
  el.innerHTML = [
    ['OpenMemo Core', d.latest_core],
    ['OpenMemo Adapter', d.latest_adapter],
    ['Schema Version', d.schema_version],
  ].map(([k,v]) => '<div class="stat-row"><span>' + k + '</span><span class="stat-value">' + v + '</span></div>').join('');
  document.getElementById('header-version').textContent = 'Core ' + d.latest_core + ' / Adapter ' + d.latest_adapter;
}

let searchTimer;
document.getElementById('search-input').addEventListener('input', function() {
  clearTimeout(searchTimer);
  const q = this.value.trim();
  if (q.length < 2) { document.getElementById('search-results').innerHTML = ''; return; }
  searchTimer = setTimeout(() => doSearch(q), 300);
});

async function doSearch(q) {
  const d = await fetchJSON('/api/inspector/search?q=' + encodeURIComponent(q));
  const el = document.getElementById('search-results');
  if (!d || !d.results || d.results.length === 0) { el.innerHTML = '<div class="empty">No results for "' + escapeHtml(q) + '"</div>'; return; }
  el.innerHTML = d.results.map(renderMemory).join('');
}

async function refreshAll() {
  await Promise.all([loadChecklist(), loadHealth(), loadSummary(), loadRecent(), loadVersion()]);
}

refreshAll();
setInterval(refreshAll, 5000);
</script>
</body>
</html>"""
