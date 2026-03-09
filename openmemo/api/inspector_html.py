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
:root {
  --bg-primary: #0a0e17;
  --bg-card: #111827;
  --bg-card-hover: #1a2332;
  --bg-input: #0d1321;
  --border: #1e293b;
  --border-light: #334155;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent: #6366f1;
  --accent-light: #818cf8;
  --green: #22c55e;
  --green-bg: rgba(34,197,94,0.12);
  --amber: #f59e0b;
  --amber-bg: rgba(245,158,11,0.12);
  --red: #ef4444;
  --red-bg: rgba(239,68,68,0.12);
  --blue: #3b82f6;
  --blue-bg: rgba(59,130,246,0.12);
  --purple: #a78bfa;
  --purple-bg: rgba(167,139,250,0.12);
  --cyan: #22d3ee;
  --radius: 16px;
  --radius-sm: 10px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg-primary); color: var(--text-primary); line-height: 1.5; -webkit-font-smoothing: antialiased; }

.header { background: linear-gradient(135deg, #111827 0%, #0f172a 100%); border-bottom: 1px solid var(--border); padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; backdrop-filter: blur(12px); }
.header-left { display: flex; align-items: center; gap: 14px; }
.logo-icon { width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%); display: flex; align-items: center; justify-content: center; font-size: 18px; }
.header h1 { font-size: 18px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.3px; }
.header-right { display: flex; align-items: center; gap: 16px; }
.header .version-text { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); display: inline-block; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.refresh-label { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }

.page { max-width: 1280px; margin: 0 auto; padding: 28px 32px 48px; }

.hero-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.hero-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 22px 24px; position: relative; overflow: hidden; transition: border-color 0.2s, transform 0.15s; }
.hero-card:hover { border-color: var(--border-light); transform: translateY(-1px); }
.hero-card .hero-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-muted); margin-bottom: 8px; }
.hero-card .hero-value { font-size: 32px; font-weight: 700; letter-spacing: -1px; color: var(--text-primary); }
.hero-card .hero-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.hero-card .hero-icon { position: absolute; top: 18px; right: 20px; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.hero-icon.green { background: var(--green-bg); }
.hero-icon.blue { background: var(--blue-bg); }
.hero-icon.purple { background: var(--purple-bg); }
.hero-icon.amber { background: var(--amber-bg); }

.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.grid-full { grid-column: 1 / -1; }

.card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; transition: border-color 0.2s; }
.card:hover { border-color: var(--border-light); }
.card-title { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-muted); margin-bottom: 18px; display: flex; align-items: center; gap: 8px; }
.card-title .dot { width: 6px; height: 6px; border-radius: 50%; }
.card-title .dot.green { background: var(--green); }
.card-title .dot.blue { background: var(--blue); }
.card-title .dot.purple { background: var(--accent); }
.card-title .dot.amber { background: var(--amber); }
.card-title .dot.cyan { background: var(--cyan); }

.check-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.check-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: var(--radius-sm); background: rgba(255,255,255,0.02); border: 1px solid transparent; transition: all 0.15s; }
.check-item:hover { background: rgba(255,255,255,0.04); }
.check-item.ok { border-left: 3px solid var(--green); }
.check-item.fail { border-left: 3px solid var(--red); }
.check-item.warning { border-left: 3px solid var(--amber); }
.check-item.cold_start { border-left: 3px solid var(--text-muted); }
.check-icon { width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
.check-icon.ok { background: var(--green-bg); color: var(--green); }
.check-icon.fail { background: var(--red-bg); color: var(--red); }
.check-icon.warning { background: var(--amber-bg); color: var(--amber); }
.check-icon.cold_start { background: rgba(100,116,139,0.15); color: var(--text-muted); }
.check-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }

