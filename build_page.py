#!/usr/bin/env python3
"""radar_out.json + sources.json -> site/index.html: a single self-contained dashboard page (inline CSS/JS, data embedded).

Env: RADAR_DATA (dir holding radar_out.json; default <repo>/data), SITE_DIR (output dir; default <repo>/site),
     PAGE_REPO (repo URL for the footer link)."""
import json, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_dash

ROOT = build_dash.ROOT
REPO_URL = os.environ.get("PAGE_REPO", "https://github.com/TheBurntWaffl3/jadar")
EXTRA = ["salary", "salaryMin", "salaryMax", "workMode", "employment", "travel", "relocation", "reqSnippet"]

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Job Radar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&display=swap">
<style>
:root {
  color-scheme: light;
  --page: #ffffff; --ink: #0b0b0c; --ink-2: #3f3f44; --muted: #737379; --line: #ececee; --card: #f7f7f8; --pill: #f4f4f5;
  --ember: #fa5d19; --tint: #fff0e8; --tint-2: #ffd5bf; --on-ember: #ffffff;
  --good: #0ca30c; --maybe: #fa5d19; --no: #8a8a90; --crit: #d03b3b;
  --fail-wash: rgba(208,59,59,0.06);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0b0b0c; --ink: #ececee; --ink-2: #c6c6cb; --muted: #8a8a90; --line: #232326; --card: #141416; --pill: #1b1b1e;
    --tint: #2a1709; --tint-2: #3d2010; --on-ember: #ffffff; --good: #2bbf2b; --no: #737379; --fail-wash: rgba(208,59,59,0.14);
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0b0b0c; --ink: #ececee; --ink-2: #c6c6cb; --muted: #8a8a90; --line: #232326; --card: #141416; --pill: #1b1b1e;
  --tint: #2a1709; --tint-2: #3d2010; --on-ember: #ffffff; --good: #2bbf2b; --no: #737379; --fail-wash: rgba(208,59,59,0.14);
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.45 "Inter Tight", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
body { overflow-x: hidden; -webkit-font-smoothing: antialiased; }
a { color: inherit; }
main { max-width: 1180px; margin: 0 auto; padding: 16px; }
.mono { font-family: ui-monospace, Menlo, Consolas, "SF Mono", monospace; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }

/* hero */
.hero { background: var(--ember); color: var(--on-ember); border-radius: 24px; padding: 36px 28px 28px; margin-top: 8px; }
.hero h1 { font-size: clamp(40px, 7vw, 64px); line-height: 1; letter-spacing: -0.035em; font-weight: 600; margin: 0 0 18px; }
.hero .meta { opacity: .92; }
.hero .meta .sep { opacity: .55; margin: 0 .35em; }
.hero .who { margin-top: 6px; font-size: 14px; opacity: .85; }

/* stat strip */
.stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 0; margin: 22px 0 8px; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.stat { padding: 16px 12px 14px; border-left: 1px solid var(--line); }
.stat:first-child { border-left: 0; }
.stat .label { color: var(--muted); }
.stat .value { font-size: 34px; font-weight: 600; letter-spacing: -0.03em; line-height: 1.1; margin-top: 6px; font-variant-numeric: tabular-nums; }
.stat .value.ember { color: var(--ember); } .stat .value.good { color: var(--good); }
.stat .sub { color: var(--muted); font-size: 12.5px; margin-top: 2px; }

h2 { font-size: 28px; letter-spacing: -0.03em; font-weight: 600; margin: 34px 0 6px; }
h2 + .lede { color: var(--muted); margin: 0 0 14px; }

/* controls */
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 12px; }
.seg { display: inline-flex; background: var(--pill); border-radius: 999px; padding: 3px; }
.seg button { background: transparent; color: var(--ink); border: 0; padding: 7px 14px; font: inherit; font-size: 13.5px; font-weight: 500; border-radius: 999px; cursor: pointer; min-height: 32px; }
.seg button[aria-pressed="true"] { background: var(--ink); color: var(--page); }
.ctl { font: inherit; font-size: 13.5px; font-weight: 500; padding: 8px 14px; border: 0; border-radius: 999px; background: var(--pill); color: var(--ink); min-height: 38px; }
select.ctl { appearance: none; -webkit-appearance: none; padding-right: 30px; background-image: linear-gradient(45deg, transparent 50%, currentColor 50%), linear-gradient(135deg, currentColor 50%, transparent 50%); background-position: calc(100% - 17px) 55%, calc(100% - 12px) 55%; background-size: 5px 5px; background-repeat: no-repeat; cursor: pointer; }
input.ctl { flex: 1 1 180px; min-width: 150px; }
input.ctl::placeholder { color: var(--muted); }
.count { color: var(--muted); margin-left: auto; white-space: nowrap; }

