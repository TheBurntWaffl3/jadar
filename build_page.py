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
  --hero: #0b0b0c; --on-hero: #ffffff; --hero-muted: #9a9aa0;
  --ember: #2f5bea; --tint: #eaf0ff; --tint-2: #cbd8ff; --on-ember: #ffffff;
  --good: #0ca30c; --maybe: #2f5bea; --no: #8a8a90; --crit: #d03b3b;
  --fail-wash: rgba(208,59,59,0.06);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0b0b0c; --ink: #ececee; --ink-2: #c6c6cb; --muted: #8a8a90; --line: #232326; --card: #141416; --pill: #1b1b1e;
    --hero: #15151a; --on-hero: #ffffff; --hero-muted: #8a8a90; --ember: #5b82ff; --maybe: #5b82ff;
    --tint: #121a33; --tint-2: #1c2a55; --on-ember: #ffffff; --good: #2bbf2b; --no: #737379; --fail-wash: rgba(208,59,59,0.14);
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0b0b0c; --ink: #ececee; --ink-2: #c6c6cb; --muted: #8a8a90; --line: #232326; --card: #141416; --pill: #1b1b1e;
  --hero: #15151a; --on-hero: #ffffff; --hero-muted: #8a8a90; --ember: #5b82ff; --maybe: #5b82ff;
  --tint: #121a33; --tint-2: #1c2a55; --on-ember: #ffffff; --good: #2bbf2b; --no: #737379; --fail-wash: rgba(208,59,59,0.14);
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.45 "Inter Tight", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
body { overflow-x: hidden; -webkit-font-smoothing: antialiased; }
a { color: inherit; }
main { max-width: 1180px; margin: 0 auto; padding: 16px; }
.mono { font-family: ui-monospace, Menlo, Consolas, "SF Mono", monospace; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }

/* hero */
.hero { background: var(--hero); color: var(--on-hero); border: 1px solid var(--line); border-radius: 24px; padding: 36px 28px 28px; margin-top: 8px; }
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
.btn.alt { background: var(--pill); color: var(--ink); font-weight: 500; margin-top: 0; }
.people { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 14px; }
.people .k { margin-right: 4px; }
.empty { padding: 24px 10px; color: var(--muted); }

