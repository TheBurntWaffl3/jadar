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
.topnav { display: inline-flex; align-items: center; gap: 4px; margin: 0 0 22px; padding: 4px; border-radius: 999px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14); font-size: 13px; letter-spacing: .01em; }
.topnav .sep { display: none; }
.topnav a { color: var(--on-hero); text-decoration: none; opacity: .72; padding: 7px 16px; border-radius: 999px; font-weight: 600; transition: background .12s, opacity .12s; }
.topnav a:hover { opacity: 1; background: rgba(255,255,255,.10); }
.topnav a[aria-current] { opacity: 1; background: var(--ember); color: #fff; }
.topnav a:focus-visible { outline: 2px solid var(--ember); outline-offset: 2px; }
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
#loc, #company { max-width: 280px; text-overflow: ellipsis; }
.ctl.more-toggle[aria-expanded="true"] { background: var(--ink); color: var(--page); }
.controls.more { display: none; padding: 10px 12px; background: var(--card); border: 1px solid var(--line); border-radius: 16px; }
.controls.more.open { display: flex; }
.chk { display: inline-flex; align-items: center; gap: 6px; font-size: 13.5px; color: var(--ink); padding: 6px 4px; cursor: pointer; }
.chk input { accent-color: var(--ink); width: 15px; height: 15px; margin: 0; }
.chk.off { opacity: .45; cursor: not-allowed; }
.linkbtn { background: none; border: 0; padding: 6px 4px; font: inherit; font-size: 13px; color: var(--ember); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
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
.tag.t2027 { background: transparent; color: var(--good); box-shadow: inset 0 0 0 1.5px var(--good); }
.tag.twindow, .tag.tasap { background: var(--pill); color: var(--muted); }
.ctl.pillbtn[aria-pressed="true"] { background: var(--good); color: #fff; }
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
.found { margin-top: 12px; font-size: 13.5px; }
.found .k { margin-bottom: 6px; }
.found ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.found li a { color: var(--ink); font-weight: 600; text-decoration: none; } .found li a:hover { text-decoration: underline; }
.found li .hl { color: var(--muted); font-size: 13px; }
.found .quiet { color: var(--muted); }
.found .fhead { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 8px; }
.found .fhead .k { margin: 0; }
.tseg { display: inline-flex; gap: 2px; background: var(--pill); border-radius: 999px; padding: 2px; }
.pbtn.sm { padding: 3px 10px; font-size: 12px; min-height: 0; border-color: transparent; background: transparent; }
.tseg .pbtn.sm.on { background: var(--ink); color: var(--page); }
.found li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 8px; }
.found li .why-t { font-size: 10.5px; color: var(--ember); background: var(--tint); border-radius: 999px; padding: 1px 7px; letter-spacing: .06em; text-transform: uppercase; font-family: ui-monospace, Menlo, Consolas, monospace; }
.found li .draft-b { margin-left: auto; }
.draft { flex-basis: 100%; display: grid; gap: 8px; margin: 4px 0 6px; }
.draft textarea { width: 100%; min-height: 128px; font: inherit; font-size: 13.5px; line-height: 1.45; border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; background: var(--page); color: var(--ink); resize: vertical; }
.draft .brow { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.draft .brow .quiet { font-size: 12.5px; }
.tag.terps { background: var(--tint); color: var(--ember); }
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
.tag.closed { background: var(--pill); color: var(--muted); } .tag.status.repost { opacity: .85; } .tag.status { background: var(--tint); color: var(--ember); } .tag.status.applied { background: rgba(12,163,12,.12); color: var(--good); }
tr.row.dim td .role a, tr.row.dim td.co, tr.row.dim td.why { color: var(--muted); }
.tag.tasap-hidden { background: var(--pill); color: var(--muted); }
.imm-note { color: var(--muted); margin: -4px 0 10px; } .imm-note a { color: var(--ember); text-decoration: none; }
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
  <nav class="topnav mono" aria-label="Pages"><a href="index.html" aria-current="page">Radar</a><span class="sep">·</span><a href="tracker.html" title="Your applications">Tracker</a></nav>
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
  <button type="button" class="ctl pillbtn" id="only2027" aria-pressed="false" title="Only roles that name 2027 in their grad or start window">2027 only</button>
  <select class="ctl" id="sector" aria-label="Sector"><option value="">All sectors</option></select>
  <select class="ctl" id="disc" aria-label="Field"><option value="">All fields</option></select>
  <select class="ctl" id="days" aria-label="Posted within">
    <option value="">Any date</option><option value="7">Posted in 7 days</option><option value="30">Posted in 30 days</option>
  </select>
  <select class="ctl" id="loc" aria-label="Location"><option value="">All locations</option></select>
  <select class="ctl" id="sort" aria-label="Sort by">
    <option value="fit2027">Sort: Fit · 2027 first</option><option value="fit">Sort: Fit</option><option value="date">Sort: Newest</option><option value="applyBy">Sort: Apply-by soonest</option>
    <option value="salary">Sort: Salary high→low</option><option value="company">Sort: Company</option><option value="minYears">Sort: Min yrs</option>
  </select>
  <input class="ctl" type="search" id="q" placeholder="Search company, title, location, why" aria-label="Search">
  <button type="button" class="ctl more-toggle" id="more-toggle" aria-expanded="false" aria-controls="more">More filters</button>
  <button type="button" class="linkbtn" id="clear-filters" hidden>Clear filters</button>
  <span class="count mono" id="count"></span>
</div>
<div class="imm-note mono" id="imm-note" hidden></div>
<div class="controls more" id="more">
  <select class="ctl" id="mode" aria-label="Work mode"><option value="">Any work mode</option><option value="Remote">Remote</option><option value="Hybrid">Hybrid</option><option value="On-site">On-site</option></select>
  <select class="ctl" id="pay" aria-label="Pay at least"><option value="">Any pay</option><option value="60000">Pay ≥ $60k</option><option value="70000">Pay ≥ $70k</option><option value="80000">Pay ≥ $80k</option><option value="90000">Pay ≥ $90k</option><option value="100000">Pay ≥ $100k</option><option value="120000">Pay ≥ $120k</option></select>
  <label class="chk"><input type="checkbox" id="payonly"> only roles that state pay</label>
  <select class="ctl" id="exp" aria-label="Experience"><option value="">Any experience</option><option value="0">0 years</option><option value="1">Up to 1 year</option><option value="ns">Not stated</option></select>
  <select class="ctl" id="clr" aria-label="Clearance"><option value="">Any clearance</option><option value="none">None mentioned</option><option value="obtain">Obtainable</option></select>
  <select class="ctl" id="cit" aria-label="Citizenship"><option value="">Any citizenship</option><option value="none">No requirement stated</option><option value="citizen">US citizen required</option><option value="itar">US person (ITAR)</option></select>
  <select class="ctl" id="company" aria-label="Company"><option value="">All companies</option></select>
  <select class="ctl" id="closing" aria-label="Closing"><option value="">Any closing date</option><option value="7">Closes within 7 days</option><option value="14">Closes within 14 days</option><option value="30">Closes within 30 days</option><option value="any">Has a deadline</option></select>
  <label class="chk" id="terps-chk"><input type="checkbox" id="terps"> has Terps found</label>
  <select class="ctl" id="timing" aria-label="Timing"><option value="">Any timing</option><option value="2027">Says 2027</option><option value="window">States a window</option><option value="unstated">Not stated</option><option value="immediate">Immediate start</option></select>
  <label class="chk"><input type="checkbox" id="newonly"> new today</label>
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
__SHARED_JS__
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const NEW = new Set(D.new || []);
  const J = window.JADAR;
  const today = new Date(D.today + 'T00:00:00');
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = J.esc, MON = J.MON, companyKey = J.companyKey;
  const fmt = iso => J.fmt(iso, today), fmtLong = J.fmtLong, daysTo = iso => J.daysTo(iso, today);
  const num = n => n == null ? '' : n.toLocaleString('en-US');
  const FITRANK = {Yes: 0, Maybe: 1, No: 2};
  // ---------- location parsing: two-letter state + remote flag from the free-text location ----------
  const STATE_NAMES = {'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO','connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID','illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV','new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY','north carolina':'NC','north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA','rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA','west virginia':'WV','wisconsin':'WI','wyoming':'WY','district of columbia':'DC'};
  const STATE_CODES = new Set(Object.values(STATE_NAMES));
  const CITY_STATE = {'hawthorne':'CA','starbase':'TX','boca chica':'TX','huntsville':'AL','laurel':'MD','chantilly':'VA','wallops island':'VA','schenectady':'NY','niskayuna':'NY','kent':'WA','long beach':'CA','el segundo':'CA','pasadena':'CA','littleton':'CO','denver':'CO','tucson':'AZ','orlando':'FL','cape canaveral':'FL','everett':'WA','seattle':'WA','marina':'CA','costa mesa':'CA','irvine':'CA','austin':'TX','houston':'TX','boston':'MA','cambridge':'MA','bedford':'MA','lexington':'MA','groton':'CT','new london':'CT','newport news':'VA','ingalls':'MS','pascagoula':'MS','bath':'ME','lynchburg':'VA','pittsburgh':'PA','cranberry township':'PA','idaho falls':'ID','los alamos':'NM','albuquerque':'NM','livermore':'CA','oak ridge':'TN','palmdale':'CA','fort worth':'TX','stennis':'MS','mojave':'CA','berkeley':'CA','redmond':'WA','columbia':'MD','silver spring':'MD','greenbelt':'MD','elkton':'MD','orange':'VA','camden':'AR','canoga park':'CA','goleta':'CA','marlborough':'MA','sterling':'VA','mclean':'VA','reston':'VA','dulles':'VA','arlington':'VA','washington':'DC','los angeles':'CA','san francisco':'CA','san diego':'CA','sunnyvale':'CA','mountain view':'CA','university park':'PA','state college':'PA','colorado springs':'CO','melbourne':'FL','titusville':'FL','st. louis':'MO','st louis':'MO','ridley park':'PA','ocean springs':'MS','new orleans':'LA','portland':'OR','phoenix':'AZ','mesa':'AZ','salt lake city':'UT','ogden':'UT','cedar rapids':'IA','dayton':'OH','cincinnati':'OH','evendale':'OH','lynn':'MA','andover':'MA','wilmington':'MA','tewksbury':'MA','nashua':'NH','manchester':'NH','burlington':'VT','hartford':'CT','east hartford':'CT','windsor locks':'CT','syracuse':'NY','rochester':'NY','binghamton':'NY','owego':'NY','moorestown':'NJ','mount laurel':'NJ','baltimore':'MD','annapolis':'MD','bethesda':'MD','rockville':'MD','linthicum':'MD','hanover':'MD','lexington park':'MD','charlottesville':'VA','norfolk':'VA','virginia beach':'VA','dahlgren':'VA','fairfax':'VA','manassas':'VA','herndon':'VA','roanoke':'VA','richmond':'VA'};
  const STATE_NAME_RX = new RegExp('\\b(' + Object.keys(STATE_NAMES).sort((a, b) => b.length - a.length).map(n => n.replace(/ /g, '\\s+')).join('|') + ')\\b', 'i');
  const CITY_RX = new RegExp('\\b(' + Object.keys(CITY_STATE).sort((a, b) => b.length - a.length).map(n => n.replace(/ /g, '\\s+')).join('|') + ')\\b', 'i');
  function parseLoc(loc) {
    const s = String(loc || ''); const remote = /\bremote\b/i.test(s) && !/\b(not|no)\s+remote\b/i.test(s);
    if (/\bD\.?C\.?\b/.test(s) && /washington/i.test(s)) return {state: 'DC', remote};
    const codeRx = /(?:^|[\s,\-–\/(])([A-Z]{2})(?=$|[\s,)\-–\/.;])/g; let m;
    while ((m = codeRx.exec(s))) if (STATE_CODES.has(m[1])) return {state: m[1], remote};
    const n = STATE_NAME_RX.exec(s); if (n) return {state: STATE_NAMES[n[1].toLowerCase().replace(/\s+/g, ' ')], remote};
    const c = CITY_RX.exec(s); if (c) return {state: CITY_STATE[c[1].toLowerCase().replace(/\s+/g, ' ')], remote};
    return {state: null, remote};
  }
  const REGIONS = [['dmv', 'DMV (MD · DC · VA)', ['MD','DC','VA']], ['ne', 'Northeast (CT MA ME NH NJ NY PA RI VT)', ['CT','MA','ME','NH','NJ','NY','PA','RI','VT']],
    ['se', 'Southeast (AL FL GA MS NC SC TN KY)', ['AL','FL','GA','MS','NC','SC','TN','KY']], ['mw', 'Midwest (IL IN IA KS MI MN MO NE ND OH SD WI)', ['IL','IN','IA','KS','MI','MN','MO','NE','ND','OH','SD','WI']],
    ['tx', 'Texas & South (TX OK AR LA)', ['TX','OK','AR','LA']], ['mt', 'Mountain (AZ CO ID MT NM NV UT WY)', ['AZ','CO','ID','MT','NM','NV','UT','WY']],
    ['wc', 'West Coast (CA OR WA AK HI)', ['CA','OR','WA','AK','HI']]];
  const REGION_STATES = Object.fromEntries(REGIONS.map(([k, , st]) => [k, new Set(st)]));
  const locMatch = (r, v) => !v ? true : v === 'remote' ? r._remote : v === 'unknown' ? !r._state : REGION_STATES[v] ? REGION_STATES[v].has(r._state) : r._state === v;
  const TIMING_RANK = {'2027': 0, window: 1, unstated: 2, immediate: 3};
  const TIMING_LABEL = {'2027': 'Says 2027', window: 'States a window', unstated: 'Not stated', immediate: 'Immediate start'};
  const roles = D.roles.map(r => { const pl = parseLoc(r.location); return Object.assign({}, r, {_new: NEW.has(r.url), _dt: daysTo(r.applyBy), _state: pl.state, _remote: pl.remote, _timing: TIMING_RANK[r.timing] != null ? r.timing : 'unstated',
    _q: [r.company, r.title, r.location, r.why, r.discipline, r.salary].join(' ').toLowerCase()}); });

  // ---------- per-role state (saved / applied / hidden), kept in this browser ----------
  const KEY = J.KEY, SKEY = J.SKEY, lsGet = J.lsGet, lsSet = J.lsSet, lsDel = J.lsDel, loadState = J.loadState, mergeStates = J.mergeStates;
  let S = loadState();
  function persist() { FPM = null; J.saveState(S); schedulePush(); }
  const entry = url => S.roles[url];
  const statusOf = url => (S.roles[url] || {}).status || null;
  // fingerprint = company + normalized title: a re-posted job (new URL, same job) stays hidden / applied
  const norm = t => String(t || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
  const fpOf = r => companyKey(r.company) + '|' + norm(r.title);
  Object.values(S.roles).forEach(e => { if (!e.fp && e.snap && e.snap.title) e.fp = fpOf(e.snap); });  // migrate older entries
  let FPM = null;  // fp -> 'hidden' | 'applied', rebuilt on each render
  function fpMap() { const m = {}; Object.values(S.roles).forEach(e => { if ((e.status === 'hidden' || e.status === 'applied') && e.fp) m[e.fp] = m[e.fp] === 'applied' ? 'applied' : e.status; }); return m; }
  function effStatus(r) {  // own status, else the status of another posting with the same company + title
    const own = statusOf(r.url); if (own) return {status: own, repost: false};
    const via = (FPM || (FPM = fpMap()))[fpOf(r)]; return via ? {status: via, repost: true} : {status: null, repost: false};
  }
  const inInbox = r => { const e = effStatus(r); if (e.status === 'hidden' || e.status === 'applied') return false;
    return r._timing !== 'immediate' || state.timing === 'immediate'; };  // immediate-start roles wait until the Timing filter asks for them
  const immHidden = r => { const e = effStatus(r); return e.status !== 'hidden' && e.status !== 'applied' && r._timing === 'immediate'; };
  function snapOf(r) { const s = {company: r.company, title: r.title, location: r.location || '', url: r.url, fit: r.fit}; if (r.applyBy) s.applyBy = r.applyBy; if (r.salary) s.salary = r.salary; if (r.date) s.date = r.date; return s; }
  function setStatus(r, status) {
    const url = r.url, cur = S.roles[url]; const now = new Date().toISOString();
    if (!status) { if (cur && (cur.note || cur.app)) { cur.status = null; cur.at = now; } else delete S.roles[url]; }  // un-applying keeps the tracker data
    else {
      const e = Object.assign({}, cur || {}, {status, at: now, snap: (cur && cur.snap && cur.snap.title) ? cur.snap : snapOf(r), fp: fpOf(r)});
      if (status === 'applied') {  // the Tracker page picks this up: applied date and prefilled pay / posted
        e.app = Object.assign({}, e.app || {});
        if (!e.app.appliedOn) e.app.appliedOn = D.today; if (!e.app.status) e.app.status = 'applied';
        if (!e.app.pay && r.salary) e.app.pay = r.salary; if (!e.app.posted && r.date) e.app.posted = r.date; e.app.updatedAt = now;
      }
      S.roles[url] = e;
    }
    persist();
  }
  function setNote(r, note) {
    const url = r.url, cur = S.roles[url] || {status: null, snap: snapOf(r)};
    cur.note = note || ''; cur.at = new Date().toISOString(); if (!cur.snap) cur.snap = snapOf(r);
    if (!cur.note && !cur.status && !cur.app) delete S.roles[url]; else S.roles[url] = cur;
    persist();
  }
  function act(r, a) {
    const cur = statusOf(r.url);
    if (a === 'save') setStatus(r, cur === 'saved' ? null : 'saved');
    else if (a === 'applied') setStatus(r, cur === 'applied' ? null : 'applied');
    else if (a === 'hide') setStatus(r, cur === 'hidden' ? null : 'hidden');
  }
  const counts = () => { const c = {saved: 0, applied: 0, hidden: 0}; Object.values(S.roles).forEach(e => { if (e.status) c[e.status] = (c[e.status] || 0) + 1; }); return c; };

  // hero + stats
  const sc = D.scanned ? new Date(D.scanned) : null;
  const okN = D.orgs.filter(o => o.status === 'OK').length, failN = D.orgs.filter(o => o.status === 'Failing').length, gapN = D.orgs.filter(o => o.status === 'Not covered yet').length;
  const stamp = sc ? sc.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'}) + ' ' + sc.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'}) : D.today;
  $('#meta').innerHTML = ['Scanned ' + esc(stamp), 'rules ' + esc(D.rulesVersion || '—'), D.fullRead ? 'full re-read' : 'incremental', okN + '/' + (okN + failN) + ' boards'].join('<span class="sep">·</span>');
  if (D.profileName) $('#who').textContent = 'For ' + D.profileName;
  function renderStats() {
    const inbox = roles.filter(inInbox);
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
  const FILTER_DEFAULTS = {sector: '', disc: '', days: '', loc: '', q: '', mode: '', pay: '', payonly: false, exp: '', clr: '', cit: '', company: '', closing: '', timing: '', terps: false, newonly: false};
  const state = Object.assign({tab: 'inbox', fit: 'fits', sort: 'fit2027', dir: 'asc', more: false, open: null, draft: null}, FILTER_DEFAULTS);
  const FKEY = 'jadar.filters.v1';
  // Only the sort and the More-filters disclosure survive a reload; every filter (search, fit, location, timing, ...) starts
  // clear so a filter left on yesterday never hides roles today (Kevin, 2026-11-18).
  function saveFilters() { lsSet(FKEY, JSON.stringify({v: 2, sort: state.sort, dir: state.dir, more: state.more})); }
  function loadFilters() { try { const o = JSON.parse(lsGet(FKEY) || 'null'); if (!o || !(o.v === 1 || o.v === 2)) return;
    if (typeof o.sort === 'string' && KEYS[o.sort]) state.sort = o.sort; if (o.dir === 'asc' || o.dir === 'desc') state.dir = o.dir; state.more = !!o.more; } catch (e) {} }
  const fill = (sel, vals) => { vals.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }); };
  fill($('#sector'), [...new Set(roles.map(r => r.sector).filter(Boolean))].sort());
  fill($('#disc'), [...new Set(roles.map(r => r.discipline).filter(Boolean))].sort());
  function setOptions(sel, groups, keep) {  // groups: [[label, [[value, text], ...]], ...]; first option stays
    const first = sel.options[0]; sel.innerHTML = ''; sel.appendChild(first);
    groups.forEach(([label, opts]) => { if (!opts.length) return; const g = label ? document.createElement('optgroup') : sel; if (label) { g.label = label; sel.appendChild(g); }
      opts.forEach(([v, t]) => { const o = document.createElement('option'); o.value = v; o.textContent = t; g.appendChild(o); }); });
    sel.value = [...sel.options].some(o => o.value === keep) ? keep : '';
    return sel.value;
  }
  let fillTab = null;
  function fillDynamic(tab) {  // location and company options with counts from the current tab's roles
    if (fillTab === tab) return; fillTab = tab;
    const base = listFor(tab);
    const stc = {}; let remote = 0, unknown = 0;
    base.forEach(r => { if (r._state) stc[r._state] = (stc[r._state] || 0) + 1; else unknown++; if (r._remote) remote++; });
    const reg = REGIONS.map(([k, label, st]) => [k, label, st.reduce((n, c) => n + (stc[c] || 0), 0)]).filter(x => x[2]).map(([k, label, n]) => [k, label + ' · ' + n]);
    if (remote) reg.push(['remote', 'Remote · ' + remote]); if (unknown) reg.push(['unknown', 'Multiple / unknown · ' + unknown]);
    const st = Object.entries(stc).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([c, n]) => [c, c + ' · ' + n]);
    state.loc = setOptions($('#loc'), [['Regions', reg], ['States', st]], state.loc);
    const cc = {}; base.forEach(r => { if (r.company) cc[r.company] = (cc[r.company] || 0) + 1; });
    state.company = setOptions($('#company'), [['', Object.keys(cc).sort().map(c => [c, c + ' · ' + cc[c]])]], state.company);
  }
  function reflectFilters() {  // push state into the controls
    ['sector', 'disc', 'days', 'loc', 'mode', 'pay', 'exp', 'clr', 'cit', 'company', 'closing', 'timing', 'sort'].forEach(k => { const el = $('#' + k); if (el) el.value = state[k]; });
    $('#only2027').setAttribute('aria-pressed', state.timing === '2027');
    $('#q').value = state.q; $('#payonly').checked = state.payonly; $('#terps').checked = state.terps; $('#newonly').checked = state.newonly;
    document.querySelectorAll('.seg:not(.tabs) button').forEach(x => x.setAttribute('aria-pressed', x.dataset.fit === state.fit));
    $('#more').classList.toggle('open', state.more); $('#more-toggle').setAttribute('aria-expanded', state.more);
  }
  const activeFilters = () => Object.keys(FILTER_DEFAULTS).filter(k => state[k] !== FILTER_DEFAULTS[k]);
  const MORE_KEYS = ['mode', 'pay', 'payonly', 'exp', 'clr', 'cit', 'company', 'closing', 'timing', 'terps', 'newonly'];
  document.querySelectorAll('.seg:not(.tabs) button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.seg:not(.tabs) button').forEach(x => x.setAttribute('aria-pressed', x === b)); state.fit = b.dataset.fit; saveFilters(); render();
  }));
  document.querySelectorAll('.tabs button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.tabs button').forEach(x => x.setAttribute('aria-pressed', x === b)); state.tab = b.dataset.tab; state.open = null; render();
  }));
  ['sector', 'disc', 'days', 'loc', 'mode', 'pay', 'exp', 'clr', 'cit', 'company', 'closing', 'timing'].forEach(k => $('#' + k).addEventListener('change', e => { state[k] = e.target.value; saveFilters(); render(); }));
  $('#only2027').addEventListener('click', () => { state.timing = state.timing === '2027' ? '' : '2027'; saveFilters(); render(); });
  $('#imm-note').addEventListener('click', e => { if (e.target.id === 'imm-show') { e.preventDefault(); state.timing = 'immediate'; saveFilters(); render(); } });
  [['payonly', 'payonly'], ['terps', 'terps'], ['newonly', 'newonly']].forEach(([id, k]) => $('#' + id).addEventListener('change', e => { state[k] = e.target.checked; saveFilters(); render(); }));
  $('#q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); saveFilters(); render(); });
  $('#more-toggle').addEventListener('click', () => { state.more = !state.more; $('#more').classList.toggle('open', state.more); $('#more-toggle').setAttribute('aria-expanded', state.more); saveFilters(); });
  $('#clear-filters').addEventListener('click', () => { Object.assign(state, FILTER_DEFAULTS); fillTab = null; reflectFilters(); saveFilters(); render(); });
  const DEFAULT_DIR = {fit2027: 'asc', fit: 'asc', date: 'desc', applyBy: 'asc', salary: 'desc', company: 'asc', minYears: 'asc', discipline: 'asc'};
  $('#sort').addEventListener('change', e => { state.sort = e.target.value; state.dir = DEFAULT_DIR[state.sort]; saveFilters(); render(); });
  document.querySelectorAll('th.sortable').forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.sort;
    const kk = (k === 'fit' && state.sort === 'fit2027') ? 'fit2027' : k;
    state.dir = state.sort === kk ? (state.dir === 'asc' ? 'desc' : 'asc') : DEFAULT_DIR[kk]; state.sort = kk;
    if ([...$('#sort').options].some(o => o.value === kk)) $('#sort').value = kk; saveFilters(); render();
  }));
  loadFilters();

  // sorting
  const cmpNum = (a, b) => (a == null ? 0 : a) - (b == null ? 0 : b);  // nulls are moved last before this runs
  const cmpStr = (a, b) => (a || '').localeCompare(b || '');
  const KEYS = {
    fit2027: (a, b) => FITRANK[a.fit] - FITRANK[b.fit] || TIMING_RANK[a._timing] - TIMING_RANK[b._timing] || cmpStr(b.date, a.date),
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
    const t = []; const es = effStatus(r); const st = es.status;
    if (r._closed) t.push('<span class="tag closed">closed</span>');
    if (r._new) t.push('<span class="tag new">New</span>');
    if (st && state.tab !== st && state.tab !== 'saved' && state.tab !== 'applied' && state.tab !== 'hidden')
      t.push(`<span class="tag status ${st}${es.repost ? ' repost' : ''}">${st === 'hidden' ? 'Hidden' : st === 'applied' ? 'Applied' : 'Saved'}${es.repost ? ' (re-post)' : ''}</span>`);
    if (r._dt != null && r._dt >= 0 && r._dt <= 10) t.push(`<span class="tag closing">${r._dt === 0 ? 'Closes today' : 'Closes in ' + r._dt + 'd'}</span>`);
    if (r._timing === '2027') t.push(`<span class="tag t2027" title="${esc(r.timingNote || 'Names 2027 in the grad or start window')}">2027</span>`);
    else if (r._timing === 'window') t.push(`<span class="tag twindow" title="${esc(r.timingNote || 'States a grad/start window')}">window</span>`);
    else if (r._timing === 'immediate') { t.push(`<span class="tag tasap" title="${esc(r.timingNote || 'Wants an immediate start')}">ASAP</span>`);
      if (state.tab === 'all' && state.timing !== 'immediate') t.push(`<span class="tag tasap-hidden" title="${esc(r.timingNote || 'Wants an immediate start')}">hidden until spring</span>`); }
    if (r.workMode) t.push(`<span class="tag">${esc(r.workMode)}</span>`);
    if (r.employment && r.employment !== 'Full-time') t.push(`<span class="tag">${esc(r.employment)}</span>`);
    const pf = peopleFor(r); if (pf && pf.people.length) t.push(`<span class="tag terps">${pf.people.length} Terp${pf.people.length === 1 ? '' : 's'}</span>`);
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
  // ---------- Terps found here: people.json from the private sync repo (memory only, never stored or embedded) ----------
  let PEOPLE = null;  // {v, updated, companies: {companyKey: {searched, people: [{name, headline, url}]}}}
  function peopleFor(r) { if (!PEOPLE || !PEOPLE.companies) return null; const e = PEOPLE.companies[companyKey(r.company)]; return e && Array.isArray(e.people) ? e : null; }
  const linkedinOk = u => typeof u === 'string' && /^https?:\/\/([a-z0-9-]+\.)*linkedin\.com\//i.test(u);
  const TKEY = 'jadar.terps.v1', NKEY = 'jadar.notetpl.v1';
  const terpsMode = () => lsGet(TKEY) === 'all' ? 'all' : 'likely';
  const FIELD_OF = {Thermal: 'thermal', Propulsion: 'propulsion', Structures: 'structures', Test: 'test', Nuclear: 'nuclear', Naval: 'naval', Aero: 'aero', Mechanical: 'mechanical', GNC: 'gnc'};
  function rankPeople(list, r) {  // who is most likely to answer a student: recruiters, same field, recent grads
    const field = FIELD_OF[r.discipline] || null;
    const scored = list.map((p, i) => {
      const text = ((p && p.headline) || '') + ' ' + ((p && p.snippet) || ''); const tags = []; let sc = 0;
      if (/recruit|talent|university relations|campus|early career program/i.test(text)) { sc += 3; tags.push('recruiter'); }
      if (field && p && typeof p.via === 'string' && p.via.toLowerCase() === field) { sc += 3; tags.push('same field'); }
      if (/\b(202[2-6])\b|new grad|recent grad|engineer i\b|associate|entry/i.test(text)) { sc += 2; tags.push('recent grad'); }
      if (/engineer/i.test((p && p.headline) || '')) sc += 1;
      if (/\bvp\b|vice president|director|chief|head of|senior director/i.test(text)) sc -= 2;
      return {p, i, sc, tags};
    });
    scored.sort((a, b) => b.sc - a.sc || String(a.p && a.p.name || '').localeCompare(String(b.p && b.p.name || '')) || a.i - b.i);
    return scored;
  }
  const DRAFT = {};  // url -> people list as rendered (for the Draft note buttons)
  function foundBlock(r) {
    if (!syncCfg()) return `<div class="found"><span class="quiet">Connect sync in Data to see Terps found at this company.</span></div>`;
    const e = peopleFor(r);
    if (!e) return `<div class="found"><span class="quiet">Not searched yet (next weekly run).</span></div>`;
    const mode = terpsMode();
    const seg = `<span class="tseg" role="group" aria-label="Terps order"><button type="button" class="pbtn sm${mode === 'likely' ? ' on' : ''}" data-terps="likely" aria-pressed="${mode === 'likely'}">Likely to reply</button><button type="button" class="pbtn sm${mode === 'all' ? ' on' : ''}" data-terps="all" aria-pressed="${mode === 'all'}">All</button></span>`;
    const head = `<div class="fhead"><span class="k mono">Terps found here · ${e.people.length} found${e.searched ? ' · searched ' + esc(fmt(String(e.searched).slice(0, 10))) : ''}</span>${e.people.length ? seg : ''}</div>`;
    if (!e.people.length) return `<div class="found">${head}<span class="quiet">none found yet</span></div>`;
    const ranked = mode === 'likely' ? rankPeople(e.people, r) : e.people.map((p, i) => ({p, i, sc: 0, tags: []}));
    DRAFT[r.url] = ranked.map(x => x.p);
    const items = ranked.slice(0, 6).map((x, k) => {
      const p = x.p; const name = esc(p && p.name || 'Unknown'); const hl = p && p.headline ? `<span class="hl">${esc(p.headline)}</span>` : '';
      const tags = mode === 'likely' ? x.tags.map(t => `<span class="why-t">${esc(t)}</span>`).join('') : '';
      const dr = state.draft && state.draft.url === r.url && state.draft.pi === k ? draftPanel(p, r, state.draft.editing) : '';
      return `<li data-pi="${k}">${linkedinOk(p && p.url) ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">${name} ↗</a>` : name}${hl}${tags}<button type="button" class="pbtn sm draft-b" data-draft="${k}" aria-expanded="${!!dr}">Draft note</button>${dr}</li>`;
    }).join('');
    const more = e.people.length > 6 ? `<li class="quiet">+${e.people.length - 6} more</li>` : '';
    return `<div class="found">${head}<ul>${items}${more}</ul></div>`;
  }
  // ---------- Draft note: a copy-only message to one person; nothing is ever sent by the page ----------
  const noteTemplate = () => lsGet(NKEY) || D.noteTemplate || '';
  function fillNote(tpl, p, r) {
    const name = (p && p.name) || ''; const first = name.trim().split(/\s+/)[0] || 'there';
    return tpl.replace(/\{first\}/g, first).replace(/\{name\}/g, name).replace(/\{title\}/g, r.title || '').replace(/\{company\}/g, companyKey(r.company));
  }
  function draftPanel(p, r, editing) {
    const tpl = noteTemplate();
    const prof = linkedinOk(p && p.url) ? `<a class="pbtn sm" href="${esc(p.url)}" target="_blank" rel="noopener">Open profile ↗</a>` : '';
    if (editing) return `<div class="draft" data-draft-panel="1"><span class="quiet">Template · placeholders: {first} {name} {title} {company}</span><textarea data-tpl="1" aria-label="Note template">${esc(tpl)}</textarea>` +
      `<div class="brow"><button type="button" class="pbtn sm on" data-tpl-save="1">Save template</button><button type="button" class="pbtn sm" data-tpl-reset="1">Reset</button><button type="button" class="pbtn sm" data-draft-close="1">Close</button></div></div>`;
    return `<div class="draft" data-draft-panel="1"><textarea data-note-ta="1" aria-label="Draft note">${esc(fillNote(tpl, p, r))}</textarea>` +
      `<div class="brow"><button type="button" class="pbtn sm on" data-copy="1">Copy</button>${prof}<button type="button" class="pbtn sm" data-tpl-edit="1">Edit template</button><button type="button" class="pbtn sm" data-draft-close="1">Close</button><span class="quiet" data-copy-status=""></span></div></div>`;
  }
  function showDraft(r, pi, editing) {  // (re)render with the panel open and focus its textarea
    state.draft = pi == null ? null : {url: r.url, pi, editing: !!editing}; render();
    if (state.draft) { const ta = $(`.found li[data-pi="${pi}"] textarea`); if (ta) ta.focus({preventScroll: true}); }
  }
  async function copyText(text, statusEl, ta) {
    let ok = false;
    try { await navigator.clipboard.writeText(text); ok = true; } catch (e) {}
    if (!ok && ta) { try { ta.focus(); ta.select(); ok = document.execCommand('copy'); } catch (e) {} }
    if (statusEl) statusEl.textContent = ok ? 'copied' : 'select the text and copy';
  }
  function detail(r) {
    const yrs = r.minYears == null ? 'not stated' : r.minYears + (r.schoolExpOk ? ' (school/internship counts)' : '');
    const pay = r.salary ? r.salary + (/\/hr$/.test(r.salary) && r.salaryMin != null ? ' · $' + num(r.salaryMin) + (r.salaryMax != null && r.salaryMax !== r.salaryMin ? '–$' + num(r.salaryMax) : '') + ' annualized' : '') : null;
    const left = [kv('Min experience', yrs), kv('Degree', r.degree), kv('Major', r.majorReq), kv('GPA', r.gpaReq), kv('Clearance', r.clearance), kv('Citizenship', r.citizenship),
      kv('Timing', TIMING_LABEL[r._timing] + (r.timingNote ? ' · ' + r.timingNote : '')), kv('Grad window', r.gradReq), kv('Start', r.startReq), kv('Start window', r.startWindow), kv('Apply by', r.applyBy ? fmtLong(r.applyBy) + (r._dt != null ? ' (' + (r._dt < 0 ? 'passed' : r._dt + ' days') + ')' : '') : null),
      kv('Pay', pay), kv('Work mode', r.workMode), kv('Employment', r.employment), kv('Travel', r.travel), kv('Relocation', r.relocation === true ? 'offered' : r.relocation === false ? 'not offered' : null),
      kv('Posted', r.date ? fmtLong(r.date) + ' (' + r.dateKind + ')' : null), kv('First seen', r.firstSeen ? fmtLong(r.firstSeen) : null), kv('Sector', r.sector)].join('');
    const snip = r.reqSnippet ? `<div class="snip"><div class="k mono">Minimum qualifications</div>${esc(r.reqSnippet)}</div>` : `<div class="snip"><div class="k mono">Why</div>${esc(r.why)}</div>`;
    return `<div class="panel"><div class="kv">${left}</div><div>${snip}<a class="btn" href="${esc(r.url)}" target="_blank" rel="noopener">Open posting ↗</a>${people(r)}${foundBlock(r)}</div></div>${actRow(r)}`;
  }
  function listFor(tab) {  // the universe of rows for a tab, before filters
    if (tab === 'inbox') return roles.filter(inInbox);
    if (tab === 'all') return roles.slice();
    const st = tab;  // saved / applied / hidden: stored entries, newest action first, closed postings as snapshots
    return Object.values(S.roles).filter(e => e.status === st).sort((a, b) => (b.at || '').localeCompare(a.at || ''))
      .map(e => byUrl.get(e.snap && e.snap.url) || snapRole(e));
  }
  function render() {
    FPM = null; renderStats();
    const c = counts(); const inboxN = roles.filter(inInbox).length;
    const badges = {inbox: inboxN, saved: c.saved, applied: c.applied, hidden: c.hidden, all: roles.length};
    document.querySelectorAll('.tabs [data-badge]').forEach(b => b.textContent = badges[b.dataset.badge] ? ' ' + badges[b.dataset.badge] : '');
    $('#state-sum').textContent = (c.saved || c.applied || c.hidden) ? `${c.saved} saved · ${c.applied} applied · ${c.hidden} hidden` : '';
    fillDynamic(state.tab); reflectFilters();
    const base = listFor(state.tab); const listTab = ['saved', 'applied', 'hidden'].includes(state.tab);
    let list = listTab ? base : base.filter(r => state.fit === 'all' || (state.fit === 'fits' ? r.fit !== 'No' : r.fit === state.fit));
    if (!listTab) {  // your own lists (Saved / Applied / Disliked) show everything you marked; only the search box narrows them
    if (state.sector) list = list.filter(r => r.sector === state.sector);
    if (state.disc) list = list.filter(r => r.discipline === state.disc);
    if (state.days) list = list.filter(r => r.dateKind === 'posted' && r.date && daysTo(r.date) >= -Number(state.days));
    if (state.loc) list = list.filter(r => locMatch(r, state.loc));
    if (state.mode) list = list.filter(r => r.workMode === state.mode || (state.mode === 'Remote' && r._remote));
    if (state.pay) list = list.filter(r => r.salaryMax == null ? !state.payonly : r.salaryMax >= Number(state.pay));
    else if (state.payonly) list = list.filter(r => r.salaryMax != null);
    if (state.exp) list = list.filter(r => state.exp === 'ns' ? r.minYears == null : state.exp === '0' ? r.minYears === 0 : (r.minYears != null && r.minYears <= 1));
    if (state.clr) list = list.filter(r => state.clr === 'none' ? !r.clearance : /obtain/i.test(r.clearance || ''));
    if (state.cit) list = list.filter(r => state.cit === 'none' ? !r.citizenship : state.cit === 'citizen' ? /citizen/i.test(r.citizenship || '') : /itar|person/i.test(r.citizenship || ''));
    if (state.company) list = list.filter(r => r.company === state.company);
    if (state.closing) list = list.filter(r => state.closing === 'any' ? !!r.applyBy : (r._dt != null && r._dt >= 0 && r._dt <= Number(state.closing)));
    if (state.terps) list = list.filter(r => { const e = peopleFor(r); return e && e.people.length; });
    if (state.timing) list = list.filter(r => r._timing === state.timing);
    if (state.newonly) list = list.filter(r => r._new);
    }
    const nMore = MORE_KEYS.filter(k => state[k] !== FILTER_DEFAULTS[k]).length;
    $('#more-toggle').textContent = nMore ? 'More filters · ' + nMore : 'More filters';
    $('#clear-filters').hidden = !activeFilters().length;
    const tc = $('#terps-chk'); tc.classList.toggle('off', !PEOPLE); $('#terps').disabled = !PEOPLE; tc.title = PEOPLE ? '' : 'Connect sync in Data to use this';
    if (state.q) { const words = state.q.split(/\s+/).filter(Boolean);  // every word must appear somewhere in the row
      list = list.filter(r => { const h = r._q || [r.company, r.title, r.location].join(' ').toLowerCase(); return words.every(w => h.includes(w)); }); }
    if (!listTab) list = sorted(list);
    document.querySelectorAll('th.sortable').forEach(th => (!listTab && (th.dataset.sort === state.sort || (th.dataset.sort === 'fit' && state.sort === 'fit2027'))) ? th.setAttribute('aria-sort', state.dir === 'asc' ? 'ascending' : 'descending') : th.removeAttribute('aria-sort'));
    $('#count').textContent = list.length + ' of ' + base.length + ' roles';
    const immN = (state.tab === 'inbox' && state.timing !== 'immediate') ? roles.filter(r => immHidden(r) && (state.fit === 'all' || (state.fit === 'fits' ? r.fit !== 'No' : r.fit === state.fit))).length : 0;
    $('#imm-note').hidden = !immN;
    if (immN) $('#imm-note').innerHTML = `${immN} immediate-start role${immN === 1 ? '' : 's'} hidden · <a href="#" id="imm-show">show</a>`;
    if (!list.length) {
      const msg = {saved: 'Nothing saved yet. Star a role to keep it here.', applied: 'Nothing marked applied yet.', hidden: 'Nothing hidden. The ✕ on a role sends it here.'}[state.tab] || 'Nothing matches these filters.';
      $('#rows').innerHTML = `<tr><td colspan="9" class="empty">${msg}</td></tr>`; return;
    }
    $('#rows').innerHTML = list.map(r => {
      const open = !r._closed && state.open === r.id; const es = effStatus(r);
      const dim = state.tab === 'all' && (es.status === 'hidden' || (r._timing === 'immediate' && state.timing !== 'immediate'));
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
    const tb = e.target.closest('button[data-terps]');
    if (tb) { e.stopPropagation(); lsSet(TKEY, tb.dataset.terps); render(); return; }
    const db = e.target.closest('button[data-draft], button[data-copy], button[data-tpl-edit], button[data-tpl-save], button[data-tpl-reset], button[data-draft-close]');
    if (db) {
      e.stopPropagation(); const r = roleFromEl(db); const li = db.closest('li'); if (!r || !li) return;
      const pi = Number(li.dataset.pi); const p = (DRAFT[r.url] || [])[pi]; if (!p) return;
      const isOpen = state.draft && state.draft.url === r.url && state.draft.pi === pi;
      if (db.dataset.draft != null) showDraft(r, isOpen ? null : pi, false);
      else if (db.dataset.copy) { const ta = li.querySelector('textarea[data-note-ta]'); copyText(ta ? ta.value : '', li.querySelector('[data-copy-status]'), ta); }
      else if (db.dataset.tplEdit) showDraft(r, pi, true);
      else if (db.dataset.tplSave) { const ta = li.querySelector('textarea[data-tpl]'); if (ta && ta.value.trim()) lsSet(NKEY, ta.value); showDraft(r, pi, false); }
      else if (db.dataset.tplReset) { lsDel(NKEY); showDraft(r, pi, false); }
      else if (db.dataset.draftClose) showDraft(r, null);
      return;
    }
    if (e.target.closest('a') || e.target.closest('input') || e.target.closest('textarea') || e.target.closest('tr.detail')) return;
    const tr = e.target.closest('tr.row'); if (!tr || tr.querySelector('.chev[style]')) return;
    state.open = state.open === tr.dataset.id ? null : tr.dataset.id; state.draft = null; render();
    if (state.open) { const el = $(`tr.row[data-id="${state.open}"]`); if (el) el.focus({preventScroll: true}); }
  });
  $('#rows').addEventListener('keydown', e => {
    if (e.target.matches('input[data-note]')) { if (e.key === 'Enter') { e.preventDefault(); e.target.blur(); } return; }
    if (e.target.matches('textarea')) return;
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
    if (confirm(`Un-hide ${n} role${n === 1 ? '' : 's'}?`)) { Object.keys(S.roles).forEach(u => { if (S.roles[u].status === 'hidden') { if (S.roles[u].note || S.roles[u].app) { S.roles[u].status = null; S.roles[u].at = new Date().toISOString(); } else delete S.roles[u]; } }); persist(); render(); }
  });

  // optional sync through a private GitHub repo (token stays in this browser; only api.github.com is contacted) — shared with the Tracker page
  const syncCfg = J.syncCfg, b64dec = J.b64dec, ghHeaders = J.ghHeaders, peopleUrl = J.peopleUrl;
  function reflectSync() { const c = syncCfg(); $('#sync-connect').style.display = c ? 'none' : ''; $('#sync-disconnect').style.display = c ? '' : 'none'; $('#sync-now').style.display = c ? '' : 'none'; if (c) { $('#sync-repo').value = c.repo; $('#sync-path').value = c.path || 'state.json'; } }
  async function loadPeople(c) {
    try {
      const r = await fetch(peopleUrl(c), {headers: ghHeaders(c), cache: 'no-store'});
      if (!r.ok) { if (r.status === 404) PEOPLE = {v: 1, companies: {}}; return; }
      const j = await r.json(); const d = JSON.parse(b64dec(j.content || ''));
      if (d && typeof d === 'object' && d.companies && typeof d.companies === 'object' && JSON.stringify(d) !== JSON.stringify(PEOPLE)) { PEOPLE = d; render(); }
    } catch (e) { /* quiet: the block says "not searched yet" */ }
  }
  const sync = J.makeSync({get: () => S, set: s => { S = s; FPM = null; adoptManual(); render(); }, statusEl: $('#sync-status'), after: c => loadPeople(c)});
  const setSync = sync.setStatus, syncNow = sync.syncNow, schedulePush = sync.schedulePush;
  $('#sync-connect').addEventListener('click', () => {
    const repo = $('#sync-repo').value.trim(), path = $('#sync-path').value.trim() || 'state.json', token = $('#sync-token').value.trim();
    if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) { alert('Repository must look like owner/name'); return; }
    if (!token) { alert('Paste a fine-grained token for that repo (Contents: read and write)'); return; }
    if (!lsSet(SKEY, JSON.stringify({repo, path, token}))) { alert('This browser blocks storage; sync cannot be kept.'); return; }
    $('#sync-token').value = ''; reflectSync(); syncNow();
  });
  $('#sync-disconnect').addEventListener('click', () => { lsDel(SKEY); PEOPLE = null; reflectSync(); setSync(''); render(); });
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
  // rows added on the Tracker page (or imported from the sheet) with a link to a live posting become that posting's applied entry
  function adoptManual() {
    const norm = u => String(u || '').trim().replace(/\/+$/, ''); const live = new Map(roles.map(r => [norm(r.url), r])); let changed = false;
    Object.entries(S.manual || {}).forEach(([id, m]) => {
      const r = m.link && live.get(norm(m.link)); if (!r) return;
      const cur = S.roles[r.url] || {}; const now = new Date().toISOString();
      S.roles[r.url] = Object.assign({}, cur, {status: 'applied', at: now, snap: (cur.snap && cur.snap.title) ? cur.snap : snapOf(r), fp: fpOf(r), app: Object.assign({status: 'applied', appliedOn: D.today}, cur.app || {}, m.app || {}, {updatedAt: now})});
      delete S.manual[id]; changed = true;
    });
    if (changed) persist();
  }
  adoptManual();
  render();
  if (syncCfg()) syncNow();
})();
</script>
</body>
</html>
"""

CSS_SHARED_EXTRA = r"""
/* shared bits (nav, pills, data panel, footer) */
.topnav { display: inline-flex; align-items: center; gap: 4px; margin: 0 0 22px; padding: 4px; border-radius: 999px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14); font-size: 13px; letter-spacing: .01em; }
.topnav .sep { display: none; }
.topnav a { color: var(--on-hero); text-decoration: none; opacity: .72; padding: 7px 16px; border-radius: 999px; font-weight: 600; transition: background .12s, opacity .12s; }
.topnav a:hover { opacity: 1; background: rgba(255,255,255,.10); }
.topnav a[aria-current] { opacity: 1; background: var(--ember); color: #fff; }
.topnav a:focus-visible { outline: 2px solid var(--ember); outline-offset: 2px; }
.tabsrow { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin: 0 0 10px; }
.ctl.small { min-height: 32px; padding: 6px 12px; font-size: 13px; }
.sync-status { color: var(--muted); }
.pbtn { font: inherit; font-size: 13px; font-weight: 600; border: 1px solid var(--line); background: var(--page); color: var(--ink); border-radius: 999px; padding: 7px 14px; cursor: pointer; min-height: 32px; }
.pbtn.on { background: var(--ink); color: var(--page); border-color: var(--ink); }
.pbtn.sm { padding: 3px 10px; font-size: 12px; min-height: 0; }
#datapanel { display: none; background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px; margin: 0 0 14px; }
#datapanel.open { display: block; }
.dp-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 6px 0; }
.dp-row + .dp-row { margin-top: 10px; }
.dp-head { margin: 10px 0 4px; }
.dp-note { color: var(--muted); font-size: 12.5px; }
.dp-row input[type="text"], .dp-row input[type="password"], .dp-row input[type="date"], .dp-row input[type="url"] { font: inherit; font-size: 13.5px; border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; background: var(--page); color: var(--ink); min-width: 140px; }
.dp-row input.wide { flex: 1 1 220px; }
.empty { padding: 24px 10px; color: var(--muted); }
footer { color: var(--muted); font-size: 13px; margin: 36px 0 12px; }
footer a { color: var(--ink); }
"""

# JavaScript shared by index.html and tracker.html: same storage keys, same state shape, same merge, same GitHub sync.
SHARED_JS = r"""<script>
window.JADAR = (function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const isIso = s => /^\d{4}-\d{2}-\d{2}/.test(String(s || ''));
  const fmt = (iso, today) => { if (!isIso(iso)) return iso || ''; const [y,m,d] = iso.split('-').map(Number); return MON[m-1] + ' ' + d + (today && y !== today.getFullYear() ? ', ' + y : ''); };
  const fmtLong = iso => { if (!isIso(iso)) return iso || ''; const [y,m,d] = iso.split('-').map(Number); return MON[m-1] + ' ' + d + ', ' + y; };
  const daysTo = (iso, today) => { if (!isIso(iso)) return null; const [y,m,d] = iso.split('-').map(Number); return Math.round((new Date(y, m-1, d) - today) / 86400000); };
  const nowIso = () => new Date().toISOString();
  function companyKey(c) { return (c || '').replace(/\s*\(.*?\)\s*/g, ' ').split(' / ')[0].replace(/\s+/g, ' ').trim(); }
  // 9/8/26, 10/12/2026, 11/11 (this year), 2026-09-08, "Nov 11" -> ISO; anything else -> null
  function parseDate(s, year) {
    s = String(s || '').trim(); if (!s) return null;
    let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/); if (m) return m[1] + '-' + m[2].padStart(2, '0') + '-' + m[3].padStart(2, '0');
    m = s.match(/^(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?/);
    if (m) { let y = m[3] ? Number(m[3]) : year; if (y < 100) y += 2000; const mo = Number(m[1]), d = Number(m[2]); if (mo < 1 || mo > 12 || d < 1 || d > 31) return null; return y + '-' + String(mo).padStart(2, '0') + '-' + String(d).padStart(2, '0'); }
    m = s.match(/^([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?/);
    if (m) { const mo = MON.findIndex(x => x.toLowerCase() === m[1].toLowerCase()); if (mo < 0) return null; return (m[3] ? Number(m[3]) : year) + '-' + String(mo + 1).padStart(2, '0') + '-' + m[2].padStart(2, '0'); }
    return null;
  }
  // ---- state: one object shared by both pages, in this browser and (optionally) in the private sync repo ----
  const KEY = 'jadar.state.v1', SKEY = 'jadar.sync.v1';
  const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } };
  const lsDel = k => { try { localStorage.removeItem(k); } catch (e) {} };
  const emptyState = () => ({v: 1, roles: {}, manual: {}, tracker: {connections: [], places: [], at: ''}});
  function normState(s) {  // older files have only `roles`; give them the tracker parts
    if (!s || s.v !== 1 || !s.roles || typeof s.roles !== 'object') return null;
    if (!s.manual || typeof s.manual !== 'object') s.manual = {};
    if (!s.tracker || typeof s.tracker !== 'object') s.tracker = {connections: [], places: [], at: ''};
    if (!Array.isArray(s.tracker.connections)) s.tracker.connections = []; if (!Array.isArray(s.tracker.places)) s.tracker.places = [];
    return s;
  }
  function loadState() { try { const s = normState(JSON.parse(lsGet(KEY) || 'null')); if (s) return s; } catch (e) {} return emptyState(); }
  const saveState = s => lsSet(KEY, JSON.stringify(s));
  function mergeStates(a, b) {  // roles per url and manual rows per id: newer `at` wins; tracker lists: newer `at` wins as a whole
    a = normState(a) || emptyState(); b = normState(b) || emptyState();
    const out = emptyState();
    const newer = (x, y) => !x ? y : !y ? x : ((y.at || '') > (x.at || '') ? y : x);
    new Set([...Object.keys(a.roles), ...Object.keys(b.roles)]).forEach(u => { out.roles[u] = newer(a.roles[u], b.roles[u]); });
    new Set([...Object.keys(a.manual), ...Object.keys(b.manual)]).forEach(k => { out.manual[k] = newer(a.manual[k], b.manual[k]); });
    out.tracker = newer(a.tracker, b.tracker);
    return out;
  }
  // ---- GitHub Contents API (token stays in this browser; only api.github.com is contacted) ----
  const b64enc = s => { const u = new TextEncoder().encode(s); let bin = ''; for (let i = 0; i < u.length; i += 0x8000) bin += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(bin); };
  const b64dec = b => new TextDecoder().decode(Uint8Array.from(atob(b.replace(/\s/g, '')), ch => ch.charCodeAt(0)));
  function syncCfg() { try { const c = JSON.parse(lsGet(SKEY) || 'null'); return c && c.repo && c.token ? c : null; } catch (e) { return null; } }
  const ghUrl = c => 'https://api.github.com/repos/' + c.repo + '/contents/' + (c.path || 'state.json');
  const ghHeaders = c => ({'Authorization': 'Bearer ' + c.token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'});
  const peopleUrl = c => 'https://api.github.com/repos/' + c.repo + '/contents/' + ((c.path || 'state.json').replace(/[^/]*$/, '') + 'people.json');
  async function ghGet(c) {
    const r = await fetch(ghUrl(c), {headers: ghHeaders(c), cache: 'no-store'});
    if (r.status === 404) return {state: null, sha: null};
    if (!r.ok) throw new Error(String(r.status));
    const j = await r.json(); let st = null; try { st = normState(JSON.parse(b64dec(j.content || ''))); } catch (e) { st = null; }
    return {state: st, sha: j.sha};
  }
  async function ghPut(c, st, sha) {
    const body = {message: 'jadar state', content: b64enc(JSON.stringify(st, null, 1))}; if (sha) body.sha = sha;
    const r = await fetch(ghUrl(c), {method: 'PUT', headers: Object.assign({'Content-Type': 'application/json'}, ghHeaders(c)), body: JSON.stringify(body)});
    if (!r.ok) throw new Error(String(r.status));
  }
  function makeSync(o) {  // o: {get: () => state, set: state => void, statusEl, after?: cfg => void}
    let syncing = false, pending = false, timer = null;
    const setStatus = m => { if (o.statusEl) o.statusEl.textContent = m || ''; };
    async function syncNow() {
      const c = syncCfg(); if (!c) return;
      if (syncing) { pending = true; return; }
      syncing = true;
      try {
        if (navigator.onLine === false) { setStatus('offline'); return; }
        setStatus('syncing…');
        const {state: remote, sha} = await ghGet(c);
        const S = o.get(); const before = JSON.stringify(S);
        const merged = remote ? mergeStates(S, remote) : S;
        if (JSON.stringify(merged) !== before) { saveState(merged); o.set(merged); }
        if (!remote || JSON.stringify(merged) !== JSON.stringify(remote)) await ghPut(c, merged, sha);
        setStatus('synced ' + new Date().toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'}).toLowerCase());
        if (o.after) o.after(c);
      } catch (err) { setStatus('sync failed: ' + (err.message || 'error')); }
      finally { syncing = false; if (pending) { pending = false; syncNow(); } }
    }
    function schedulePush() { if (!syncCfg()) return; clearTimeout(timer); timer = setTimeout(syncNow, 2000); }
    return {syncNow, schedulePush, setStatus};
  }
  function bindSyncPanel($, sync, onChange) {  // the Data panel's Connect / Disconnect / Sync now controls (same markup on both pages)
    function reflect() { const c = syncCfg(); $('#sync-connect').style.display = c ? 'none' : ''; $('#sync-disconnect').style.display = c ? '' : 'none'; $('#sync-now').style.display = c ? '' : 'none'; if (c) { $('#sync-repo').value = c.repo; $('#sync-path').value = c.path || 'state.json'; } }
    $('#sync-connect').addEventListener('click', () => {
      const repo = $('#sync-repo').value.trim(), path = $('#sync-path').value.trim() || 'state.json', token = $('#sync-token').value.trim();
      if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) { alert('Repository must look like owner/name'); return; }
      if (!token) { alert('Paste a fine-grained token for that repo (Contents: read and write)'); return; }
      if (!lsSet(SKEY, JSON.stringify({repo, path, token}))) { alert('This browser blocks storage; sync cannot be kept.'); return; }
      $('#sync-token').value = ''; reflect(); sync.syncNow();
    });
    $('#sync-disconnect').addEventListener('click', () => { lsDel(SKEY); reflect(); sync.setStatus(''); if (onChange) onChange(); });
    $('#sync-now').addEventListener('click', sync.syncNow);
    window.addEventListener('online', () => { if (syncCfg()) sync.syncNow(); });
    reflect();
  }
  return {esc, MON, isIso, fmt, fmtLong, daysTo, nowIso, companyKey, parseDate, KEY, SKEY, lsGet, lsSet, lsDel, emptyState, normState, loadState, saveState, mergeStates,
          b64enc, b64dec, syncCfg, ghUrl, ghHeaders, peopleUrl, ghGet, ghPut, makeSync, bindSyncPanel};
})();
</script>"""

TRACKER_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&display=swap">
<style>
__CSS_SHARED__
/* tracker table */
.stats.four { grid-template-columns: repeat(4, 1fr); }
.twrap { overflow-x: auto; border-top: 1px solid var(--line); -webkit-overflow-scrolling: touch; }
table.tr { border-collapse: collapse; width: 100%; min-width: 1120px; font-size: 13px; }
.tr th, .tr td { text-align: left; vertical-align: top; padding: 9px 6px; border-bottom: 1px solid var(--line); background: var(--page); }
.tr th { color: var(--muted); font-weight: 500; white-space: nowrap; user-select: none; }
.tr th.sortable { cursor: pointer; } .tr th.sortable:hover { color: var(--ink); }
.tr th .arrow { display: inline-block; width: 1em; opacity: 0; } .tr th[aria-sort] .arrow { opacity: 1; color: var(--ink); }
.tr th[aria-sort="ascending"] .arrow::after { content: "↑"; } .tr th[aria-sort="descending"] .arrow::after { content: "↓"; }
.tr th:first-child, .tr td.co { position: sticky; left: 0; z-index: 1; font-weight: 600; min-width: 130px; box-shadow: 1px 0 0 var(--line); }
.tr td.pos a { font-weight: 600; text-decoration: none; } .tr td.pos a:hover { text-decoration: underline; }
.tr td.pos { min-width: 180px; }
.stats.five { grid-template-columns: repeat(5, 1fr); }
tr.fu td:first-child { box-shadow: inset 3px 0 0 #f0b400; }
.pbtn.tiny { font-size: 11.5px; padding: 3px 9px; min-height: 0; margin-top: 4px; }
#upnext { margin: 0 0 26px; } #upnext .sm-table td.n { white-space: nowrap; } .due-soon { color: var(--crit); font-weight: 600; }
tr.st-rejected td, tr.st-closed td, tr.st-withdrawn td { background: color-mix(in srgb, var(--page) 90%, #d03b3b); }
tr.st-screen td, tr.st-interview td { background: color-mix(in srgb, var(--page) 86%, #f0b400); }
tr.st-offer td { background: color-mix(in srgb, var(--page) 88%, #0ca30c); }
td.ed { cursor: text; min-width: 96px; } td.ed:hover { box-shadow: inset 0 0 0 1px var(--line); border-radius: 6px; }
td.ed.editing { cursor: default; }
td.ed input, td.ed textarea { font: inherit; font-size: 13px; width: 100%; min-width: 110px; border: 1px solid var(--ember); border-radius: 6px; padding: 4px 6px; background: var(--page); color: var(--ink); }
td.ed textarea { min-height: 54px; resize: vertical; }
.hint { color: var(--muted); font-size: 11.5px; display: block; margin-top: 2px; }
.late { color: var(--crit); font-weight: 600; }
select.sel { font: inherit; font-size: 12.5px; font-weight: 500; border: 1px solid var(--line); border-radius: 999px; padding: 4px 22px 4px 10px; background: var(--pill); color: var(--ink); appearance: none; -webkit-appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, currentColor 50%), linear-gradient(135deg, currentColor 50%, transparent 50%); background-position: calc(100% - 13px) 55%, calc(100% - 8px) 55%; background-size: 5px 5px; background-repeat: no-repeat; }
.rm { color: var(--muted); background: none; border: 0; cursor: pointer; font-size: 15px; padding: 2px 6px; border-radius: 999px; } .rm:hover { color: var(--crit); background: var(--pill); }
.src { color: var(--muted); font-size: 11px; } td.pos .src { display: block; margin-top: 2px; }
.sub2 { display: grid; grid-template-columns: 3fr 2fr; gap: 24px; margin-top: 10px; }
.sm-table { border-collapse: collapse; width: 100%; font-size: 13.5px; border-top: 1px solid var(--line); }
.sm-table th, .sm-table td { text-align: left; vertical-align: top; padding: 9px 8px; border-bottom: 1px solid var(--line); }
.sm-table th { color: var(--muted); font-weight: 500; white-space: nowrap; }
.sm-table td.ed:hover { box-shadow: inset 0 0 0 1px var(--line); border-radius: 6px; }
.sm-table td.ed input, .sm-table td.ed textarea { font: inherit; font-size: 13px; width: 100%; border: 1px solid var(--ember); border-radius: 6px; padding: 4px 6px; background: var(--page); color: var(--ink); }
.addrow { margin: 8px 0 0; }
textarea.tsv { width: 100%; min-height: 120px; font: 12.5px/1.4 ui-monospace, Menlo, Consolas, monospace; border: 1px solid var(--line); border-radius: 12px; padding: 10px; background: var(--page); color: var(--ink); }
.controls.more { display: none; padding: 10px 12px; background: var(--card); border: 1px solid var(--line); border-radius: 16px; margin-bottom: 12px; } .controls.more.open { display: flex; }
.controls.more input { font: inherit; font-size: 13.5px; border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; background: var(--page); color: var(--ink); min-width: 140px; }
@media (max-width: 900px) { .sub2 { grid-template-columns: 1fr; } }
@media (max-width: 640px) { main { padding: 12px 16px; } .hero { padding: 28px 20px 22px; border-radius: 20px; } .stats, .stats.four, .stats.five { grid-template-columns: repeat(2, 1fr); } .stat:nth-child(3) { border-left: 0; } .stat:nth-child(-n+2) { border-bottom: 1px solid var(--line); } .count { margin-left: 0; width: 100%; } }
</style>
</head>
<body>
<main>
<section class="hero">
  <nav class="topnav mono" aria-label="Pages"><a href="index.html" title="Open roles">Radar</a><span class="sep">·</span><a href="tracker.html" aria-current="page">Tracker</a></nav>
  <h1>Tracker.</h1>
  <div class="meta mono" id="meta"></div>
  <div class="who" id="who"></div>
</section>

<section class="stats five" id="stats" aria-label="Summary"></section>

<section id="upnext" hidden>
<h2>Up next.</h2>
<p class="lede">Roles you saved on the radar that have a deadline, soonest first.</p>
<table class="sm-table" id="next"><thead><tr><th>Company</th><th>Role</th><th>Apply by</th><th>Fit</th></tr></thead><tbody id="next-rows"></tbody></table>
<p class="dp-note" id="next-note"></p>
</section>

<h2>Applications.</h2>
<p class="lede">Every role you marked applied on the radar, plus anything you add here. Click a cell to edit; it saves on Enter or when you click away.</p>
<div class="tabsrow">
  <button type="button" class="ctl small" id="add-toggle" aria-expanded="false" aria-controls="addform">Add row</button>
  <button type="button" class="ctl small" id="data-toggle" aria-expanded="false" aria-controls="datapanel">Data</button>
  <button type="button" class="ctl small" id="fu-toggle" aria-pressed="false" title="Applied 14+ days ago (or past the expected date) with no reply and no follow-up in the last 14 days">Needs follow-up</button>
  <span class="sync-status mono" id="sync-status"></span>
  <span class="count mono" id="count"></span>
</div>
<div class="controls more" id="addform">
  <input type="text" id="add-company" placeholder="Company" aria-label="Company">
  <input type="text" id="add-position" placeholder="Position" aria-label="Position" style="flex:1 1 220px">
  <input type="url" id="add-link" placeholder="Link (optional)" aria-label="Link" style="flex:1 1 220px">
  <input type="date" id="add-applied" aria-label="Applied on">
  <button type="button" class="pbtn on" id="add-save">Add</button>
  <button type="button" class="pbtn" id="add-cancel">Cancel</button>
</div>
<div id="datapanel">
  <div class="dp-row">
    <button type="button" class="pbtn" id="export-csv">Export CSV</button>
    <button type="button" class="pbtn" id="export-btn">Export jadar-state.json</button>
    <span class="dp-note">The same state file as the radar: applied roles, your edits here, connections and places.</span>
  </div>
  <div class="dp-head mono">Import from your sheet</div>
  <div class="dp-note">Select the rows in Google Sheets (header row optional), copy, paste here. Columns by header name, or in this order: Company, Position, Benefits, Applied, Posted, Pay Range, Expected Response, First Response, Dates, Appl. Link, Contacted.</div>
  <textarea class="tsv" id="tsv" aria-label="Pasted rows" placeholder="Company	Position	Benefits	Applied	Posted	Pay Range	…"></textarea>
  <div class="dp-row">
    <button type="button" class="pbtn" id="tsv-preview">Preview</button>
    <button type="button" class="pbtn on" id="tsv-import" disabled>Import</button>
    <span class="dp-note" id="tsv-note"></span>
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
<div class="twrap">
  <table class="tr" id="apps">
    <thead><tr>
      <th class="sortable" data-sort="company">Company<span class="arrow"></span></th>
      <th>Position</th>
      <th>Benefits</th>
      <th class="sortable" data-sort="applied">Applied<span class="arrow"></span></th>
      <th class="sortable" data-sort="posted">Posted<span class="arrow"></span></th>
      <th>Pay range</th>
      <th>Expected response</th>
      <th>First response</th>
      <th>Dates</th>
      <th>Contacted</th>
      <th class="sortable" data-sort="status">Status<span class="arrow"></span></th>
      <th>Notes</th>
      <th></th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
</div>

<div class="sub2">
  <section>
    <h2>Connections.</h2>
    <p class="lede">Who you know where, and what they told you.</p>
    <table class="sm-table" id="conn"><thead><tr><th>Company</th><th>Connections</th><th>Advice</th><th></th></tr></thead><tbody id="conn-rows"></tbody></table>
    <button type="button" class="pbtn addrow" id="conn-add">Add connection</button>
  </section>
  <section>
    <h2>Places of interest.</h2>
    <p class="lede">Where you'd want to be, and why.</p>
    <table class="sm-table" id="places"><thead><tr><th>Place</th><th>Reason</th><th></th></tr></thead><tbody id="place-rows"></tbody></table>
    <button type="button" class="pbtn addrow" id="place-add">Add place</button>
  </section>
</div>

<footer>Nothing here is sent to any company. Source: <a href="__REPO__">__REPO_SHORT__</a>.</footer>
</main>
<script id="data" type="application/json">__DATA__</script>
__SHARED_JS__
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const J = window.JADAR; const $ = (s, el) => (el || document).querySelector(s); const esc = J.esc;
  const today = new Date(D.today + 'T00:00:00'); const YEAR = today.getFullYear();
  const fmt = iso => J.fmt(iso, today), daysTo = iso => J.daysTo(iso, today), isIso = J.isIso;
  let S = J.loadState();
  if (D.profileName) $('#who').textContent = 'For ' + D.profileName;
  const STATUSES = ['applied', 'screen', 'interview', 'offer', 'rejected', 'closed', 'withdrawn'];
  const LABEL = {applied: 'Applied', screen: 'Phone screen', interview: 'Interview', offer: 'Offer', rejected: 'Rejected', closed: 'Closed', withdrawn: 'Withdrawn'};
  const RANK = {offer: 0, interview: 1, screen: 2, applied: 3, withdrawn: 4, closed: 5, rejected: 6};
  const APP_FIELDS = ['benefits', 'appliedOn', 'posted', 'pay', 'expected', 'firstResponse', 'dates', 'contacted', 'notes'];
  const FU_DAYS = 14;  // no reply after this many days -> nudge; a follow-up resets the clock
  function needsFollowUp(r) {
    if ((r.app.status || 'applied') !== 'applied' || r.get('firstResponse')) return false;
    const last = r.app.followedUp; if (isIso(last) && -daysTo(last) < FU_DAYS) return false;
    const exp = r.get('expected'), ap = r.get('appliedOn');
    return (isIso(exp) && daysTo(exp) < 0) || (isIso(ap) && -daysTo(ap) >= FU_DAYS);
  }
  function markFollowedUp(row) {
    const t = target(row); if (!t) return; t.app = t.app || {}; t.app.followedUp = D.today;
    const note = 'Followed up ' + fmt(D.today); t.app.contacted = t.app.contacted ? t.app.contacted + '; ' + note : note;
    t.app.updatedAt = J.nowIso(); stamp(t); persist(); render();
  }
  const DATE_FIELDS = new Set(['appliedOn', 'posted', 'expected', 'firstResponse']);
  const sync = J.makeSync({get: () => S, set: s => { S = s; render(); }, statusEl: $('#sync-status')});
  function persist() { J.saveState(S); sync.schedulePush(); }
  const stamp = (t) => { t.at = J.nowIso(); return t; };

  // ---- rows: applied radar roles + manual rows, read from the shared state (no roles data is embedded in this page) ----
  function target(row) { return row.kind === 'radar' ? S.roles[row.key] : S.manual[row.key]; }
  function rowsAll() {
    const out = [];
    Object.entries(S.roles).forEach(([url, e]) => {
      if (e.status !== 'applied') return; const s = e.snap || {}; const app = e.app || {};
      out.push({kind: 'radar', key: url, company: s.company || '', position: s.title || '', link: url, app,
                get: f => f === 'pay' ? (app.pay || s.salary || '') : f === 'posted' ? (app.posted || s.date || '') : f === 'appliedOn' ? (app.appliedOn || (e.at || '').slice(0, 10)) : (app[f] || '')});
    });
    Object.entries(S.manual || {}).forEach(([id, m]) => {
      const app = m.app || {};
      out.push({kind: 'manual', key: id, company: m.company || '', position: m.position || '', link: m.link || '', app, get: f => f === 'posted' ? (app.posted || m.posted || '') : (app[f] || '')});
    });
    return out;
  }
  function setApp(row, field, value) {
    const t = target(row); if (!t) return;
    t.app = t.app || {}; value = (value == null ? '' : String(value)).trim();
    if (DATE_FIELDS.has(field)) { const iso = J.parseDate(value, YEAR); value = iso || value; }
    if (value) t.app[field] = value; else delete t.app[field];
    t.app.updatedAt = J.nowIso(); stamp(t); persist(); render();
  }
  function setManualField(row, field, value) { const t = S.manual[row.key]; if (!t) return; t[field] = (value || '').trim(); stamp(t); persist(); render(); }
  function removeManual(row) { if (!S.manual[row.key]) return; if (!confirm('Remove this row?')) return; delete S.manual[row.key]; persist(); render(); }
  const newId = () => 'm' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  function addManual(company, position, link, appliedOn) {
    const id = newId(); S.manual[id] = stamp({company: (company || '').trim(), position: (position || '').trim(), link: (link || '').trim(), app: {status: 'applied', appliedOn: appliedOn || D.today, updatedAt: J.nowIso()}});
    persist(); render(); return id;
  }

  // ---- hero + stats ----
  function renderStats() {
    const rows = rowsAll(); const st = r => r.app.status || 'applied';
    const n = rows.length, waiting = rows.filter(r => st(r) === 'applied' && !r.get('firstResponse')).length;
    const inter = rows.filter(r => ['screen', 'interview'].includes(st(r))).length, rej = rows.filter(r => ['rejected', 'closed', 'withdrawn'].includes(st(r))).length;
    const offers = rows.filter(r => st(r) === 'offer').length, fu = rows.filter(needsFollowUp).length;
    $('#meta').innerHTML = [n + ' application' + (n === 1 ? '' : 's'), waiting + ' awaiting response', fu + ' to follow up', inter + ' interview' + (inter === 1 ? '' : 's'), rej + ' rejected'].map(esc).join('<span class="sep">·</span>');
    $('#fu-toggle').textContent = 'Needs follow-up' + (fu ? ' · ' + fu : '');
    const stats = [['Applications', n, 'tracked', ''], ['Awaiting', waiting, 'no response yet', waiting ? 'ember' : ''], ['Follow up', fu, fu ? FU_DAYS + '+ days, no reply' : 'nothing overdue', fu ? 'ember' : ''], ['Interviews', inter + offers, offers ? offers + ' offer' + (offers === 1 ? '' : 's') : 'screens + interviews', inter + offers ? 'good' : ''], ['Closed out', rej, 'rejected / closed', '']];
    $('#stats').innerHTML = stats.map(([l, v, s, c]) => `<div class="stat"><div class="label mono">${esc(l)}</div><div class="value ${c}">${esc(v)}</div><div class="sub">${esc(s)}</div></div>`).join('');
  }

  // ---- main table ----
  const state = {sort: 'applied', dir: 'desc', editing: null, fuOnly: false};
  const cmpStr = (a, b) => String(a || '').localeCompare(String(b || ''));
  const SORTS = {
    applied: (a, b) => cmpStr(a.get('appliedOn'), b.get('appliedOn')),
    posted: (a, b) => cmpStr(isIso(a.get('posted')) ? a.get('posted') : '', isIso(b.get('posted')) ? b.get('posted') : ''),
    company: (a, b) => cmpStr(a.company, b.company) || cmpStr(b.get('appliedOn'), a.get('appliedOn')),
    status: (a, b) => (RANK[a.app.status || 'applied'] - RANK[b.app.status || 'applied']) || cmpStr(b.get('appliedOn'), a.get('appliedOn')),
  };
  const DEFAULT_DIR = {applied: 'desc', posted: 'desc', company: 'asc', status: 'asc'};
  function cell(row, f, kind) {  // kind: 'text' | 'date' | 'long'
    const v = row.get(f); const id = `${row.kind}:${row.key}:${f}`;
    if (state.editing === id) {
      const input = kind === 'date' ? `<input type="date" value="${esc(isIso(v) ? v.slice(0, 10) : '')}" data-f="${f}" aria-label="${f}">` :
        kind === 'long' ? `<textarea data-f="${f}" aria-label="${f}">${esc(v)}</textarea>` : `<input type="text" value="${esc(v)}" data-f="${f}" aria-label="${f}">`;
      return `<td class="ed editing" data-f="${f}" data-kind="${kind}">${input}</td>`;
    }
    let shown = kind === 'date' ? esc(fmt(v)) : esc(v); let extra = '';
    if (f === 'appliedOn' && isIso(v)) { const d = -daysTo(v); extra = `<span class="hint">${d === 0 ? 'today' : d === 1 ? '1 day ago' : d + ' days ago'}</span>`; }
    if (f === 'expected' && isIso(v) && daysTo(v) < 0 && !row.get('firstResponse')) shown = `<span class="late" title="Expected response date passed with no reply">${shown}</span>`;
    if (f === 'contacted' && needsFollowUp(row)) { const ap = row.get('appliedOn'); extra = `<button type="button" class="pbtn tiny" data-fu="1" title="Logs today's date here and resets the ${FU_DAYS}-day nudge">Followed up today</button>` + (isIso(ap) ? `<span class="hint">${-daysTo(ap)} days, no reply</span>` : ''); }
    return `<td class="ed" data-f="${f}" data-kind="${kind}" tabindex="0">${shown || '<span class="src">—</span>'}${extra}</td>`;
  }
  function render() {
    renderStats();
    let rows = rowsAll(); if (state.fuOnly) rows = rows.filter(needsFollowUp);
    const sign = state.dir === 'desc' ? -1 : 1; rows.sort((a, b) => sign * SORTS[state.sort](a, b));
    document.querySelectorAll('#apps th.sortable').forEach(th => th.dataset.sort === state.sort ? th.setAttribute('aria-sort', state.dir === 'asc' ? 'ascending' : 'descending') : th.removeAttribute('aria-sort'));
    $('#count').textContent = rows.length + ' row' + (rows.length === 1 ? '' : 's');
    if (!rows.length) { $('#rows').innerHTML = `<tr><td colspan="13" class="empty">${state.fuOnly ? 'Nothing needs a follow-up right now.' : 'Nothing yet. Mark a role applied on the radar, add a row, or paste your sheet under Data.'}</td></tr>`; renderSide(); renderNext(); return; }
    $('#rows').innerHTML = rows.map(r => {
      const st = r.app.status || 'applied';
      const link = r.link ? `<a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(r.position || r.link)}</a>` : esc(r.position);
      const manual = r.kind === 'manual';
      const coCell = manual ? cell(Object.assign({}, r, {get: f => r.company}), 'company', 'text').replace('class="ed"', 'class="ed co"').replace('class="ed editing"', 'class="ed editing co"') : `<td class="co">${esc(r.company)}</td>`;
      const posCell = manual ? cell(Object.assign({}, r, {get: f => r.position}), 'position', 'text').replace('class="ed"', 'class="ed pos"').replace('class="ed editing"', 'class="ed editing pos"') : `<td class="pos">${link}<span class="src">from the radar</span></td>`;
      const sel = `<select class="sel" data-f="status" aria-label="Status">${STATUSES.map(x => `<option value="${x}"${x === st ? ' selected' : ''}>${LABEL[x]}</option>`).join('')}</select>`;
      return `<tr class="st-${esc(st)}${needsFollowUp(r) ? ' fu' : ''}" data-kind="${r.kind}" data-key="${esc(r.key)}">${coCell}${posCell}${cell(r, 'benefits', 'text')}${cell(r, 'appliedOn', 'date')}${cell(r, 'posted', 'date')}${cell(r, 'pay', 'text')}${cell(r, 'expected', 'date')}${cell(r, 'firstResponse', 'date')}${cell(r, 'dates', 'text')}${cell(r, 'contacted', 'text')}<td>${sel}</td>${cell(r, 'notes', 'long')}<td>${manual ? `<button type="button" class="rm" data-rm="1" title="Remove row" aria-label="Remove row">✕</button>` : `<span class="src" title="Un-apply it on the radar to remove this row">radar</span>`}</td></tr>`;
    }).join('');
    if (state.editing) { const el = $('#rows td.editing input, #rows td.editing textarea'); if (el) { el.focus({preventScroll: true}); if (el.select && el.type !== 'date') el.select(); } }
    renderSide(); renderNext();
  }
  // ---- up next: saved radar roles with a deadline (from their snapshots; nothing embedded in the page) ----
  function renderNext() {
    const saved = Object.entries(S.roles).filter(([u, e]) => e.status === 'saved').map(([u, e]) => Object.assign({url: u}, e.snap || {}));
    const dated = saved.filter(r => isIso(r.applyBy) && daysTo(r.applyBy) >= 0).sort((a, b) => cmpStr(a.applyBy, b.applyBy));
    const sec = $('#upnext'); sec.hidden = !saved.length; if (!saved.length) return;
    $('#next-rows').innerHTML = dated.length ? dated.map(r => { const d = daysTo(r.applyBy); const when = d === 0 ? 'today' : d === 1 ? 'tomorrow' : 'in ' + d + ' days';
      return `<tr><td class="co">${esc(r.company || '')}</td><td><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title || r.url)}</a>${r.location ? `<span class="src"> · ${esc(r.location)}</span>` : ''}</td><td class="n"><span class="${d <= 7 ? 'due-soon' : ''}">${esc(fmt(r.applyBy))}</span><span class="hint">${when}</span></td><td>${esc(r.fit || '')}</td></tr>`; }).join('')
      : `<tr><td colspan="4" class="empty">None of your saved roles lists a deadline.</td></tr>`;
    const rest = saved.length - dated.length;
    $('#next-note').innerHTML = (rest ? `${rest} more saved role${rest === 1 ? '' : 's'} without a deadline` : `${saved.length} saved role${saved.length === 1 ? '' : 's'}`) + ' · <a href="index.html">Saved on the radar</a>';
  }
  $('#fu-toggle').addEventListener('click', e => { state.fuOnly = !state.fuOnly; e.currentTarget.setAttribute('aria-pressed', state.fuOnly); e.currentTarget.classList.toggle('on', state.fuOnly); render(); });
  function rowFromEl(el) { const tr = el.closest('tr[data-kind]'); if (!tr) return null; return rowsAll().find(r => r.kind === tr.dataset.kind && r.key === tr.dataset.key) || null; }
  function commit(el) {
    const td = el.closest('td.ed'); const row = rowFromEl(el); if (!td || !row) { state.editing = null; render(); return; }
    const f = td.dataset.f; const v = el.value;
    state.editing = null;
    if (row.kind === 'manual' && (f === 'company' || f === 'position')) setManualField(row, f, v); else setApp(row, f, v);
  }
  $('#rows').addEventListener('click', e => {
    if (e.target.closest('a') || e.target.closest('select') || e.target.closest('input') || e.target.closest('textarea')) return;
    const rm = e.target.closest('button[data-rm]'); if (rm) { const row = rowFromEl(rm); if (row) removeManual(row); return; }
    const fu = e.target.closest('button[data-fu]'); if (fu) { const row = rowFromEl(fu); if (row) markFollowedUp(row); return; }
    const td = e.target.closest('td.ed'); if (!td) return; const row = rowFromEl(td); if (!row) return;
    state.editing = `${row.kind}:${row.key}:${td.dataset.f}`; render();
  });
  $('#rows').addEventListener('keydown', e => {
    if (e.target.matches('td.ed') && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); e.target.click(); return; }
    if (!e.target.matches('input, textarea')) return;
    if (e.key === 'Escape') { state.editing = null; render(); }
    else if (e.key === 'Enter' && !(e.target.matches('textarea') && e.shiftKey) && !e.target.matches('textarea')) { e.preventDefault(); commit(e.target); }
    else if (e.key === 'Enter' && e.target.matches('textarea') && (e.metaKey || e.ctrlKey)) { e.preventDefault(); commit(e.target); }
  });
  $('#rows').addEventListener('focusout', e => { if (e.target.matches('td.editing input, td.editing textarea')) setTimeout(() => { if (state.editing && document.activeElement !== e.target) commit(e.target); }, 0); });
  $('#rows').addEventListener('change', e => { if (e.target.matches('select[data-f="status"]')) { const row = rowFromEl(e.target); if (row) setApp(row, 'status', e.target.value); } });
  document.querySelectorAll('#apps th.sortable').forEach(th => th.addEventListener('click', () => { const k = th.dataset.sort; state.dir = state.sort === k ? (state.dir === 'asc' ? 'desc' : 'asc') : DEFAULT_DIR[k]; state.sort = k; render(); }));

  // ---- add row ----
  $('#add-toggle').addEventListener('click', e => { const o = $('#addform').classList.toggle('open'); e.target.setAttribute('aria-expanded', o); if (o) { $('#add-applied').value = D.today; $('#add-company').focus(); } });
  $('#add-cancel').addEventListener('click', () => { $('#addform').classList.remove('open'); $('#add-toggle').setAttribute('aria-expanded', 'false'); });
  $('#add-save').addEventListener('click', () => {
    const co = $('#add-company').value.trim(), pos = $('#add-position').value.trim(); if (!co && !pos) { alert('Company or position, at least.'); return; }
    addManual(co, pos, $('#add-link').value, $('#add-applied').value); ['add-company', 'add-position', 'add-link'].forEach(id => $('#' + id).value = '');
    $('#addform').classList.remove('open'); $('#add-toggle').setAttribute('aria-expanded', 'false');
  });

  // ---- connections + places (S.tracker) ----
  const side = {editing: null};
  function sideCell(list, i, f, kind) {
    const v = (S.tracker[list][i] || {})[f] || ''; const id = `${list}:${i}:${f}`;
    if (side.editing === id) return `<td class="ed editing" data-list="${list}" data-i="${i}" data-f="${f}">${kind === 'long' ? `<textarea aria-label="${f}">${esc(v)}</textarea>` : `<input type="text" value="${esc(v)}" aria-label="${f}">`}</td>`;
    return `<td class="ed" data-list="${list}" data-i="${i}" data-f="${f}" tabindex="0">${esc(v) || '<span class="src">—</span>'}</td>`;
  }
  function renderSide() {
    const C = S.tracker.connections, P = S.tracker.places;
    $('#conn-rows').innerHTML = C.length ? C.map((c, i) => `<tr>${sideCell('connections', i, 'company', 'text')}${sideCell('connections', i, 'people', 'text')}${sideCell('connections', i, 'advice', 'long')}<td><button type="button" class="rm" data-side-rm="connections" data-i="${i}" aria-label="Remove">✕</button></td></tr>`).join('')
      : `<tr><td colspan="4" class="empty">No connections yet.</td></tr>`;
    $('#place-rows').innerHTML = P.length ? P.map((p, i) => `<tr>${sideCell('places', i, 'place', 'text')}${sideCell('places', i, 'reason', 'long')}<td><button type="button" class="rm" data-side-rm="places" data-i="${i}" aria-label="Remove">✕</button></td></tr>`).join('')
      : `<tr><td colspan="3" class="empty">No places yet.</td></tr>`;
    if (side.editing) { const el = $('.sm-table td.editing input, .sm-table td.editing textarea'); if (el) { el.focus({preventScroll: true}); if (el.select) el.select(); } }
  }
  function sideCommit(el) {
    const td = el.closest('td.ed'); side.editing = null; if (!td) { renderSide(); return; }
    const list = td.dataset.list, i = Number(td.dataset.i), f = td.dataset.f; const item = S.tracker[list][i]; if (!item) { renderSide(); return; }
    item[f] = el.value.trim(); stamp(S.tracker); persist(); renderSide();
  }
  ['#conn', '#places'].forEach(sel => {
    $(sel).addEventListener('click', e => {
      const rm = e.target.closest('button[data-side-rm]'); if (rm) { if (confirm('Remove?')) { S.tracker[rm.dataset.sideRm].splice(Number(rm.dataset.i), 1); stamp(S.tracker); persist(); renderSide(); } return; }
      if (e.target.closest('input, textarea')) return;
      const td = e.target.closest('td.ed'); if (!td) return; side.editing = `${td.dataset.list}:${td.dataset.i}:${td.dataset.f}`; renderSide();
    });
    $(sel).addEventListener('keydown', e => {
      if (e.target.matches('td.ed') && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); e.target.click(); return; }
      if (!e.target.matches('input, textarea')) return;
      if (e.key === 'Escape') { side.editing = null; renderSide(); }
      else if (e.key === 'Enter' && (!e.target.matches('textarea') || e.metaKey || e.ctrlKey)) { e.preventDefault(); sideCommit(e.target); }
    });
    $(sel).addEventListener('focusout', e => { if (e.target.matches('td.editing input, td.editing textarea')) setTimeout(() => { if (side.editing && document.activeElement !== e.target) sideCommit(e.target); }, 0); });
  });
  $('#conn-add').addEventListener('click', () => { S.tracker.connections.push({company: '', people: '', advice: ''}); stamp(S.tracker); persist(); side.editing = `connections:${S.tracker.connections.length - 1}:company`; renderSide(); });
  $('#place-add').addEventListener('click', () => { S.tracker.places.push({place: '', reason: ''}); stamp(S.tracker); persist(); side.editing = `places:${S.tracker.places.length - 1}:place`; renderSide(); });

  // ---- Data panel: CSV export, state export, TSV import, sync ----
  $('#data-toggle').addEventListener('click', e => { const o = $('#datapanel').classList.toggle('open'); e.target.setAttribute('aria-expanded', o); });
  function download(name, text, type) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {type})); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500); }
  $('#export-btn').addEventListener('click', () => download('jadar-state.json', JSON.stringify(S, null, 1), 'application/json'));
  const COLS = [['Company', r => r.company], ['Position', r => r.position], ['Benefits', r => r.get('benefits')], ['Applied', r => r.get('appliedOn')], ['Posted', r => r.get('posted')], ['Pay Range', r => r.get('pay')],
    ['Expected Response', r => r.get('expected')], ['First Response', r => r.get('firstResponse')], ['Dates', r => r.get('dates')], ['Appl. Link', r => r.link], ['Contacted', r => r.get('contacted')], ['Status', r => LABEL[r.app.status || 'applied']], ['Notes', r => r.get('notes')]];
  const csvCell = v => { v = String(v == null ? '' : v); return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  $('#export-csv').addEventListener('click', () => {
    let rows = rowsAll(); rows.sort((a, b) => -SORTS.applied(a, b));
    download('jadar-tracker.csv', [COLS.map(c => c[0]).join(',')].concat(rows.map(r => COLS.map(c => csvCell(c[1](r))).join(','))).join('\r\n'), 'text/csv');
  });
  const HEADERS = {company: 'company', position: 'position', role: 'position', title: 'position', benefits: 'benefits', applied: 'appliedOn', 'applied on': 'appliedOn', 'date applied': 'appliedOn', posted: 'posted', 'pay range': 'pay', pay: 'pay', salary: 'pay',
    'expected response': 'expected', expected: 'expected', 'first response': 'firstResponse', response: 'firstResponse', dates: 'dates', 'appl link': 'link', 'appl. link': 'link', link: 'link', url: 'link', 'application link': 'link', contacted: 'contacted', contact: 'contacted', status: 'status', notes: 'notes', note: 'notes'};
  const ORDER = ['company', 'position', 'benefits', 'appliedOn', 'posted', 'pay', 'expected', 'firstResponse', 'dates', 'link', 'contacted'];
  const normH = h => String(h || '').toLowerCase().replace(/[:.]/g, '').replace(/\s+/g, ' ').trim();
  function parseTsv(text) {
    const lines = text.replace(/\r/g, '').split('\n').filter(l => l.trim()); if (!lines.length) return {rows: [], hasHeader: false};
    const split = l => l.split('\t').map(x => x.trim());
    let cols = ORDER, hasHeader = false; const first = split(lines[0]).map(normH);
    if (first.includes('company') && (first.includes('position') || first.includes('role') || first.includes('title'))) { hasHeader = true; cols = first.map(h => HEADERS[h.replace(/\s*\(.*\)$/, '')] || HEADERS[h] || null); }
    const rows = [];
    lines.slice(hasHeader ? 1 : 0).forEach(l => {
      const cells = split(l); const o = {};
      cells.forEach((v, i) => { const k = cols[i]; if (k && v) o[k] = v; });
      if (!o.company && !o.position) return;
      ['appliedOn', 'posted', 'expected', 'firstResponse'].forEach(k => { if (o[k]) { const iso = J.parseDate(o[k], YEAR); if (iso) o[k] = iso; } });
      if (o.status) { const st = STATUSES.find(x => LABEL[x].toLowerCase() === o.status.toLowerCase() || x === o.status.toLowerCase()); o.status = st || null; if (!o.status) delete o.status; }
      rows.push(o);
    });
    return {rows, hasHeader};
  }
  const normUrl = u => String(u || '').trim().replace(/\/+$/, '');
  function planImport(rows) { const byUrl = Object.keys(S.roles).reduce((m, u) => (m[normUrl(u)] = u, m), {}); return rows.map(o => ({o, attach: o.link ? (byUrl[normUrl(o.link)] || null) : null})); }
  let PREVIEW = null;
  $('#tsv-preview').addEventListener('click', () => {
    const {rows, hasHeader} = parseTsv($('#tsv').value); PREVIEW = planImport(rows);
    const attach = PREVIEW.filter(x => x.attach).length;
    const linked = PREVIEW.filter(x => !x.attach && x.o.link).length;
    $('#tsv-note').textContent = rows.length ? `${rows.length} row${rows.length === 1 ? '' : 's'} found${hasHeader ? ' (header row detected)' : ''}: ${attach} match postings you already acted on, ${rows.length - attach} will be added as your own rows${linked ? ' (' + linked + ' with a link; a link to a live posting joins that posting next time you open the radar)' : ''}.` : 'No rows found. Paste tab-separated rows copied from the sheet.';
    $('#tsv-import').disabled = !rows.length;
  });
  $('#tsv-import').addEventListener('click', () => {
    if (!PREVIEW || !PREVIEW.length) return; const now = J.nowIso(); let n = 0;
    PREVIEW.forEach(({o, attach}) => {
      const app = {}; ['benefits', 'appliedOn', 'posted', 'pay', 'expected', 'firstResponse', 'dates', 'contacted', 'notes'].forEach(k => { if (o[k]) app[k] = o[k]; });
      app.status = o.status || 'applied'; if (!app.appliedOn) app.appliedOn = D.today; app.updatedAt = now;
      if (attach) { const e = S.roles[attach]; e.status = 'applied'; e.at = now; e.app = Object.assign({}, e.app || {}, app); }
      else S.manual[newId()] = {company: o.company || '', position: o.position || '', link: o.link || '', app, at: now};
      n++;
    });
    persist(); render(); PREVIEW = null; $('#tsv').value = ''; $('#tsv-import').disabled = true; $('#tsv-note').textContent = `Imported ${n} row${n === 1 ? '' : 's'}.`;
  });
  J.bindSyncPanel($, sync, () => render());
  render();
  if (J.syncCfg()) sync.syncNow();
})();
</script>
</body>
</html>
"""

DEFAULT_NOTE = ("Hi {first}, I'm a University of Maryland {major} senior (graduating {grad}) and I'm applying to the {title} role at {company}. "
                "I saw you're a fellow Terp there \u2014 would you be open to a 10-minute chat about the team, or to pointing me to the right person? "
                "Happy to send my resume. Thanks so much,\n{signoff}")

def note_template(profile):
    """The default 'Draft note' text, with the profile's major, graduation month and first name baked in."""
    profile = profile or {}
    majors = profile.get("majors") or ["aerospace"]
    major = majors[0] if majors[0].endswith("engineering") else majors[0] + " engineering"
    grad = profile.get("gradDate") or "2027-05"
    try: grad = dt.date(int(grad[:4]), int(grad[5:7]), 1).strftime("%B %Y")
    except Exception: grad = "May 2027"
    signoff = (profile.get("name") or "Kevin").split()[0]
    return DEFAULT_NOTE.replace("{major}", major).replace("{grad}", grad).replace("{signoff}", signoff)

CSS_SHARED = TEMPLATE[TEMPLATE.index(":root {"):TEMPLATE.index("/* table */")] + CSS_SHARED_EXTRA

def build_tracker(profile_name=None, profile=None, today=None):
    """Return the HTML string for tracker.html. It embeds no roles data: rows come from the shared state (applied roles'
    snapshots + manual rows) in the browser / private sync repo."""
    data = dict(today=today or dt.date.today().isoformat(), profileName=profile_name or (profile or {}).get("name"))
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    short = REPO_URL.replace("https://github.com/", "")
    return (TRACKER_TEMPLATE.replace("__CSS_SHARED__", CSS_SHARED).replace("__SHARED_JS__", SHARED_JS).replace("__DATA__", blob)
            .replace("__REPO__", REPO_URL).replace("__REPO_SHORT__", short))

def build(out, src, profile_name=None, profile=None):
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
                rulesVersion=out.get("rulesVersion"), fullRead=out.get("fullRead"), profileName=profile_name or (profile or {}).get("name"),
                noteTemplate=note_template(profile))
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    short = REPO_URL.replace("https://github.com/", "")
    return TEMPLATE.replace("__SHARED_JS__", SHARED_JS).replace("__DATA__", blob).replace("__REPO__", REPO_URL).replace("__REPO_SHORT__", short)

def main():
    data = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
    site = os.environ.get("SITE_DIR", os.path.join(ROOT, "site"))
    with open(os.path.join(data, "radar_out.json")) as f: out = json.load(f)
    with open(os.path.join(ROOT, "sources.json")) as f: src = json.load(f)
    name = None; profile = None
    try:
        prof = os.environ.get("PROFILE") or os.path.join(ROOT, "profiles", f"{out.get('profile', 'kevin')}.json")
        with open(prof) as f: profile = json.load(f)
        name = profile.get("name")
    except Exception: pass
    html = build(out, src, name, profile)
    os.makedirs(site, exist_ok=True)
    with open(os.path.join(site, "index.html"), "w") as f: f.write(html)
    tracker = build_tracker(name, profile, (out.get("scanned") or dt.date.today().isoformat())[:10])
    with open(os.path.join(site, "tracker.html"), "w") as f: f.write(tracker)
    print(f"site/index.html: {len(html) // 1024} KB, {len(out['roles'])} roles; site/tracker.html: {len(tracker) // 1024} KB")

if __name__ == "__main__":
    main()