/* table */
.wrap { border-top: 1px solid var(--line); }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; vertical-align: top; padding: 12px 10px; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 500; white-space: nowrap; user-select: none; }
th.sortable { cursor: pointer; } th.sortable:hover { color: var(--ink); }
th .arrow { display: inline-block; width: 1em; opacity: 0; } th[aria-sort] .arrow { opacity: 1; color: var(--ink); }
th[aria-sort="ascending"] .arrow::after { content: "↑"; } th[aria-sort="descending"] .arrow::after { content: "↓"; }
tr.row { cursor: pointer; } tr.row:hover td { background: var(--card); }
tr.row[aria-expanded="true"] td { background: var(--card); border-bottom-color: transparent; }
td.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
.fit { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; white-space: nowrap; }
.fit::before { content: ""; width: 9px; height: 9px; border-radius: 50%; background: var(--no); flex: 0 0 auto; }
.fit.Yes::before { background: var(--good); } .fit.Maybe::before { background: var(--maybe); }
.co { font-weight: 500; } .sm-co { display: none; }
.role a { font-weight: 600; text-decoration: none; } .role a:hover { text-decoration: underline; }
.role .loc { color: var(--muted); font-size: 13px; margin-top: 2px; }
.tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
.tag { display: inline-block; font-size: 11.5px; font-weight: 600; border-radius: 999px; padding: 2px 8px; background: var(--pill); color: var(--ink-2); white-space: nowrap; }
.tag.new { background: var(--ember); color: var(--on-ember); }
.tag.closing { background: var(--tint); color: var(--ember); }
.kind { color: var(--muted); display: block; margin-top: 2px; }
td.date { white-space: nowrap; }
.why { color: var(--ink-2); font-size: 13.5px; max-width: 320px; }
.chev { color: var(--muted); width: 28px; text-align: center; }
.chev::after { content: "›"; display: inline-block; font-size: 20px; line-height: 1; transition: transform .15s; }
tr.row[aria-expanded="true"] .chev::after { transform: rotate(90deg); }
tr.detail td { padding: 0 10px 16px; background: var(--card); }
.panel { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 28px; padding: 12px 6px 4px; }
.kv { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px 18px; align-content: start; }
.kv .k { color: var(--muted); margin-bottom: 3px; }
.kv .v { font-size: 14px; }
.snip { background: var(--page); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; font-size: 13px; line-height: 1.5; color: var(--ink-2); }
.snip .k { margin-bottom: 6px; }
.btn { display: inline-flex; align-items: center; gap: 6px; background: var(--ink); color: var(--page); border-radius: 999px; padding: 8px 16px; font-weight: 600; font-size: 13.5px; text-decoration: none; margin-top: 12px; }
.empty { padding: 24px 10px; color: var(--muted); }

/* boards */
.boards-head { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin: 10px 0; }
.boards-head .sum { color: var(--ink-2); }
#boards { display: none; } #boards.open { display: block; }
#orgs th { cursor: default; }
tr.fail td { background: var(--fail-wash); } tr.gap td { color: var(--muted); }
.st { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.st::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--no); }
.st.ok::before { background: var(--good); } .st.failing::before { background: var(--crit); }
.note { color: var(--muted); font-size: 13px; }