/* tabs + per-role state */
.tabsrow { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin: 0 0 10px; }
.seg.tabs { flex-wrap: wrap; }
.tabs button { display: inline-flex; align-items: center; gap: 6px; }
.tabs .badge { font-size: 10.5px; letter-spacing: .04em; opacity: .7; }
.tabs button[aria-pressed="true"] .badge { opacity: .85; }
.state-sum { color: var(--muted); }
.ctl.small { min-height: 32px; padding: 6px 12px; font-size: 13px; }
.sync-status { color: var(--muted); }
td.acts { white-space: nowrap; width: 96px; padding-left: 4px; padding-right: 4px; }
.ic { width: 28px; height: 28px; border: 0; border-radius: 999px; background: transparent; color: var(--muted); cursor: pointer; font-size: 15px; line-height: 1; padding: 0; vertical-align: middle; }
.ic:hover, .ic:focus-visible { background: var(--pill); color: var(--ink); outline: none; }
.ic.on.save { color: var(--ember); } .ic.on.applied { color: var(--good); } .ic.on.hide { color: var(--crit); }
.tag.closed { background: var(--pill); color: var(--muted); } .tag.status { background: var(--tint); color: var(--ember); } .tag.status.applied { background: rgba(12,163,12,.12); color: var(--good); }
tr.row.dim td .role a, tr.row.dim td.co, tr.row.dim td.why { color: var(--muted); }
.actrow { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 14px; }
.pbtn { font: inherit; font-size: 13px; font-weight: 600; border: 1px solid var(--line); background: var(--page); color: var(--ink); border-radius: 999px; padding: 7px 14px; cursor: pointer; min-height: 32px; }
.pbtn.on { background: var(--ink); color: var(--page); border-color: var(--ink); }
.note-in { font: inherit; font-size: 13.5px; flex: 1 1 220px; min-width: 160px; border: 1px solid var(--line); border-radius: 999px; padding: 7px 14px; background: var(--page); color: var(--ink); }
.note-in::placeholder { color: var(--muted); }
.applied-at { color: var(--muted); font-size: 13px; }
#datapanel { display: none; background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px; margin: 0 0 14px; }
#datapanel.open { display: block; }
.dp-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 6px 0; }
.dp-row + .dp-row { margin-top: 10px; }
.dp-head { margin: 10px 0 4px; }
.dp-note { color: var(--muted); font-size: 12.5px; }
.dp-row input[type="text"], .dp-row input[type="password"] { font: inherit; font-size: 13.5px; border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; background: var(--page); color: var(--ink); min-width: 140px; }
.dp-row input.wide { flex: 1 1 220px; }
.stats.n7 { grid-template-columns: repeat(7, 1fr); }

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
  #roles td.acts { display: flex; gap: 6px; width: auto; margin-top: 8px; }
  .seg.tabs button { padding: 6px 10px; font-size: 13px; }
  .stats.n7 { grid-template-columns: repeat(2, 1fr); }
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
<p class="lede">Entry-level fits across the boards. Click a row for the full requirements; star, check or hide roles as you go.</p>
<div class="tabsrow">
  <div class="seg tabs" role="group" aria-label="List">
    <button type="button" data-tab="inbox" aria-pressed="true">Inbox<span class="badge mono" data-badge="inbox"></span></button>
    <button type="button" data-tab="saved" aria-pressed="false">Saved<span class="badge mono" data-badge="saved"></span></button>
    <button type="button" data-tab="applied" aria-pressed="false">Applied<span class="badge mono" data-badge="applied"></span></button>
    <button type="button" data-tab="hidden" aria-pressed="false">Disliked<span class="badge mono" data-badge="hidden"></span></button>
    <button type="button" data-tab="all" aria-pressed="false">All<span class="badge mono" data-badge="all"></span></button>
  </div>
  <span class="state-sum mono" id="state-sum"></span>
  <button type="button" class="ctl small" id="data-toggle" aria-expanded="false" aria-controls="datapanel">Data</button>
  <span class="sync-status mono" id="sync-status"></span>
</div>
<div id="datapanel">
  <div class="dp-row">
    <button type="button" class="pbtn" id="export-btn">Export jadar-state.json</button>
    <label class="pbtn" for="import-file">Import…</label><input type="file" id="import-file" accept="application/json,.json" style="display:none">
    <button type="button" class="pbtn" id="clear-hidden">Clear hidden</button>
    <span class="dp-note">Saved, applied and hidden roles live in this browser. Export to move them, or sync below.</span>
  </div>
  <div class="dp-head mono">Sync with GitHub</div>
  <div class="dp-row">
    <input type="text" id="sync-repo" placeholder="owner/name" value="TheBurntWaffl3/jadar-state" aria-label="Repository">
    <input type="text" id="sync-path" placeholder="state.json" value="state.json" aria-label="File path">
    <input type="password" id="sync-token" class="wide" placeholder="fine-grained token" aria-label="Token" autocomplete="off">
    <button type="button" class="pbtn" id="sync-connect">Connect</button>
    <button type="button" class="pbtn" id="sync-disconnect">Disconnect</button>
    <button type="button" class="pbtn" id="sync-now">Sync now</button>
  </div>
  <div class="dp-note">The token stays in this browser only; scope it to that one private repo, Contents read/write. Nothing is sent anywhere but api.github.com.</div>