.dist-group { margin-bottom: 16px; }
.dist-group:last-child { margin-bottom: 0; }
.dist-group-title { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 10px; }
.dist-row { display: flex; align-items: center; gap: 12px; padding: 5px 0; }
.dist-label { font-size: 13px; color: var(--text-secondary); min-width: 100px; font-weight: 500; }
.dist-track { flex: 1; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 3px; transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1); }
.dist-fill.type { background: linear-gradient(90deg, var(--accent), var(--accent-light)); }
.dist-fill.scene { background: linear-gradient(90deg, var(--green), #4ade80); }
.dist-count { font-size: 13px; color: var(--text-muted); min-width: 32px; text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }

.timeline { position: relative; }
.timeline-item { display: flex; gap: 16px; padding: 12px 0; position: relative; }
.timeline-item:not(:last-child)::before { content: ''; position: absolute; left: 15px; top: 38px; bottom: 0; width: 1px; background: var(--border); }
.timeline-dot { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; position: relative; z-index: 1; }
.timeline-dot.preference { background: var(--blue-bg); border: 1px solid rgba(59,130,246,0.3); }
.timeline-dot.task_execution { background: var(--green-bg); border: 1px solid rgba(34,197,94,0.3); }
.timeline-dot.fact { background: var(--purple-bg); border: 1px solid rgba(167,139,250,0.3); }
.timeline-dot.decision { background: var(--amber-bg); border: 1px solid rgba(245,158,11,0.3); }
.timeline-dot.observation { background: rgba(34,211,238,0.1); border: 1px solid rgba(34,211,238,0.3); }
.timeline-body { flex: 1; min-width: 0; }
.timeline-content { font-size: 14px; color: var(--text-primary); line-height: 1.5; margin-bottom: 6px; }
.timeline-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pill { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: 0.3px; }
.pill.scene { background: rgba(59,130,246,0.12); color: #60a5fa; }
.pill.type { background: rgba(34,197,94,0.12); color: #4ade80; }
.pill.score { background: rgba(245,158,11,0.12); color: #fbbf24; }
.pill.time { background: rgba(100,116,139,0.12); color: var(--text-muted); }

.search-wrap { position: relative; margin-bottom: 16px; }
.search-icon { position: absolute; left: 16px; top: 50%; transform: translateY(-50%); color: var(--text-muted); font-size: 14px; pointer-events: none; }
.search-input { width: 100%; padding: 14px 16px 14px 42px; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-primary); font-size: 14px; outline: none; transition: border-color 0.2s, box-shadow 0.2s; }
.search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
.search-input::placeholder { color: var(--text-muted); }
.search-results { min-height: 20px; }

.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.info-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.info-item:nth-last-child(-n+2) { border-bottom: none; }
.info-item:nth-child(odd) { padding-right: 20px; }
.info-item:nth-child(even) { padding-left: 20px; border-left: 1px solid rgba(255,255,255,0.04); }
.info-label { font-size: 13px; color: var(--text-muted); }
.info-value { font-size: 13px; color: var(--text-primary); font-weight: 600; font-variant-numeric: tabular-nums; }

.empty-state { text-align: center; padding: 32px 16px; color: var(--text-muted); font-size: 13px; }
.empty-state .empty-icon { font-size: 28px; margin-bottom: 8px; opacity: 0.5; }

@media (max-width: 768px) {
  .hero-stats { grid-template-columns: 1fr 1fr; }
  .grid { grid-template-columns: 1fr; }
  .check-grid { grid-template-columns: 1fr; }
  .info-grid { grid-template-columns: 1fr; }
  .info-item:nth-child(even) { padding-left: 0; border-left: none; }
  .info-item:nth-child(odd) { padding-right: 0; }
  .page { padding: 16px; }
  .header { padding: 16px; }
}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="logo-icon">M</div>
    <h1>Memory Inspector</h1>
  </div>
  <div class="header-right">
    <span class="version-text" id="header-version"></span>
    <span class="refresh-label"><span class="live-dot"></span> Live</span>
  </div>
</div>

<div class="page">
  <div class="hero-stats" id="hero-stats"></div>

  <div class="grid">
    <div class="card grid-full">
      <div class="card-title"><span class="dot green"></span> System Health</div>
      <div class="check-grid" id="checklist"></div>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-title"><span class="dot purple"></span> Type Distribution</div>
      <div id="type-dist"></div>
    </div>
    <div class="card">
      <div class="card-title"><span class="dot green"></span> Scene Distribution</div>
      <div id="scene-dist"></div>
    </div>
  </div>

  <div class="grid">
    <div class="card grid-full">
      <div class="card-title"><span class="dot cyan"></span> Recent Memory Stream</div>
      <div class="timeline" id="recent-writes"></div>
    </div>
  </div>

  <div class="grid">
    <div class="card grid-full">
      <div class="card-title"><span class="dot blue"></span> Memory Search</div>
      <div class="search-wrap">
        <span class="search-icon">&#x1F50D;</span>
        <input type="text" class="search-input" id="search-input" placeholder="Search through agent memories..." />
      </div>
      <div class="search-results" id="search-results"></div>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-title"><span class="dot amber"></span> System Info</div>
      <div class="info-grid" id="system-info"></div>
    </div>
    <div class="card">
      <div class="card-title"><span class="dot purple"></span> Version</div>
      <div id="update-status"></div>
    </div>
  </div>
</div>

<script>
const API = '';

function escapeHtml(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

async function fetchJSON(url) {
  try { const r = await fetch(API + url); return await r.json(); } catch(e) { return null; }
}

function typeIcon(t) {
  const map = { preference: '&#x2764;', task_execution: '&#x26A1;', fact: '&#x1F4CC;', decision: '&#x2696;', observation: '&#x1F441;' };
  return map[t] || '&#x1F4AD;';
}

function renderHero(memories, cells, scenes, status) {
  document.getElementById('hero-stats').innerHTML =
    '<div class="hero-card"><div class="hero-label">Total Memories</div><div class="hero-value">' + memories + '</div><div class="hero-sub">stored memory entries</div><div class="hero-icon blue">&#x1F9E0;</div></div>' +
    '<div class="hero-card"><div class="hero-label">Memory Cells</div><div class="hero-value">' + cells + '</div><div class="hero-sub">atomic knowledge units</div><div class="hero-icon purple">&#x2B21;</div></div>' +
    '<div class="hero-card"><div class="hero-label">Active Scenes</div><div class="hero-value">' + scenes + '</div><div class="hero-sub">context groups</div><div class="hero-icon green">&#x1F3AF;</div></div>' +
    '<div class="hero-card"><div class="hero-label">System Status</div><div class="hero-value" style="color:var(--green)">' + (status === 'ok' ? '&#x2713; Healthy' : status) + '</div><div class="hero-sub">all checks passed</div><div class="hero-icon amber">&#x2699;</div></div>';
}

async function loadChecklist() {
  const d = await fetchJSON('/api/inspector/checklist');
  if (!d) { document.getElementById('checklist').innerHTML = '<div class="empty-state"><div class="empty-icon">&#x26A0;</div>Could not load</div>'; return; }
  document.getElementById('checklist').innerHTML = d.checks.map(c => {
    const icon = c.status === 'ok' ? '&#x2713;' : c.status === 'warning' ? '!' : c.status === 'cold_start' ? '&#x25CB;' : '&#x2717;';
    return '<div class="check-item ' + c.status + '"><div class="check-icon ' + c.status + '">' + icon + '</div><span class="check-label">' + c.name + '</span></div>';
  }).join('');
}

async function loadSummary() {
  const d = await fetchJSON('/api/inspector/memory-summary');
  const h = await fetchJSON('/api/inspector/health');
  if (!d) return;
  renderHero(d.total_memories || 0, d.total_cells || 0, d.total_scenes || 0, h ? h.status : '-');

  if (d.type_distribution && Object.keys(d.type_distribution).length > 0) {
    const maxT = Math.max(...Object.values(d.type_distribution), 1);
    document.getElementById('type-dist').innerHTML = Object.entries(d.type_distribution).map(([k,v]) =>
      '<div class="dist-row"><span class="dist-label">' + k + '</span><div class="dist-track"><div class="dist-fill type" style="width:' + ((v/maxT)*100) + '%"></div></div><span class="dist-count">' + v + '</span></div>'
    ).join('');
  }
  if (d.scene_distribution && Object.keys(d.scene_distribution).length > 0) {
    const maxS = Math.max(...Object.values(d.scene_distribution), 1);
    document.getElementById('scene-dist').innerHTML = Object.entries(d.scene_distribution).map(([k,v]) =>
      '<div class="dist-row"><span class="dist-label">' + (k||'(none)') + '</span><div class="dist-track"><div class="dist-fill scene" style="width:' + ((v/maxS)*100) + '%"></div></div><span class="dist-count">' + v + '</span></div>'
    ).join('');
  }
}

async function loadHealth() {
  const d = await fetchJSON('/api/inspector/health');
  if (!d) return;
  document.getElementById('system-info').innerHTML = [
    ['Backend', d.backend || 'openmemo'],
    ['Status', d.status || '-'],
    ['API Version', d.api_version || '-'],
    ['Engine', d.engine_version || '-'],
    ['Memories', d.total_memories || 0],
    ['Scenes', d.total_scenes || 0],
  ].map(([k,v]) => '<div class="info-item"><span class="info-label">' + k + '</span><span class="info-value">' + v + '</span></div>').join('');
}

function renderTimelineItem(m) {
  const content = m.content || m.text || '';
  const scene = m.scene || '';
  const mtype = m.memory_type || m.cell_type || m.type || '';
  const score = m.score != null ? m.score.toFixed(2) : '';
  let meta = '';
  if (scene) meta += '<span class="pill scene">' + scene + '</span>';
  if (mtype) meta += '<span class="pill type">' + mtype + '</span>';
  if (score) meta += '<span class="pill score">' + score + '</span>';
  return '<div class="timeline-item"><div class="timeline-dot ' + mtype + '">' + typeIcon(mtype) + '</div><div class="timeline-body"><div class="timeline-content">' + escapeHtml(content.substring(0, 200)) + '</div><div class="timeline-meta">' + meta + '</div></div></div>';
}

async function loadRecent() {
  const d = await fetchJSON('/api/inspector/recent');
  const el = document.getElementById('recent-writes');
  if (!d || !d.recent || d.recent.length === 0) { el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#x1F331;</div>No memories yet &mdash; cold start</div>'; return; }
  el.innerHTML = d.recent.map(renderTimelineItem).join('');
}

async function loadVersion() {
  const d = await fetchJSON('/version');
  if (!d) return;
  document.getElementById('update-status').innerHTML = [
    ['OpenMemo Core', d.latest_core],
    ['Adapter', d.latest_adapter],
    ['Schema', 'v' + d.schema_version],
  ].map(([k,v]) => '<div class="info-item" style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04)"><span class="info-label">' + k + '</span><span class="info-value">' + v + '</span></div>').join('');
  document.getElementById('header-version').textContent = 'v' + d.latest_core;
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
  if (!d || !d.results || d.results.length === 0) { el.innerHTML = '<div class="empty-state">No results for &ldquo;' + escapeHtml(q) + '&rdquo;</div>'; return; }
  el.innerHTML = '<div class="timeline">' + d.results.map(renderTimelineItem).join('') + '</div>';
}

async function refreshAll() {
  await Promise.all([loadChecklist(), loadSummary(), loadHealth(), loadRecent(), loadVersion()]);
}
refreshAll();
setInterval(refreshAll, 5000);
</script>
</body>
</html>"""