footer { color: var(--muted); font-size: 13px; margin: 36px 0 12px; }
footer a { color: var(--ink); }

@media (max-width: 900px) { .stats { grid-template-columns: repeat(3, 1fr); } .stat:nth-child(4) { border-left: 0; } .stat:nth-child(-n+3) { border-bottom: 1px solid var(--line); } }
@media (max-width: 640px) {
  main { padding: 12px 16px; }
  .hero { padding: 28px 20px 22px; border-radius: 20px; }
  .stat .value { font-size: 26px; }
  .stats { grid-template-columns: repeat(2, 1fr); }
  .stat:nth-child(3), .stat:nth-child(5) { border-left: 0; } .stat:nth-child(4) { border-left: 1px solid var(--line); }
  .stat:nth-child(-n+4) { border-bottom: 1px solid var(--line); }
  .count { margin-left: 0; width: 100%; }
  th, td { padding: 10px 8px; }
  /* roles become cards */
  #roles, #roles tbody, #roles tr, #roles td { display: block; }
  #roles thead { display: none; }
  #roles tr.row { padding: 12px 0; border-bottom: 1px solid var(--line); }
  #roles tr.row td { padding: 0; border: 0; background: transparent !important; }
  #roles td.fitco { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
  #roles td.co { display: none; } #roles .sm-co { display: inline; }
  #roles td.role { margin-bottom: 6px; }
  #roles td.kvl { display: inline; font-size: 13px; color: var(--ink-2); }
  #roles td.kvl:empty { display: none; }
  #roles td.kvl + td.kvl:not(:empty)::before { content: " · "; color: var(--muted); }
  #roles td.kvl .kind { display: inline; margin-left: 4px; }
  #roles td.why { display: block; margin-top: 6px; max-width: none; }
  #roles td.chev { display: none; }
  #roles tr.detail td { padding: 0 0 14px; border-radius: 16px; }
  .panel { grid-template-columns: 1fr; padding: 12px; }
  #orgs .hide-sm { display: none; }
}
</style>
</head>
<body>
<main>
<section class="hero">
  <h1>Job radar.</h1>
  <div class="meta mono" id="meta"></div>
  <div class="who" id="who"></div>
</section>

<section class="stats" id="stats" aria-label="Summary"></section>

<h2>Roles.</h2>
<p class="lede">Entry-level fits across the boards. Click a row for the full requirements.</p>
<div class="controls" id="controls">
  <div class="seg" role="group" aria-label="Fit">
    <button type="button" data-fit="fits" aria-pressed="true">Yes + Maybe</button>
    <button type="button" data-fit="Yes" aria-pressed="false">Yes</button>
    <button type="button" data-fit="all" aria-pressed="false">All</button>
  </div>
  <select class="ctl" id="sector" aria-label="Sector"><option value="">All sectors</option></select>
  <select class="ctl" id="disc" aria-label="Field"><option value="">All fields</option></select>
  <select class="ctl" id="days" aria-label="Posted within">
    <option value="">Any date</option><option value="7">Posted in 7 days</option><option value="30">Posted in 30 days</option>
  </select>
  <select class="ctl" id="sort" aria-label="Sort by">
    <option value="fit">Sort: Fit</option><option value="date">Sort: Newest</option><option value="applyBy">Sort: Apply-by soonest</option>
    <option value="salary">Sort: Salary high→low</option><option value="company">Sort: Company</option><option value="minYears">Sort: Min yrs</option>
  </select>
  <input class="ctl" type="search" id="q" placeholder="Search company, title, location, why" aria-label="Search">
  <span class="count mono" id="count"></span>
</div>
<div class="wrap">
  <table id="roles">
    <thead><tr>
      <th class="sortable" data-sort="fit">Fit<span class="arrow"></span></th>
      <th class="sortable" data-sort="company">Company<span class="arrow"></span></th>
      <th>Role</th>
      <th class="sortable" data-sort="discipline">Field<span class="arrow"></span></th>
      <th class="sortable" data-sort="salary">Salary<span class="arrow"></span></th>
      <th class="sortable" data-sort="date">Date<span class="arrow"></span></th>
      <th>Why</th>
      <th></th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