</div>
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

  // ---------- per-role state (saved / applied / hidden), kept in this browser ----------
  const KEY = 'jadar.state.v1', SKEY = 'jadar.sync.v1';
  const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } };
  const lsDel = k => { try { localStorage.removeItem(k); } catch (e) {} };
  function loadState() { try { const s = JSON.parse(lsGet(KEY) || 'null'); if (s && s.v === 1 && s.roles) return s; } catch (e) {} return {v: 1, roles: {}}; }
  let S = loadState();
  function persist() { lsSet(KEY, JSON.stringify(S)); schedulePush(); }
  const entry = url => S.roles[url];
  const statusOf = url => (S.roles[url] || {}).status || null;
  function snapOf(r) { const s = {company: r.company, title: r.title, location: r.location || '', url: r.url, fit: r.fit}; if (r.applyBy) s.applyBy = r.applyBy; return s; }
  function setStatus(r, status) {
    const url = r.url, cur = S.roles[url];
    if (!status) { if (cur && cur.note) { cur.status = null; cur.at = new Date().toISOString(); } else delete S.roles[url]; }
    else S.roles[url] = Object.assign({}, cur || {}, {status, at: new Date().toISOString(), snap: (cur && cur.snap && cur.snap.title) ? cur.snap : snapOf(r)});
    persist();
  }
  function setNote(r, note) {
    const url = r.url, cur = S.roles[url] || {status: null, snap: snapOf(r)};
    cur.note = note || ''; cur.at = new Date().toISOString(); if (!cur.snap) cur.snap = snapOf(r);
    if (!cur.note && !cur.status) delete S.roles[url]; else S.roles[url] = cur;
    persist();
  }
  function act(r, a) {
    const cur = statusOf(r.url);
    if (a === 'save') setStatus(r, cur === 'saved' ? null : 'saved');
    else if (a === 'applied') setStatus(r, cur === 'applied' ? null : 'applied');
    else if (a === 'hide') setStatus(r, cur === 'hidden' ? null : 'hidden');
  }
  function mergeStates(a, b) {  // per-url newer `at` wins; returns a fresh state
    const out = {v: 1, roles: {}}; const urls = new Set([...Object.keys(a.roles || {}), ...Object.keys(b.roles || {})]);
    urls.forEach(u => { const x = (a.roles || {})[u], y = (b.roles || {})[u]; out.roles[u] = !x ? y : !y ? x : ((y.at || '') > (x.at || '') ? y : x); });
    return out;
  }
  const counts = () => { const c = {saved: 0, applied: 0, hidden: 0}; Object.values(S.roles).forEach(e => { if (e.status) c[e.status] = (c[e.status] || 0) + 1; }); return c; };

  // hero + stats
  const sc = D.scanned ? new Date(D.scanned) : null;
  const okN = D.orgs.filter(o => o.status === 'OK').length, failN = D.orgs.filter(o => o.status === 'Failing').length, gapN = D.orgs.filter(o => o.status === 'Not covered yet').length;
  const stamp = sc ? sc.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'}) + ' ' + sc.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'}) : D.today;
  $('#meta').innerHTML = ['Scanned ' + esc(stamp), 'rules ' + esc(D.rulesVersion || '—'), D.fullRead ? 'full re-read' : 'incremental', okN + '/' + (okN + failN) + ' boards'].join('<span class="sep">·</span>');
  if (D.profileName) $('#who').textContent = 'For ' + D.profileName;
  function renderStats() {
    const inbox = roles.filter(r => { const s = statusOf(r.url); return s !== 'hidden' && s !== 'applied'; });
    const fits = inbox.filter(r => r.fit !== 'No');
    const week = fits.filter(r => r.dateKind === 'posted' && r.date && daysTo(r.date) >= -7).length;
    const closing = fits.filter(r => r._dt != null && r._dt >= 0 && r._dt <= 14).length;
    const applied = counts().applied;
    const stats = [
      ['Yes', inbox.filter(r => r.fit === 'Yes').length, 'strong fits', 'good'],
      ['Maybe', inbox.filter(r => r.fit === 'Maybe').length, 'worth a look', 'ember'],
      ['Posted 7d', week, 'Yes + Maybe', ''],
      ['Closing 14d', closing, 'apply-by known', closing ? 'ember' : ''],
      ['Roles', roles.length, 'in-field, US', ''],
      ['Boards OK', okN + ' / ' + (okN + failN), failN ? failN + ' failing' : 'none failing', ''],
    ];
    if (applied) stats.push(['Applied', applied, 'tracked here', '']);
    $('#stats').classList.toggle('n7', stats.length === 7);
    $('#stats').innerHTML = stats.map(([l, v, s, c]) => `<div class="stat"><div class="label mono">${esc(l)}</div><div class="value ${c}">${esc(v)}</div><div class="sub">${esc(s)}</div></div>`).join('');
  }

  // controls
  const state = {tab: 'inbox', fit: 'fits', sector: '', disc: '', days: '', q: '', sort: 'fit', dir: 'asc', open: null};
  const fill = (sel, vals) => { vals.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }); };
  fill($('#sector'), [...new Set(roles.map(r => r.sector).filter(Boolean))].sort());
  fill($('#disc'), [...new Set(roles.map(r => r.discipline).filter(Boolean))].sort());
  document.querySelectorAll('.seg:not(.tabs) button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.seg:not(.tabs) button').forEach(x => x.setAttribute('aria-pressed', x === b)); state.fit = b.dataset.fit; render();
  }));
  document.querySelectorAll('.tabs button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.tabs button').forEach(x => x.setAttribute('aria-pressed', x === b)); state.tab = b.dataset.tab; state.open = null; render();
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
  const byUrl = new Map(roles.map(r => [r.url, r]));
  function snapRole(e) {  // a saved/applied/hidden posting that the scan no longer lists
    const s = e.snap || {}; return Object.assign({}, s, {id: 'snap:' + s.url, _closed: true, _dt: daysTo(s.applyBy), why: '', _q: ''});
  }
  function tagsFor(r) {
    const t = []; const st = statusOf(r.url);
    if (r._closed) t.push('<span class="tag closed">closed</span>');
    if (r._new) t.push('<span class="tag new">New</span>');
    if (st && state.tab !== st && state.tab !== 'saved' && state.tab !== 'applied' && state.tab !== 'hidden') t.push(`<span class="tag status ${st}">${st === 'hidden' ? 'Hidden' : st === 'applied' ? 'Applied' : 'Saved'}</span>`);
    if (r._dt != null && r._dt >= 0 && r._dt <= 10) t.push(`<span class="tag closing">${r._dt === 0 ? 'Closes today' : 'Closes in ' + r._dt + 'd'}</span>`);
    if (r.workMode) t.push(`<span class="tag">${esc(r.workMode)}</span>`);
    if (r.employment && r.employment !== 'Full-time') t.push(`<span class="tag">${esc(r.employment)}</span>`);
    return t.length ? `<div class="tags">${t.join('')}</div>` : '';
  }
  function icons(r) {
    const st = statusOf(r.url);
    return `<button type="button" class="ic save${st === 'saved' ? ' on' : ''}" data-act="save" aria-label="${st === 'saved' ? 'Unsave' : 'Save'}" title="${st === 'saved' ? 'Unsave' : 'Save'}" aria-pressed="${st === 'saved'}">${st === 'saved' ? '★' : '☆'}</button>` +
      `<button type="button" class="ic applied${st === 'applied' ? ' on' : ''}" data-act="applied" aria-label="${st === 'applied' ? 'Mark not applied' : 'Mark applied'}" title="${st === 'applied' ? 'Mark not applied' : 'Mark applied'}" aria-pressed="${st === 'applied'}">✓</button>` +
      `<button type="button" class="ic hide${st === 'hidden' ? ' on' : ''}" data-act="hide" aria-label="${st === 'hidden' ? 'Unhide' : 'Hide (not for me)'}" title="${st === 'hidden' ? 'Unhide' : 'Hide (not for me)'}" aria-pressed="${st === 'hidden'}">✕</button>`;
  }
  function kv(k, v) { return v == null || v === '' ? '' : `<div><div class="k mono">${esc(k)}</div><div class="v">${esc(v)}</div></div>`; }
  function actRow(r) {
    const e = entry(r.url) || {}; const st = e.status;
    const at = e.at ? fmtLong(e.at.slice(0, 10)) : '';
    return `<div class="actrow">` +
      `<button type="button" class="pbtn${st === 'saved' ? ' on' : ''}" data-act="save">${st === 'saved' ? '★ Saved' : '☆ Save'}</button>` +
      `<button type="button" class="pbtn${st === 'applied' ? ' on' : ''}" data-act="applied">${st === 'applied' ? '✓ Applied' : 'Mark applied'}</button>` +
      `<button type="button" class="pbtn${st === 'hidden' ? ' on' : ''}" data-act="hide">${st === 'hidden' ? 'Hidden · unhide' : 'Not for me'}</button>` +
      (st === 'applied' && at ? `<span class="applied-at">Applied ${esc(at)}</span>` : '') +
      `<input type="text" class="note-in" data-note="1" placeholder="Note (contact, referral, follow-up…)" value="${esc(e.note || '')}" aria-label="Note"></div>`;
  }
  function companyKey(c) { return (c || '').replace(/\s*\(.*?\)\s*/g, ' ').split(' / ')[0].replace(/\s+/g, ' ').trim(); }
  function division(title) {
    const t = title || '';
    let m = t.match(/\(([^)]{3,30})\)\s*$/) || t.match(/[,\u2013\u2014-]\s*([A-Za-z][A-Za-z &/]{2,30})\s*$/);
    if (!m) return null;
    const d = m[1].trim();
    if (/^(i{1,3}|iv|v|\d|entry|junior|senior|sr|staff|lead|associate|new grad|early career|remote|hybrid|onsite|on-site|contract|usa|us)\b/i.test(d)) return null;
    return d;
  }
  function people(r) {
    const co = companyKey(r.company); if (!co) return '';
    const alum = k => `https://www.linkedin.com/school/university-of-maryland/people/?keywords=${encodeURIComponent(k)}`;
    const div = division(r.title);
    return `<div class="people"><span class="k mono">Terps here</span>` +
      `<a class="btn alt" href="${alum(co)}" target="_blank" rel="noopener">UMD alumni at ${esc(co)} ↗</a>` +
      (div ? `<a class="btn alt" href="${alum(co + ' ' + div)}" target="_blank" rel="noopener">…in ${esc(div)} ↗</a>` : '') +
      `<a class="btn alt" href="https://terrapinsconnect.umd.edu/" target="_blank" rel="noopener">Terrapins Connect ↗</a></div>`;
  }
  function detail(r) {
    const yrs = r.minYears == null ? 'not stated' : r.minYears + (r.schoolExpOk ? ' (school/internship counts)' : '');
    const pay = r.salary ? r.salary + (/\/hr$/.test(r.salary) && r.salaryMin != null ? ' · $' + num(r.salaryMin) + (r.salaryMax != null && r.salaryMax !== r.salaryMin ? '–$' + num(r.salaryMax) : '') + ' annualized' : '') : null;
    const left = [kv('Min experience', yrs), kv('Degree', r.degree), kv('Major', r.majorReq), kv('GPA', r.gpaReq), kv('Clearance', r.clearance), kv('Citizenship', r.citizenship),
      kv('Grad window', r.gradReq), kv('Start', r.startReq), kv('Start window', r.startWindow), kv('Apply by', r.applyBy ? fmtLong(r.applyBy) + (r._dt != null ? ' (' + (r._dt < 0 ? 'passed' : r._dt + ' days') + ')' : '') : null),
      kv('Pay', pay), kv('Work mode', r.workMode), kv('Employment', r.employment), kv('Travel', r.travel), kv('Relocation', r.relocation === true ? 'offered' : r.relocation === false ? 'not offered' : null),
      kv('Posted', r.date ? fmtLong(r.date) + ' (' + r.dateKind + ')' : null), kv('First seen', r.firstSeen ? fmtLong(r.firstSeen) : null), kv('Sector', r.sector)].join('');
    const snip = r.reqSnippet ? `<div class="snip"><div class="k mono">Minimum qualifications</div>${esc(r.reqSnippet)}</div>` : `<div class="snip"><div class="k mono">Why</div>${esc(r.why)}</div>`;
    return `<div class="panel"><div class="kv">${left}</div><div>${snip}<a class="btn" href="${esc(r.url)}" target="_blank" rel="noopener">Open posting ↗</a>${people(r)}</div></div>${actRow(r)}`;
  }
  function listFor(tab) {  // the universe of rows for a tab, before filters
    if (tab === 'inbox') return roles.filter(r => { const s = statusOf(r.url); return s !== 'hidden' && s !== 'applied'; });
    if (tab === 'all') return roles.slice();
    const st = tab;  // saved / applied / hidden: stored entries, newest action first, closed postings as snapshots
    return Object.values(S.roles).filter(e => e.status === st).sort((a, b) => (b.at || '').localeCompare(a.at || ''))
      .map(e => byUrl.get(e.snap && e.snap.url) || snapRole(e));
  }
  function render() {
    renderStats();
    const c = counts(); const inboxN = roles.filter(r => { const s = statusOf(r.url); return s !== 'hidden' && s !== 'applied'; }).length;
    const badges = {inbox: inboxN, saved: c.saved, applied: c.applied, hidden: c.hidden, all: roles.length};
    document.querySelectorAll('.tabs [data-badge]').forEach(b => b.textContent = badges[b.dataset.badge] ? ' ' + badges[b.dataset.badge] : '');
    $('#state-sum').textContent = (c.saved || c.applied || c.hidden) ? `${c.saved} saved · ${c.applied} applied · ${c.hidden} hidden` : '';
    const base = listFor(state.tab); const listTab = ['saved', 'applied', 'hidden'].includes(state.tab);
    let list = listTab ? base : base.filter(r => state.fit === 'all' || (state.fit === 'fits' ? r.fit !== 'No' : r.fit === state.fit));
    if (state.sector) list = list.filter(r => r.sector === state.sector);
    if (state.disc) list = list.filter(r => r.discipline === state.disc);
    if (state.days) list = list.filter(r => r.dateKind === 'posted' && r.date && daysTo(r.date) >= -Number(state.days));
    if (state.q) { const words = state.q.split(/\s+/).filter(Boolean);  // every word must appear somewhere in the row
      list = list.filter(r => { const h = r._q || [r.company, r.title, r.location].join(' ').toLowerCase(); return words.every(w => h.includes(w)); }); }
    if (!listTab) list = sorted(list);
    document.querySelectorAll('th.sortable').forEach(th => (!listTab && th.dataset.sort === state.sort) ? th.setAttribute('aria-sort', state.dir === 'asc' ? 'ascending' : 'descending') : th.removeAttribute('aria-sort'));
    $('#count').textContent = list.length + ' of ' + base.length + ' roles';
    if (!list.length) {
      const msg = {saved: 'Nothing saved yet. Star a role to keep it here.', applied: 'Nothing marked applied yet.', hidden: 'Nothing hidden. The ✕ on a role sends it here.'}[state.tab] || 'Nothing matches these filters.';
      $('#rows').innerHTML = `<tr><td colspan="9" class="empty">${msg}</td></tr>`; return;
    }
    $('#rows').innerHTML = list.map(r => {
      const open = !r._closed && state.open === r.id; const st = statusOf(r.url);
      const dim = state.tab === 'all' && (st === 'hidden');
      return `<tr class="row${dim ? ' dim' : ''}" data-id="${esc(r.id)}" data-url="${esc(r.url)}" tabindex="0" aria-expanded="${open}">
<td class="fitco"><span class="fit ${esc(r.fit)}">${esc(r.fit)}</span><span class="co sm-co">${esc(r.company)}</span></td>
<td class="co">${esc(r.company)}</td>
<td class="role"><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>${r.location ? `<div class="loc">${esc(r.location)}</div>` : ''}${tagsFor(r)}</td>
<td class="kvl">${esc(r.discipline || '')}</td>
<td class="kvl num">${r.salary ? esc(r.salary) : '<span style="color:var(--muted)">—</span>'}</td>
<td class="kvl date">${r._closed ? (r.applyBy ? 'by ' + esc(fmt(r.applyBy)) : '') : esc(fmt(r.date))}<span class="kind mono">${esc(r._closed ? '' : (r.dateKind || ''))}</span></td>
<td class="why">${esc(r.why || '')}</td>
<td class="acts">${icons(r)}</td>
<td class="chev" aria-hidden="true"${r._closed ? ' style="visibility:hidden"' : ''}></td></tr>` + (open ? `<tr class="detail"><td colspan="9">${detail(r)}</td></tr>` : '');
    }).join('');
  }
  function roleFromEl(el) { const tr = el.closest('tr'); if (!tr) return null; const url = tr.dataset.url || (tr.previousElementSibling && tr.previousElementSibling.dataset.url); return byUrl.get(url) || (entry(url) ? snapRole(entry(url)) : null); }
  $('#rows').addEventListener('click', e => {
    const b = e.target.closest('button[data-act]');
    if (b) { e.stopPropagation(); const r = roleFromEl(b); if (r) { act(r, b.dataset.act); render(); } return; }
    if (e.target.closest('a') || e.target.closest('input') || e.target.closest('tr.detail')) return;
    const tr = e.target.closest('tr.row'); if (!tr || tr.querySelector('.chev[style]')) return;
    state.open = state.open === tr.dataset.id ? null : tr.dataset.id; render();
    if (state.open) { const el = $(`tr.row[data-id="${state.open}"]`); if (el) el.focus({preventScroll: true}); }
  });
  $('#rows').addEventListener('keydown', e => {
    if (e.target.matches('input[data-note]')) { if (e.key === 'Enter') { e.preventDefault(); e.target.blur(); } return; }
    if ((e.key === 'Enter' || e.key === ' ') && e.target.classList.contains('row')) { e.preventDefault(); e.target.click(); }
  });
  $('#rows').addEventListener('change', e => {
    if (e.target.matches('input[data-note]')) { const r = roleFromEl(e.target); if (r) { setNote(r, e.target.value.trim()); } }
  });

  // data panel: export / import / clear
  $('#data-toggle').addEventListener('click', e => { const o = $('#datapanel').classList.toggle('open'); e.target.setAttribute('aria-expanded', o); });
  $('#export-btn').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(S, null, 1)], {type: 'application/json'}); const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'jadar-state.json'; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  });
  $('#import-file').addEventListener('change', e => {
    const f = e.target.files && e.target.files[0]; if (!f) return;
    const rd = new FileReader();
    rd.onload = () => { try { const s = JSON.parse(rd.result); if (!s || !s.roles) throw new Error('not a jadar state file'); S = mergeStates(S, s); persist(); render(); setSync('imported'); } catch (err) { alert('Import failed: ' + err.message); } e.target.value = ''; };
    rd.readAsText(f);
  });
  $('#clear-hidden').addEventListener('click', () => {
    const n = counts().hidden; if (!n) return;
    if (confirm(`Un-hide ${n} role${n === 1 ? '' : 's'}?`)) { Object.keys(S.roles).forEach(u => { if (S.roles[u].status === 'hidden') { if (S.roles[u].note) { S.roles[u].status = null; S.roles[u].at = new Date().toISOString(); } else delete S.roles[u]; } }); persist(); render(); }
  });

  // optional sync through a private GitHub repo (token stays in this browser; only api.github.com is contacted)
  const b64enc = s => { const u = new TextEncoder().encode(s); let bin = ''; for (let i = 0; i < u.length; i += 0x8000) bin += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(bin); };
  const b64dec = b => new TextDecoder().decode(Uint8Array.from(atob(b.replace(/\s/g, '')), ch => ch.charCodeAt(0)));
  function syncCfg() { try { const c = JSON.parse(lsGet(SKEY) || 'null'); return c && c.repo && c.token ? c : null; } catch (e) { return null; } }
  function setSync(msg) { $('#sync-status').textContent = msg || ''; }
  function reflectSync() { const c = syncCfg(); $('#sync-connect').style.display = c ? 'none' : ''; $('#sync-disconnect').style.display = c ? '' : 'none'; $('#sync-now').style.display = c ? '' : 'none'; if (c) { $('#sync-repo').value = c.repo; $('#sync-path').value = c.path || 'state.json'; } }
  const ghUrl = c => 'https://api.github.com/repos/' + c.repo + '/contents/' + (c.path || 'state.json');
  const ghHeaders = c => ({'Authorization': 'Bearer ' + c.token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'});
  async function ghGet(c) {
    const r = await fetch(ghUrl(c), {headers: ghHeaders(c), cache: 'no-store'});
    if (r.status === 404) return {state: null, sha: null};
    if (!r.ok) throw new Error(String(r.status));
    const j = await r.json(); let st = null; try { st = JSON.parse(b64dec(j.content || '')); } catch (e) { st = null; }
    return {state: st && st.roles ? st : null, sha: j.sha};
  }
  async function ghPut(c, st, sha) {
    const body = {message: 'jadar state', content: b64enc(JSON.stringify(st, null, 1))}; if (sha) body.sha = sha;
    const r = await fetch(ghUrl(c), {method: 'PUT', headers: Object.assign({'Content-Type': 'application/json'}, ghHeaders(c)), body: JSON.stringify(body)});
    if (!r.ok) throw new Error(String(r.status));
  }
  let syncing = false, pending = false, pushTimer = null;
  async function syncNow() {
    const c = syncCfg(); if (!c) return;
    if (syncing) { pending = true; return; }
    syncing = true;
    try {
      if (navigator.onLine === false) { setSync('offline'); return; }
      setSync('syncing…');
      const {state: remote, sha} = await ghGet(c);
      const before = JSON.stringify(S);
      const merged = remote ? mergeStates(S, remote) : S;
      if (JSON.stringify(merged) !== before) { S = merged; lsSet(KEY, JSON.stringify(S)); render(); }
      if (!remote || JSON.stringify(merged) !== JSON.stringify(remote)) await ghPut(c, merged, sha);
      const now = new Date(); setSync('synced ' + now.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'}).toLowerCase());
    } catch (err) { setSync('sync failed: ' + (err.message || 'error')); }
    finally { syncing = false; if (pending) { pending = false; syncNow(); } }
  }
  function schedulePush() { if (!syncCfg()) return; clearTimeout(pushTimer); pushTimer = setTimeout(syncNow, 2000); }
  $('#sync-connect').addEventListener('click', () => {
    const repo = $('#sync-repo').value.trim(), path = $('#sync-path').value.trim() || 'state.json', token = $('#sync-token').value.trim();
    if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) { alert('Repository must look like owner/name'); return; }
    if (!token) { alert('Paste a fine-grained token for that repo (Contents: read and write)'); return; }
    if (!lsSet(SKEY, JSON.stringify({repo, path, token}))) { alert('This browser blocks storage; sync cannot be kept.'); return; }
    $('#sync-token').value = ''; reflectSync(); syncNow();
  });
  $('#sync-disconnect').addEventListener('click', () => { lsDel(SKEY); reflectSync(); setSync(''); });
  $('#sync-now').addEventListener('click', syncNow);
  window.addEventListener('online', () => { if (syncCfg()) syncNow(); });
  reflectSync();

  // boards
  $('#boards-sum').textContent = `${okN} of ${okN + failN} boards read · ${failN} failing · ${gapN} not covered`;
  $('#boards-toggle').addEventListener('click', e => { const o = $('#boards').classList.toggle('open'); e.target.setAttribute('aria-expanded', o); e.target.textContent = o ? 'Hide boards' : 'Show boards'; });
  const rank = {Failing: 0, OK: 1, 'Not covered yet': 2};
  $('#org-rows').innerHTML = D.orgs.slice().sort((a, b) => rank[a.status] - rank[b.status] || a.org.localeCompare(b.org)).map(o => {
    const cls = o.status === 'OK' ? 'ok' : o.status === 'Failing' ? 'failing' : 'gap';
    return `<tr class="${cls === 'failing' ? 'fail' : cls === 'gap' ? 'gap' : ''}"><td>${esc(o.org)}</td><td class="hide-sm">${esc(o.sector)}</td><td>${esc(o.platform)}</td><td><span class="st ${cls}">${esc(o.status)}</span></td><td class="num">${o.roles == null ? '–' : o.roles}</td><td class="num">${o.fits == null ? '–' : o.fits}</td><td class="note">${esc(o.note || '')}</td></tr>`;
  }).join('');
  render();
  if (syncCfg()) syncNow();
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
