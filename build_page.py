#!/usr/bin/env python3
"""radar_out.json + sources.json -> site/index.html: a single self-contained dashboard page (inline CSS/JS, data embedded).

Env: RADAR_DATA (dir holding radar_out.json; default <repo>/data), SITE_DIR (output dir; default <repo>/site),
     PAGE_REPO (repo URL for the footer link)."""
import json, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_dash

ROOT = build_dash.ROOT
REPO_URL = os.environ.get("PAGE_REPO", "https://github.com/TheBurntWaffl3/jadar")

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Job Radar</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --good: #0ca30c; --warn: #fab219; --crit: #d03b3b; --accent: #2a78d6; --accent-ink: #1c5cab;
  --on-good: #ffffff; --on-warn: #0b0b0b; --on-crit: #ffffff;
  --new-wash: rgba(42,120,214,0.10); --fail-wash: rgba(208,59,59,0.08); --gap-wash: rgba(11,11,11,0.04);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
    --accent: #3987e5; --accent-ink: #86b6ef; --on-warn: #0b0b0b;
    --new-wash: rgba(57,135,229,0.16); --fail-wash: rgba(208,59,59,0.16); --gap-wash: rgba(255,255,255,0.04);
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
  --accent: #3987e5; --accent-ink: #86b6ef; --on-warn: #0b0b0b;
  --new-wash: rgba(57,135,229,0.16); --fail-wash: rgba(208,59,59,0.16); --gap-wash: rgba(255,255,255,0.04);
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
body { overflow-x: hidden; }
a { color: var(--accent-ink); }
main { max-width: 1280px; margin: 0 auto; padding: 16px; }
header h1 { font-size: 24px; margin: 0; font-weight: 650; }
header .meta { color: var(--ink-2); font-size: 13px; margin-top: 4px; }
header .meta b { color: var(--ink); font-weight: 600; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 16px 0; }
.tile { background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; padding: 12px 14px; }
.tile .label { font-size: 12.5px; color: var(--ink-2); }
.tile .value { font-size: 32px; font-weight: 600; line-height: 1.15; margin-top: 2px; }
.tile .sub { font-size: 12px; color: var(--muted); }
.tile.good .value { color: var(--good); } .tile.crit .value { color: var(--crit); }
h2 { font-size: 17px; margin: 24px 0 8px; font-weight: 650; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0 10px; }
.seg { display: inline-flex; border: 1px solid var(--axis); border-radius: 6px; overflow: hidden; }
.seg button { background: var(--surface); color: var(--ink); border: 0; padding: 7px 11px; font: inherit; font-size: 13.5px; cursor: pointer; }
.seg button + button { border-left: 1px solid var(--axis); }
.seg button[aria-pressed="true"] { background: var(--accent); color: #fff; }
select, input[type=search] { font: inherit; font-size: 13.5px; padding: 7px 9px; border: 1px solid var(--axis); border-radius: 6px; background: var(--surface); color: var(--ink); min-height: 36px; }
input[type=search] { flex: 1 1 160px; min-width: 140px; }
.count { color: var(--ink-2); font-size: 13px; margin-left: auto; }
.wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th, td { text-align: left; vertical-align: top; padding: 8px 10px; border-top: 1px solid var(--grid); }
th { position: sticky; top: 0; background: var(--surface); color: var(--ink-2); font-weight: 600; font-size: 12.5px; border-top: 0; border-bottom: 1px solid var(--axis); white-space: nowrap; z-index: 1; }
td.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
td.date { white-space: nowrap; }
tr.new { background: var(--new-wash); }
tr.fail { background: var(--fail-wash); } tr.gap { background: var(--gap-wash); color: var(--ink-2); }
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 10px; font-size: 12.5px; font-weight: 600; white-space: nowrap; }
.badge.Yes { background: var(--good); color: var(--on-good); } .badge.Maybe { background: var(--warn); color: var(--on-warn); } .badge.No { background: var(--crit); color: var(--on-crit); }
.badge.ok { background: var(--good); color: #fff; } .badge.failing { background: var(--crit); color: #fff; } .badge.gap { background: var(--axis); color: var(--ink); }
.role a { font-weight: 600; text-decoration: none; } .role a:hover { text-decoration: underline; }
.role .loc, .kind, .sub { color: var(--muted); font-size: 12px; display: block; }
.tag { display: inline-block; font-size: 11px; font-weight: 600; color: var(--accent-ink); border: 1px solid var(--accent-ink); border-radius: 4px; padding: 0 5px; margin-left: 6px; vertical-align: 1px; }
.closing { color: var(--crit); font-weight: 600; font-size: 12px; display: block; }
.why { color: var(--ink-2); font-size: 13px; min-width: 200px; }
.empty { padding: 20px; color: var(--muted); text-align: center; }
.sm { display: none; }
@media (max-width: 640px) { .sm { display: inline; } #roles td.lg { display: none; } }
footer { color: var(--muted); font-size: 12.5px; margin: 28px 0 8px; }
@media (max-width: 640px) {
  .tile .value { font-size: 26px; }
  th, td { padding: 7px 8px; }
  #orgs .hide-sm { display: none; }
  /* roles: one card per posting instead of a sideways-scrolling table */
  #roles, #roles tbody, #roles tr, #roles td { display: block; }
  #roles thead { display: none; }
  #roles tr { padding: 10px 12px; border-top: 1px solid var(--grid); }
  #roles td { padding: 0; border: 0; }
  #roles td.fitco { display: flex; gap: 8px; align-items: center; margin-bottom: 4px; }
  #roles td.fitco .co { font-weight: 600; }
  #roles td.role { margin-bottom: 6px; }
  #roles td.kv { display: inline; font-size: 12.5px; color: var(--ink-2); }
  #roles td.kv:empty { display: none; }
  #roles td.kv + td.kv:not(:empty)::before { content: " · "; color: var(--muted); }
  #roles td.kv .kind { display: inline; } #roles td.kv .kind::before { content: " ("; } #roles td.kv .kind::after { content: ")"; }
  #roles td.kv .closing { display: inline; margin-left: 4px; }
  #roles td.why { display: block; margin-top: 6px; min-width: 0; }
  #roles td.empty { padding: 20px; }
}
</style>
</head>
<body>
<main>
<header>
  <h1>Job Radar <span id="who" style="font-weight:400;color:var(--ink-2)"></span></h1>
  <div class="meta" id="meta"></div>
</header>

<section class="tiles" id="tiles" aria-label="Summary"></section>

<h2>Roles</h2>
<div class="filters" id="filters">
  <div class="seg" role="group" aria-label="Fit">
    <button data-fit="yesmaybe" aria-pressed="true">Yes + Maybe</button>
    <button data-fit="yes" aria-pressed="false">Yes</button>
    <button data-fit="all" aria-pressed="false">All</button>
  </div>
  <select id="sector" aria-label="Sector"><option value="">All sectors</option></select>
  <select id="disc" aria-label="Discipline"><option value="">All fields</option></select>
  <select id="posted" aria-label="Posted within">
    <option value="">Any date</option><option value="7">Posted in last 7 days</option><option value="30">Posted in last 30 days</option>
  </select>
  <input type="search" id="q" placeholder="Search company, title, location, why" aria-label="Search">
  <span class="count" id="count"></span>
</div>
<div class="wrap">
<table id="roles">
  <thead><tr>
    <th>Fit</th><th>Company</th><th>Role</th><th>Field</th><th>Min yrs</th><th>Clearance</th><th>Citizenship</th><th>Date</th><th>Apply by</th><th>Why</th>
  </tr></thead>
  <tbody></tbody>
</table>
</div>

<h2>Organizations <span class="sub" id="orgsum" style="display:inline"></span></h2>
<div class="wrap">
<table id="orgs">
  <thead><tr><th>Organization</th><th class="hide-sm">Sector</th><th>Platform</th><th>Status</th><th>Roles</th><th>Fits</th><th>Notes</th></tr></thead>
  <tbody></tbody>
</table>
</div>

<footer>Read-only scan; never applies to jobs. Source: <a href="__REPO__">__REPO_SHORT__</a>.</footer>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById('data').textContent);
  var roles = D.roles, orgs = D.orgs, newSet = {};
  (D.new || []).forEach(function (u) { newSet[u] = 1; });
  var today = D.today;  // ISO date of the scan; all "N days" math is relative to it
  function days(a, b) { return Math.round((Date.parse(b) - Date.parse(a)) / 86400000); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function fmtDate(d) { if (!d) return ''; var p = d.split('-'); var m = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][+p[1]-1]; return m + ' ' + (+p[2]) + (p[0] !== today.slice(0,4) ? ', ' + p[0] : ''); }
  function isFit(r) { return r.fit === 'Yes' || r.fit === 'Maybe'; }

  // header
  document.getElementById('who').textContent = D.profileName ? '· ' + D.profileName : '';
  var when = D.scanned ? new Date(D.scanned) : null;
  var metaBits = [];
  if (when) metaBits.push('Scanned <b>' + esc(when.toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'})) + '</b>');
  if (D.rulesVersion) metaBits.push('rules ' + esc(D.rulesVersion));
  if (D.fullRead) metaBits.push('<b>full re-read</b> (' + esc(D.fullRead) + ')');
  else metaBits.push('incremental read');
  document.getElementById('meta').innerHTML = metaBits.join(' · ');

  // tiles
  var okOrgs = orgs.filter(function (o) { return o.status === 'OK'; }).length;
  var scanned = orgs.filter(function (o) { return o.status !== 'Not covered yet'; }).length;
  var yes = roles.filter(function (r) { return r.fit === 'Yes'; }).length;
  var maybe = roles.filter(function (r) { return r.fit === 'Maybe'; }).length;
  var recent = roles.filter(function (r) { return isFit(r) && r.dateKind === 'posted' && r.date && days(r.date, today) <= 7; }).length;
  var closing = roles.filter(function (r) { return isFit(r) && r.applyBy && days(today, r.applyBy) >= 0 && days(today, r.applyBy) <= 14; }).length;
  var tiles = [
    ['Yes', yes, 'strong fits', 'good'], ['Maybe', maybe, 'worth a look', ''],
    ['Fits posted in last 7 days', recent, 'Yes + Maybe', ''], ['Fits closing in 14 days', closing, 'apply-by known', closing ? 'crit' : ''],
    ['Roles read', roles.length, 'in-field, US', ''], ['Orgs read', okOrgs + ' / ' + scanned, (scanned - okOrgs) + ' failing', '']
  ];
  document.getElementById('tiles').innerHTML = tiles.map(function (t) {
    return '<div class="tile ' + t[3] + '"><div class="label">' + esc(t[0]) + '</div><div class="value">' + esc(t[1]) + '</div><div class="sub">' + esc(t[2]) + '</div></div>';
  }).join('');

  // filters
  var state = { fit: 'yesmaybe', sector: '', disc: '', posted: '', q: '' };
  function fill(sel, values) { values.forEach(function (v) { var o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o); }); }
  fill(document.getElementById('sector'), Array.from(new Set(roles.map(function (r) { return r.sector; }))).sort());
  fill(document.getElementById('disc'), Array.from(new Set(roles.map(function (r) { return r.discipline; }))).sort());
  document.querySelectorAll('.seg button').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.seg button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      state.fit = b.getAttribute('data-fit'); render();
    });
  });
  ['sector', 'disc', 'posted'].forEach(function (k) { document.getElementById(k).addEventListener('change', function (e) { state[k] = e.target.value; render(); }); });
  document.getElementById('q').addEventListener('input', function (e) { state.q = e.target.value.trim().toLowerCase(); render(); });

  var mq = window.matchMedia('(max-width: 640px)'); function sm() { return mq.matches; }
  (mq.addEventListener ? mq.addEventListener('change', function () { render(); }) : mq.addListener(function () { render(); }));
  var rank = { Yes: 0, Maybe: 1, No: 2 };
  function matches(r) {
    if (state.fit === 'yes' && r.fit !== 'Yes') return false;
    if (state.fit === 'yesmaybe' && !isFit(r)) return false;
    if (state.sector && r.sector !== state.sector) return false;
    if (state.disc && r.discipline !== state.disc) return false;
    if (state.posted && !(r.dateKind === 'posted' && r.date && days(r.date, today) <= +state.posted)) return false;
    if (state.q) { var hay = [r.company, r.title, r.location, r.why].join(' ').toLowerCase(); if (hay.indexOf(state.q) < 0) return false; }
    return true;
  }
  function kindLabel(k) { return k === 'posted' ? 'posted' : k === 'on or before' ? 'on or before' : k === 'refreshed' ? 'refreshed' : k === 'first seen' ? 'first seen' : (k || ''); }
  function row(r) {
    var isNew = newSet[r.url] ? '<span class="tag">New</span>' : '';
    var apply = '';
    if (r.applyBy) {
      var n = days(today, r.applyBy);
      apply = esc(fmtDate(r.applyBy)) + (n >= 0 && n <= 10 ? '<span class="closing">closes in ' + n + ' day' + (n === 1 ? '' : 's') + '</span>' : '');
    }
    var badge = '<span class="badge ' + r.fit + '">' + (r.fit === 'Yes' ? '✓ ' : r.fit === 'Maybe' ? '? ' : '✕ ') + r.fit + '</span>';
    return '<tr' + (newSet[r.url] ? ' class="new"' : '') + '>' +
      '<td class="fitco">' + badge + '<span class="co sm">' + esc(r.company) + '</span></td>' +
      '<td class="lg">' + esc(r.company) + '</td>' +
      '<td class="role"><a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.title) + '</a>' + isNew + '<span class="loc">' + esc(r.location) + '</span></td>' +
      '<td class="kv">' + esc(r.discipline) + '</td>' +
      '<td class="kv num">' + (r.minYears == null ? (sm() ? '' : '–') : (sm() ? esc(r.minYears) + ' yrs min' : esc(r.minYears))) + '</td>' +
      '<td class="kv">' + esc(r.clearance || '') + '</td>' +
      '<td class="kv">' + esc(r.citizenship || '') + '</td>' +
      '<td class="kv date">' + esc(fmtDate(r.date)) + '<span class="kind">' + esc(kindLabel(r.dateKind)) + '</span></td>' +
      '<td class="kv date">' + (apply ? (sm() ? 'apply by ' : '') + apply : '') + '</td>' +
      '<td class="why">' + esc(r.why) + '</td></tr>';
  }
  function render() {
    var shown = roles.filter(matches).sort(function (a, b) { return (rank[a.fit] - rank[b.fit]) || ((b.date || '') < (a.date || '') ? -1 : (b.date || '') > (a.date || '') ? 1 : 0); });
    document.querySelector('#roles tbody').innerHTML = shown.length ? shown.map(row).join('') : '<tr><td colspan="10" class="empty">No roles match these filters.</td></tr>';
    document.getElementById('count').textContent = shown.length + ' of ' + roles.length + ' roles';
  }
  render();

  // organizations
  var order = { Failing: 0, OK: 1, 'Not covered yet': 2 };
  var olist = orgs.slice().sort(function (a, b) { return (order[a.status] - order[b.status]) || a.org.localeCompare(b.org); });
  document.querySelector('#orgs tbody').innerHTML = olist.map(function (o) {
    var cls = o.status === 'OK' ? 'ok' : o.status === 'Failing' ? 'failing' : 'gap';
    var icon = o.status === 'OK' ? '✓ ' : o.status === 'Failing' ? '✕ ' : '– ';
    return '<tr class="' + (cls === 'ok' ? '' : cls === 'failing' ? 'fail' : 'gap') + '"><td>' + esc(o.org) + '</td><td class="hide-sm">' + esc(o.sector) + '</td><td>' + esc(o.platform) + '</td>' +
      '<td><span class="badge ' + cls + '">' + icon + esc(o.status) + '</span></td><td class="num">' + (o.roles == null ? '–' : o.roles) + '</td><td class="num">' + (o.fits == null ? '–' : o.fits) + '</td><td class="why">' + esc(o.note || '') + '</td></tr>';
  }).join('');
  var failing = orgs.filter(function (o) { return o.status === 'Failing'; }).length, gaps = orgs.length - scanned;
  document.getElementById('orgsum').textContent = okOrgs + ' OK · ' + failing + ' failing · ' + gaps + ' not covered yet';
})();
</script>
</body>
</html>
"""

def build(out, src, profile_name=None):
    """Return the HTML string for a radar_out.json dict and sources.json list."""
    roles, orgs = build_dash.datasets(out, src)
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