</div>

<h2>Boards.</h2>
<div class="boards-head">
  <span class="sum" id="boards-sum"></span>
  <button type="button" class="ctl" id="boards-toggle" aria-expanded="false" aria-controls="boards">Show boards</button>
</div>
<div id="boards">
  <table id="orgs">
    <thead><tr><th>Organization</th><th class="hide-sm">Sector</th><th>Platform</th><th>Status</th><th class="num">Roles</th><th class="num">Fits</th><th>Note</th></tr></thead>
    <tbody id="org-rows"></tbody>
  </table>
</div>

<footer>Read-only scan; never applies to jobs. Source: <a href="__REPO__">__REPO_SHORT__</a>.</footer>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const NEW = new Set(D.new || []);
  const today = new Date(D.today + 'T00:00:00');
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const fmt = iso => { if (!iso) return ''; const [y,m,d] = iso.split('-').map(Number); return MON[m-1] + ' ' + d + (y !== today.getFullYear() ? ', ' + y : ''); };
  const fmtLong = iso => { if (!iso) return ''; const [y,m,d] = iso.split('-').map(Number); return MON[m-1] + ' ' + d + ', ' + y; };
  const daysTo = iso => { if (!iso) return null; const [y,m,d] = iso.split('-').map(Number); return Math.round((new Date(y, m-1, d) - today) / 86400000); };
  const num = n => n == null ? '' : n.toLocaleString('en-US');
  const FITRANK = {Yes: 0, Maybe: 1, No: 2};
  const roles = D.roles.map(r => Object.assign({}, r, {_new: NEW.has(r.url), _dt: daysTo(r.applyBy), _q: [r.company, r.title, r.location, r.why, r.discipline, r.salary].join(' ').toLowerCase()}));

  // hero + stats
  const sc = D.scanned ? new Date(D.scanned) : null;
  const okN = D.orgs.filter(o => o.status === 'OK').length, failN = D.orgs.filter(o => o.status === 'Failing').length, gapN = D.orgs.filter(o => o.status === 'Not covered yet').length;
  const stamp = sc ? sc.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'}) + ' ' + sc.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'}) : D.today;
  $('#meta').innerHTML = ['Scanned ' + esc(stamp), 'rules ' + esc(D.rulesVersion || '—'), D.fullRead ? 'full re-read' : 'incremental', okN + '/' + (okN + failN) + ' boards'].join('<span class="sep">·</span>');
  if (D.profileName) $('#who').textContent = 'For ' + D.profileName;
  const fits = roles.filter(r => r.fit !== 'No');
  const week = fits.filter(r => r.dateKind === 'posted' && r.date && daysTo(r.date) >= -7).length;
  const closing = fits.filter(r => r._dt != null && r._dt >= 0 && r._dt <= 14).length;
  const stats = [
    ['Yes', roles.filter(r => r.fit === 'Yes').length, 'strong fits', 'good'],
    ['Maybe', roles.filter(r => r.fit === 'Maybe').length, 'worth a look', 'ember'],
    ['Posted 7d', week, 'Yes + Maybe', ''],
    ['Closing 14d', closing, 'apply-by known', closing ? 'ember' : ''],
    ['Roles', roles.length, 'in-field, US', ''],
    ['Boards OK', okN + ' / ' + (okN + failN), failN ? failN + ' failing' : 'none failing', ''],
  ];
  $('#stats').innerHTML = stats.map(([l, v, s, c]) => `<div class="stat"><div class="label mono">${esc(l)}</div><div class="value ${c}">${esc(v)}</div><div class="sub">${esc(s)}</div></div>`).join('');

  // controls
  const state = {fit: 'fits', sector: '', disc: '', days: '', q: '', sort: 'fit', dir: 'asc', open: null};
  const fill = (sel, vals) => { vals.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }); };
  fill($('#sector'), [...new Set(roles.map(r => r.sector).filter(Boolean))].sort());
  fill($('#disc'), [...new Set(roles.map(r => r.discipline).filter(Boolean))].sort());
  document.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-pressed', x === b)); state.fit = b.dataset.fit; render();
  }));
  ['sector', 'disc', 'days'].forEach(k => $('#' + k).addEventListener('change', e => { state[k] = e.target.value; render(); }));
  $('#q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(); });
  const DEFAULT_DIR = {fit: 'asc', date: 'desc', applyBy: 'asc', salary: 'desc', company: 'asc', minYears: 'asc', discipline: 'asc'};
  $('#sort').addEventListener('change', e => { state.sort = e.target.value; state.dir = DEFAULT_DIR[state.sort]; render(); });
  document.querySelectorAll('th.sortable').forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.sort;
    state.dir = state.sort === k ? (state.dir === 'asc' ? 'desc' : 'asc') : DEFAULT_DIR[k]; state.sort = k;
    if ([...$('#sort').options].some(o => o.value === k)) $('#sort').value = k; render();
  }));

  // sorting
  const cmpNum = (a, b) => (a == null ? 0 : a) - (b == null ? 0 : b);  // nulls are moved last before this runs
  const cmpStr = (a, b) => (a || '').localeCompare(b || '');
  const KEYS = {
    fit: (a, b) => FITRANK[a.fit] - FITRANK[b.fit] || cmpStr(b.date, a.date),
    date: (a, b) => cmpStr(a.date, b.date) || FITRANK[a.fit] - FITRANK[b.fit],
    applyBy: (a, b) => cmpNum(a._dt, b._dt) || FITRANK[a.fit] - FITRANK[b.fit],
    salary: (a, b) => cmpNum(a.salaryMax == null ? a.salaryMin : a.salaryMax, b.salaryMax == null ? b.salaryMin : b.salaryMax) || FITRANK[a.fit] - FITRANK[b.fit],
    company: (a, b) => cmpStr(a.company, b.company) || FITRANK[a.fit] - FITRANK[b.fit] || cmpStr(b.date, a.date),
    minYears: (a, b) => cmpNum(a.minYears, b.minYears) || FITRANK[a.fit] - FITRANK[b.fit],
    discipline: (a, b) => cmpStr(a.discipline, b.discipline) || FITRANK[a.fit] - FITRANK[b.fit] || cmpStr(b.date, a.date),
  };
  function sorted(list) {
    const f = KEYS[state.sort]; const sign = state.dir === 'desc' ? -1 : 1;
    return list.slice().sort((a, b) => {
      const nullA = state.sort === 'applyBy' ? a._dt == null : state.sort === 'salary' ? a.salaryMax == null && a.salaryMin == null : state.sort === 'minYears' ? a.minYears == null : false;
      const nullB = state.sort === 'applyBy' ? b._dt == null : state.sort === 'salary' ? b.salaryMax == null && b.salaryMin == null : state.sort === 'minYears' ? b.minYears == null : false;
      if (nullA !== nullB) return nullA ? 1 : -1;
      return sign * f(a, b);
    });
  }

  // rows
  function tagsFor(r) {
    const t = [];
    if (r._new) t.push('<span class="tag new">New</span>');
    if (r._dt != null && r._dt >= 0 && r._dt <= 10) t.push(`<span class="tag closing">${r._dt === 0 ? 'Closes today' : 'Closes in ' + r._dt + 'd'}</span>`);
    if (r.workMode) t.push(`<span class="tag">${esc(r.workMode)}</span>`);
    if (r.employment && r.employment !== 'Full-time') t.push(`<span class="tag">${esc(r.employment)}</span>`);
    return t.length ? `<div class="tags">${t.join('')}</div>` : '';
  }
  function kv(k, v) { return v == null || v === '' ? '' : `<div><div class="k mono">${esc(k)}</div><div class="v">${esc(v)}</div></div>`; }
  function detail(r) {
    const yrs = r.minYears == null ? 'not stated' : r.minYears + (r.schoolExpOk ? ' (school/internship counts)' : '');
    const pay = r.salary ? r.salary + (/\/hr$/.test(r.salary) && r.salaryMin != null ? ' · $' + num(r.salaryMin) + (r.salaryMax != null && r.salaryMax !== r.salaryMin ? '–$' + num(r.salaryMax) : '') + ' annualized' : '') : null;
    const left = [kv('Min experience', yrs), kv('Degree', r.degree), kv('Major', r.majorReq), kv('GPA', r.gpaReq), kv('Clearance', r.clearance), kv('Citizenship', r.citizenship),
      kv('Grad window', r.gradReq), kv('Start', r.startReq), kv('Start window', r.startWindow), kv('Apply by', r.applyBy ? fmtLong(r.applyBy) + (r._dt != null ? ' (' + (r._dt < 0 ? 'passed' : r._dt + ' days') + ')' : '') : null),
      kv('Pay', pay), kv('Work mode', r.workMode), kv('Employment', r.employment), kv('Travel', r.travel), kv('Relocation', r.relocation === true ? 'offered' : r.relocation === false ? 'not offered' : null),
      kv('Posted', r.date ? fmtLong(r.date) + ' (' + r.dateKind + ')' : null), kv('First seen', r.firstSeen ? fmtLong(r.firstSeen) : null), kv('Sector', r.sector)].join('');
    const snip = r.reqSnippet ? `<div class="snip"><div class="k mono">Minimum qualifications</div>${esc(r.reqSnippet)}</div>` : `<div class="snip"><div class="k mono">Why</div>${esc(r.why)}</div>`;
    return `<div class="panel"><div class="kv">${left}</div><div>${snip}<a class="btn" href="${esc(r.url)}" target="_blank" rel="noopener">Open posting ↗</a></div></div>`;
  }
  function render() {
    let list = roles.filter(r => state.fit === 'all' || (state.fit === 'fits' ? r.fit !== 'No' : r.fit === state.fit));
    if (state.sector) list = list.filter(r => r.sector === state.sector);
    if (state.disc) list = list.filter(r => r.discipline === state.disc);
    if (state.days) list = list.filter(r => r.dateKind === 'posted' && r.date && daysTo(r.date) >= -Number(state.days));
    if (state.q) list = list.filter(r => r._q.includes(state.q));
    list = sorted(list);
    document.querySelectorAll('th.sortable').forEach(th => th.dataset.sort === state.sort ? th.setAttribute('aria-sort', state.dir === 'asc' ? 'ascending' : 'descending') : th.removeAttribute('aria-sort'));
    $('#count').textContent = list.length + ' of ' + roles.length + ' roles';
    if (!list.length) { $('#rows').innerHTML = '<tr><td colspan="8" class="empty">Nothing matches these filters.</td></tr>'; return; }
    $('#rows').innerHTML = list.map(r => {
      const open = state.open === r.id;
      return `<tr class="row" data-id="${esc(r.id)}" tabindex="0" aria-expanded="${open}">
<td class="fitco"><span class="fit ${esc(r.fit)}">${esc(r.fit)}</span><span class="co sm-co">${esc(r.company)}</span></td>
<td class="co">${esc(r.company)}</td>
<td class="role"><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>${r.location ? `<div class="loc">${esc(r.location)}</div>` : ''}${tagsFor(r)}</td>
<td class="kvl">${esc(r.discipline || '')}</td>
<td class="kvl num">${r.salary ? esc(r.salary) : '<span style="color:var(--muted)">—</span>'}</td>
<td class="kvl date">${esc(fmt(r.date))}<span class="kind mono">${esc(r.dateKind || '')}</span></td>
<td class="why">${esc(r.why)}</td>
<td class="chev" aria-hidden="true"></td></tr>` + (open ? `<tr class="detail"><td colspan="8">${detail(r)}</td></tr>` : '');
    }).join('');
  }
  $('#rows').addEventListener('click', e => {
    if (e.target.closest('a')) return;
    const tr = e.target.closest('tr.row'); if (!tr) return;
    state.open = state.open === tr.dataset.id ? null : tr.dataset.id; render();
    if (state.open) { const el = $(`tr.row[data-id="${state.open}"]`); if (el) el.focus({preventScroll: true}); }
  });
  $('#rows').addEventListener('keydown', e => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.classList.contains('row')) { e.preventDefault(); e.target.click(); }
  });

  // boards
  $('#boards-sum').textContent = `${okN} of ${okN + failN} boards read · ${failN} failing · ${gapN} not covered`;
  $('#boards-toggle').addEventListener('click', e => { const o = $('#boards').classList.toggle('open'); e.target.setAttribute('aria-expanded', o); e.target.textContent = o ? 'Hide boards' : 'Show boards'; });
  const rank = {Failing: 0, OK: 1, 'Not covered yet': 2};
  $('#org-rows').innerHTML = D.orgs.slice().sort((a, b) => rank[a.status] - rank[b.status] || a.org.localeCompare(b.org)).map(o => {
    const cls = o.status === 'OK' ? 'ok' : o.status === 'Failing' ? 'failing' : 'gap';
    return `<tr class="${cls === 'failing' ? 'fail' : cls === 'gap' ? 'gap' : ''}"><td>${esc(o.org)}</td><td class="hide-sm">${esc(o.sector)}</td><td>${esc(o.platform)}</td><td><span class="st ${cls}">${esc(o.status)}</span></td><td class="num">${o.roles == null ? '–' : o.roles}</td><td class="num">${o.fits == null ? '–' : o.fits}</td><td class="note">${esc(o.note || '')}</td></tr>`;
  }).join('');
  render();
})();
</script>
</body>
</html>
"""

def build(out, src, profile_name=None):
    """Return the HTML string for a radar_out.json dict and sources.json list."""
    roles, orgs = build_dash.datasets(out, src)
    by_url = {r["url"]: r for r in out["roles"]}
    for r in roles:  # extra listing facts (may be absent in older data); the requirements excerpt only for fits, to keep the page small
        src_r = by_url.get(r["url"], {})
        for k in EXTRA:
            if k not in r: r[k] = src_r.get(k)
        if r["fit"] == "No": r["reqSnippet"] = None
    roles = [{k: v for k, v in r.items() if v is not None and v is not False} for r in roles]  # drop empty keys: the page treats missing as null
    today = (out.get("scanned") or dt.date.today().isoformat())[:10]
    data = dict(roles=roles, orgs=orgs, new=[r["url"] for r in out.get("new", [])], today=today, scanned=out.get("scanned"),
                rulesVersion=out.get("rulesVersion"), fullRead=out.get("fullRead"), profileName=profile_name)
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    short = REPO_URL.replace("https://github.com/", "")
    return TEMPLATE.replace("__DATA__", blob).replace("__REPO__", REPO_URL).replace("__REPO_SHORT__", short)

def main():
    data = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
    site = os.environ.get("SITE_DIR", os.path.join(ROOT, "site"))
    with open(os.path.join(data, "radar_out.json")) as f: out = json.load(f)
    with open(os.path.join(ROOT, "sources.json")) as f: src = json.load(f)
    name = None
    try:
        prof = os.environ.get("PROFILE") or os.path.join(ROOT, "profiles", f"{out.get('profile', 'kevin')}.json")
        with open(prof) as f: name = json.load(f).get("name")
    except Exception: pass
    html = build(out, src, name)
    os.makedirs(site, exist_ok=True)
    with open(os.path.join(site, "index.html"), "w") as f: f.write(html)
    print(f"site/index.html: {len(html) // 1024} KB, {len(out['roles'])} roles")

if __name__ == "__main__":
    main()
