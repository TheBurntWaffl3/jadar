#!/usr/bin/env python3
"""radar_out.json + history.json + calendar.json -> site/calendar.html: when each organization opens entry-level roles.

Observed postings: every Yes/Maybe posting the radar has listed (history.json on the data branch, never pruned, plus
today's radar_out.json), filtered to entry-level titles, bucketed by posting month into hiring cycles (June to May,
named for the graduating class). Curated prior-cycle examples and the pattern each organization follows come from
calendar.json in the repo.

Env: RADAR_DATA (dir holding radar_out.json and history.json; default <repo>/data), SITE_DIR (default <repo>/site),
     PAGE_REPO (repo URL for the footer link)."""
import json, os, re, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_URL = os.environ.get("PAGE_REPO", "https://github.com/TheBurntWaffl3/jadar")
CLASS_YEAR = re.compile(r"\b20[2-3]\d\b|'\d\d\b")
KEYS = ("company", "title", "location", "fit", "date", "dateKind", "firstSeen", "lastSeen", "url", "gradReq", "startWindow")


def is_entry(r):
    """Entry-level posting: a Yes (the fit rules already require that), or a Maybe whose title says so."""
    if r.get("fit") == "Yes": return True
    if r.get("fit") != "Maybe": return False
    t = r.get("title") or ""
    return bool(scan.TITLE_ENTRY.search(t) or CLASS_YEAR.search(t))


def cycle_of(date):
    """Hiring cycle a date belongs to, named for the class it hires: June 2026 .. May 2027 -> 2027."""
    y, m = int(date[:4]), int(date[5:7])
    return y + 1 if m >= 6 else y


def postings(out, history):
    """Merge history and today's roles (today wins), keep entry-level ones, trim to the keys the page needs."""
    merged = dict(history.get("postings", {}))
    for r in out.get("roles", []):
        e = dict(merged.get(r["url"], {})); e.update({k: r.get(k) for k in KEYS if r.get(k) is not None}); e["url"] = r["url"]
        e.setdefault("lastSeen", (out.get("scanned") or "")[:10] or None)
        merged[r["url"]] = e
    rows = []
    for u, e in merged.items():
        e = dict(e); e["url"] = u
        if not is_entry(e): continue
        when = e.get("date") if e.get("dateKind") == "posted" else None
        e["month"] = when[:7] if when else None            # chart bucket: posted dates only
        e["cycle"] = cycle_of(when or e.get("firstSeen") or e.get("lastSeen") or "2026-11-12")
        rows.append({k: e.get(k) for k in KEYS + ("month", "cycle") if e.get(k) is not None})
    rows.sort(key=lambda r: (r.get("date") or r.get("firstSeen") or ""), reverse=True)
    return rows


def build(out, history, cal, profile=None):
    rows = postings(out, history)
    today = (out.get("scanned") or dt.date.today().isoformat())[:10]
    grad = (profile or {}).get("gradDate") or ""
    data = dict(today=today, scanned=out.get("scanned"), rows=rows, patterns=cal.get("patterns", []), orgs=cal.get("orgs", []),
                classYear=int(grad[:4]) if grad[:4].isdigit() else cycle_of(today), profileName=(profile or {}).get("name"),
                historySince=min([r.get("firstSeen") or today for r in rows] or [today]))
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    short = REPO_URL.replace("https://github.com/", "")
    return TEMPLATE.replace("__DATA__", blob).replace("__REPO__", REPO_URL).replace("__REPO_SHORT__", short)


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Hiring Calendar</title>
<meta name="description" content="When each organization opens entry-level engineering roles: posting months by hiring cycle, with past examples.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&display=swap">
<style>
:root {
  color-scheme: light;
  --page: #ffffff; --ink: #0b0b0c; --ink-2: #3f3f44; --muted: #737379; --line: #ececee; --card: #f7f7f8; --pill: #f4f4f5;
  --hero: #0b0b0c; --on-hero: #ffffff; --hero-muted: #9a9aa0;
  --ember: #2f5bea; --tint: #eaf0ff; --on-ember: #ffffff; --good: #0ca30c;
  --c1: #dce5fc; --c2: #b3c5f7; --c3: #7d9cf1; --c4: #2f5bea; --c5: #1c3fb3;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0b0b0c; --ink: #ececee; --ink-2: #c6c6cb; --muted: #8a8a90; --line: #232326; --card: #141416; --pill: #1b1b1e;
    --hero: #15151a; --on-hero: #ffffff; --hero-muted: #8a8a90; --ember: #5b82ff; --tint: #121a33; --on-ember: #ffffff; --good: #2bbf2b;
    --c1: #1a2440; --c2: #243a73; --c3: #3356b5; --c4: #5b82ff; --c5: #8eaaff;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0b0b0c; --ink: #ececee; --ink-2: #c6c6cb; --muted: #8a8a90; --line: #232326; --card: #141416; --pill: #1b1b1e;
  --hero: #15151a; --on-hero: #ffffff; --hero-muted: #8a8a90; --ember: #5b82ff; --tint: #121a33; --on-ember: #ffffff; --good: #2bbf2b;
  --c1: #1a2440; --c2: #243a73; --c3: #3356b5; --c4: #5b82ff; --c5: #8eaaff;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.45 "Inter Tight", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }
body { overflow-x: hidden; -webkit-font-smoothing: antialiased; }
a { color: inherit; }
main { max-width: 1180px; margin: 0 auto; padding: 16px; }
.mono { font-family: ui-monospace, Menlo, Consolas, "SF Mono", monospace; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }

.hero { background: var(--hero); color: var(--on-hero); border: 1px solid var(--line); border-radius: 24px; padding: 36px 28px 28px; margin-top: 8px; }
.hero h1 { font-size: clamp(36px, 6vw, 60px); line-height: 1; letter-spacing: -0.035em; font-weight: 600; margin: 0 0 18px; max-width: 14ch; }
.hero .meta { opacity: .92; }
.hero .meta .sep { opacity: .55; margin: 0 .35em; }
.hero .nav { margin-top: 18px; font-size: 14px; } .hero .nav a { color: var(--on-hero); opacity: .85; text-decoration: none; border-bottom: 1px solid var(--hero-muted); padding-bottom: 1px; } .hero .nav a:hover { opacity: 1; }

h2 { font-size: 28px; letter-spacing: -0.03em; font-weight: 600; margin: 38px 0 6px; }
h2 + .lede { color: var(--muted); margin: 0 0 16px; max-width: 70ch; }
p.body { max-width: 70ch; color: var(--ink-2); }

/* patterns */
.patterns { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.pat { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px; min-width: 0; }
.pat h3 { margin: 0 0 8px; font-size: 18px; letter-spacing: -0.02em; }
.pat p { margin: 0 0 10px; color: var(--ink-2); font-size: 14px; }
.pat .advice { color: var(--ink); font-weight: 500; }
.pat .orgs { color: var(--muted); font-size: 13px; }

/* controls */
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 12px; }
.seg { display: inline-flex; background: var(--pill); border-radius: 999px; padding: 3px; }
.seg button { background: transparent; color: var(--ink); border: 0; padding: 7px 14px; font: inherit; font-size: 13.5px; font-weight: 500; border-radius: 999px; cursor: pointer; min-height: 32px; }
.seg button[aria-pressed="true"] { background: var(--ink); color: var(--page); }
.count { color: var(--muted); margin-left: auto; white-space: nowrap; }

/* heat grid */
.gridwrap { overflow-x: auto; border-top: 1px solid var(--line); -webkit-overflow-scrolling: touch; }
table.heat { border-collapse: separate; border-spacing: 0; width: 100%; min-width: 760px; font-size: 13.5px; }
.heat th, .heat td { padding: 0; border-bottom: 1px solid var(--line); }
.heat th { color: var(--muted); font-weight: 500; text-align: center; padding: 10px 2px 8px; white-space: nowrap; }
.heat th.org, .heat td.org { text-align: left; position: sticky; left: 0; background: var(--page); padding: 0 10px 0 0; min-width: 170px; max-width: 220px; font-weight: 500; z-index: 1; }
.heat th.org { font-weight: 500; }
.heat td.org .n { color: var(--muted); font-weight: 400; font-size: 12.5px; margin-left: 6px; }
.heat th.now { color: var(--ink); }
.heat td.cell { text-align: center; vertical-align: middle; height: 38px; }
.cell button { width: calc(100% - 2px); height: 34px; margin: 2px 1px; border: 0; border-radius: 6px; background: transparent; color: var(--ink); font: inherit; font-size: 13px; font-variant-numeric: tabular-nums; cursor: default; }
.cell button[data-n] { cursor: pointer; }
.cell button.l1 { background: var(--c1); } .cell button.l2 { background: var(--c2); } .cell button.l3 { background: var(--c3); color: var(--on-ember); }
.cell button.l4 { background: var(--c4); color: var(--on-ember); } .cell button.l5 { background: var(--c5); color: var(--on-ember); }
:root[data-theme="dark"] .cell button.l5, :root:not([data-theme="light"]) .cell button.l5 { color: var(--ink); }
@media (prefers-color-scheme: light) { :root:not([data-theme="dark"]) .cell button.l5 { color: var(--on-ember); } }
.cell button[aria-pressed="true"] { outline: 2px solid var(--ink); outline-offset: -2px; }
.cell button:hover[data-n] { filter: brightness(1.06); }
.heat tr.total td { font-weight: 600; } .heat tr.total td.org { font-weight: 600; }
.legend { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 13px; margin: 12px 0 0; flex-wrap: wrap; }
.legend .sw { display: inline-flex; gap: 2px; } .legend .sw i { width: 22px; height: 12px; border-radius: 3px; display: inline-block; }
.legend .sw i:nth-child(1) { background: var(--c1); } .legend .sw i:nth-child(2) { background: var(--c2); } .legend .sw i:nth-child(3) { background: var(--c3); } .legend .sw i:nth-child(4) { background: var(--c4); } .legend .sw i:nth-child(5) { background: var(--c5); }

/* cell detail */
.picked { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 14px 18px; margin-top: 14px; }
.picked h3 { margin: 0 0 8px; font-size: 16px; letter-spacing: -0.01em; }
.picked ul { margin: 0; padding: 0; list-style: none; }
.picked li { padding: 7px 0; border-top: 1px solid var(--line); font-size: 14px; }
.picked li:first-child { border-top: 0; }
.picked li a { font-weight: 600; text-decoration: none; } .picked li a:hover { text-decoration: underline; }
.picked li .sub { color: var(--muted); font-size: 13px; margin-left: 6px; }

/* org cards */
.orgcards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.org { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px; min-width: 0; }
.org li a, .picked li a, .org li .note { overflow-wrap: anywhere; }
.org h3 { margin: 0 0 6px; font-size: 20px; letter-spacing: -0.02em; display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.tag { display: inline-block; font-size: 11.5px; font-weight: 600; border-radius: 999px; padding: 2px 8px; background: var(--pill); color: var(--ink-2); white-space: nowrap; }
.tag.pool { background: var(--tint); color: var(--ember); }
.org .window { color: var(--ink); font-size: 14px; margin: 6px 0; }
.org .notes { color: var(--ink-2); font-size: 13.5px; margin: 0 0 8px; }
.org h4 { margin: 12px 0 4px; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.org ul { margin: 0; padding: 0; list-style: none; }
.org li { font-size: 13.5px; padding: 5px 0; border-top: 1px solid var(--line); }
.org li:first-child { border-top: 0; }
.org li a { text-decoration: none; font-weight: 500; } .org li a:hover { text-decoration: underline; }
.org li .d { color: var(--muted); font-variant-numeric: tabular-nums; }
.org li .note { display: block; color: var(--ink-2); font-size: 13px; }
.org .more { color: var(--muted); font-size: 13px; padding-top: 6px; }
.org .strip { display: flex; gap: 2px; margin: 8px 0 2px; }
.org .strip i { flex: 1; height: 8px; border-radius: 2px; background: var(--line); }
.org .strip i.l1 { background: var(--c1); } .org .strip i.l2 { background: var(--c2); } .org .strip i.l3 { background: var(--c3); } .org .strip i.l4 { background: var(--c4); } .org .strip i.l5 { background: var(--c5); }
.org .striplab { display: flex; justify-content: space-between; color: var(--muted); font-size: 11px; }

.method { color: var(--ink-2); font-size: 14px; max-width: 76ch; }
.method li { margin: 4px 0; }
footer { color: var(--muted); font-size: 13px; margin: 36px 0 12px; }
footer a { color: var(--ink); }

@media (max-width: 760px) {
  main { padding: 12px 16px; }
  .hero { padding: 28px 20px 22px; border-radius: 20px; }
  .patterns, .orgcards { grid-template-columns: 1fr; }
  .heat th.org, .heat td.org { min-width: 130px; max-width: 150px; font-size: 13px; }
  .count { margin-left: 0; width: 100%; white-space: normal; }
}
</style>
</head>
<body>
<main>
<section class="hero">
  <h1>When entry-level roles open.</h1>
  <div class="meta mono" id="meta"></div>
  <nav class="nav"><a href="index.html">← Job radar</a></nav>
</section>

<h2>Four ways companies hire new grads.</h2>
<p class="lede">The posting month tells you what kind of requisition you are looking at. These are the patterns in the boards the radar reads.</p>
<section class="patterns" id="patterns"></section>

<h2>Entry-level postings by month.</h2>
<p class="lede">Each cell counts entry-level requisitions first posted that month. A hiring cycle runs June to May and is named for the class it hires. Click a cell to list the postings.</p>
<div class="controls">
  <div class="seg" role="group" aria-label="Hiring cycle" id="cycles"></div>
  <div class="seg" role="group" aria-label="Rows" id="rowsel">
    <button type="button" data-rows="top" aria-pressed="true">Busiest 25</button>
    <button type="button" data-rows="all" aria-pressed="false">All organizations</button>
  </div>
  <span class="count mono" id="count"></span>
</div>
<div class="gridwrap"><table class="heat" id="heat"></table></div>
<div class="legend"><span>Postings per month</span><span class="sw"><i></i><i></i><i></i><i></i><i></i></span><span>1 · 2 · 3–4 · 5–8 · 9+</span><span id="excluded"></span></div>
<div class="picked" id="picked" hidden></div>

<h2>Organization by organization.</h2>
<p class="lede">What each board does, what the radar has seen this cycle, and checked examples from earlier cycles with the page each was read from.</p>
<section class="orgcards" id="orgs"></section>

<h2>How to read this.</h2>
<ul class="method" id="method"></ul>

<footer>Built from the radar's daily scan and <code>calendar.json</code>. <a href="__REPO__">__REPO_SHORT__</a> · <a href="index.html">Job radar</a></footer>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const MONTHS = ['Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May'];
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = d => { if (!d) return ''; const [y,m,dd] = d.split('-'); return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][+m-1] + ' ' + (+dd) + ', ' + y; };
  const monthKey = (cycle, i) => { const m = (5 + i) % 12 + 1, y = m >= 6 ? cycle - 1 : cycle; return y + '-' + String(m).padStart(2, '0'); };
  const level = n => n <= 0 ? '' : n === 1 ? 'l1' : n === 2 ? 'l2' : n <= 4 ? 'l3' : n <= 8 ? 'l4' : 'l5';
  const thisMonth = D.today.slice(0, 7);
  const pat = Object.fromEntries(D.patterns.map(p => [p.id, p]));
  const cur = Object.fromEntries(D.orgs.map(o => [o.org, o]));

  document.getElementById('meta').innerHTML = 'Hiring calendar<span class="sep">·</span>class of ' + D.classYear +
    (D.profileName ? '<span class="sep">·</span>' + esc(D.profileName) : '') + '<span class="sep">·</span>updated ' + fmt(D.today);

  // patterns
  document.getElementById('patterns').innerHTML = D.patterns.map(p => {
    const orgs = D.orgs.filter(o => o.pattern === p.id).map(o => o.org);
    return '<article class="pat"><h3>' + esc(p.name) + '</h3><p>' + esc(p.summary) + '</p><p class="advice">' + esc(p.advice) + '</p>' +
      (orgs.length ? '<div class="orgs">' + esc(orgs.join(' · ')) + '</div>' : '') + '</article>';
  }).join('');

  // cycles present (posted-dated rows only drive the grid; the rest are listed in cards)
  const dated = D.rows.filter(r => r.month);
  const cycles = [...new Set(dated.map(r => r.cycle))].sort((a, b) => b - a);
  if (!cycles.length) cycles.push(D.classYear);
  let cycle = cycles.includes(D.classYear) ? D.classYear : cycles[0], rowsMode = 'top', picked = null;
  document.getElementById('cycles').innerHTML = cycles.map(c => '<button type="button" data-cycle="' + c + '" aria-pressed="' + (c === cycle) + '">Class of ' + c + '</button>').join('');
  document.getElementById('cycles').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; cycle = +b.dataset.cycle; picked = null; render(); });
  document.getElementById('rowsel').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; rowsMode = b.dataset.rows; render(); });

  function render() {
    document.querySelectorAll('#cycles button').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.cycle === cycle)));
    document.querySelectorAll('#rowsel button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.rows === rowsMode)));
    const rows = dated.filter(r => r.cycle === cycle);
    const byOrg = {};
    rows.forEach(r => { (byOrg[r.company] = byOrg[r.company] || []).push(r); });
    let orgs = Object.keys(byOrg).sort((a, b) => byOrg[b].length - byOrg[a].length || a.localeCompare(b));
    if (rowsMode === 'top') orgs = orgs.slice(0, 25);
    const keys = MONTHS.map((_, i) => monthKey(cycle, i));
    const head = '<thead><tr><th class="org">Organization</th>' + MONTHS.map((m, i) => '<th class="' + (keys[i] === thisMonth ? 'now' : '') + (keys[i] > thisMonth ? ' future' : '') + '">' + m + '<br><span class="mono" style="letter-spacing:0;text-transform:none;font-size:10.5px">' + keys[i].slice(2, 4) + '</span></th>').join('') + '</tr></thead>';
    const cellFor = (org, i, list) => {
      const n = list.length, key = org + '|' + keys[i];
      const future = keys[i] > thisMonth;
      return '<td class="cell">' + (n ? '<button type="button" class="' + level(n) + '" data-n="' + n + '" data-key="' + esc(key) + '" aria-pressed="' + (picked === key) + '" title="' + n + ' posting' + (n > 1 ? 's' : '') + ' · click to list">' + n + '</button>' : (future ? '<button type="button" tabindex="-1" aria-hidden="true" style="color:var(--line)">·</button>' : '<button type="button" tabindex="-1" aria-hidden="true"></button>')) + '</td>';
    };
    const totalRow = '<tr class="total"><td class="org">All organizations<span class="n">' + rows.length + '</span></td>' + keys.map((k, i) => cellFor('*', i, rows.filter(r => r.month === k))).join('') + '</tr>';
    const body = orgs.map(o => '<tr><td class="org" title="' + esc(o) + '">' + esc(o) + '<span class="n">' + byOrg[o].length + '</span></td>' + keys.map((k, i) => cellFor(o, i, byOrg[o].filter(r => r.month === k))).join('') + '</tr>').join('');
    document.getElementById('heat').innerHTML = head + '<tbody>' + totalRow + body + '</tbody>';
    document.getElementById('count').textContent = rows.length + ' dated entry-level postings · ' + Object.keys(byOrg).length + ' organizations · class of ' + cycle;
    const undated = D.rows.filter(r => !r.month && r.cycle === cycle).length;
    document.getElementById('excluded').textContent = undated ? '· ' + undated + ' postings without a posted date are listed in the cards only' : '';
    const pk = document.getElementById('picked');
    if (picked) {
      const [org, key] = picked.split('|');
      const list = rows.filter(r => r.month === key && (org === '*' || r.company === org)).sort((a, b) => (b.date || '').localeCompare(a.date || ''));
      if (!list.length) { picked = null; pk.hidden = true; }
      else {
        const [y, m] = key.split('-');
        pk.hidden = false;
        pk.innerHTML = '<h3>' + (org === '*' ? 'All organizations' : esc(org)) + ' · ' + ['January','February','March','April','May','June','July','August','September','October','November','December'][+m - 1] + ' ' + y + ' · ' + list.length + ' posting' + (list.length > 1 ? 's' : '') + '</h3><ul>' +
          list.map(r => '<li><a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.title) + '</a><span class="sub">' + esc([org === '*' ? r.company : '', r.location || '', 'posted ' + fmt(r.date)].filter(Boolean).join(' · ')) + (r.lastSeen && r.lastSeen < D.today ? ' · last seen ' + fmt(r.lastSeen) : '') + '</span></li>').join('') + '</ul>';
      }
    } else pk.hidden = true;
  }
  document.getElementById('heat').addEventListener('click', e => { const b = e.target.closest('button[data-key]'); if (!b) return; picked = picked === b.dataset.key ? null : b.dataset.key; render(); if (picked) document.getElementById('picked').scrollIntoView({ block: 'nearest', behavior: 'smooth' }); });

  // org cards: curated orgs first (ordered by what the radar saw this class year), then every other org with observed postings
  const seen = {};
  D.rows.forEach(r => { (seen[r.company] = seen[r.company] || []).push(r); });
  const curated = D.orgs.map(o => o.org);
  const others = Object.keys(seen).filter(o => !curated.includes(o)).sort((a, b) => seen[b].length - seen[a].length || a.localeCompare(b));
  const order = [...curated.sort((a, b) => ((seen[b] || []).length - (seen[a] || []).length) || a.localeCompare(b)), ...others];
  const card = org => {
    const c = cur[org] || {};
    const obs = (seen[org] || []).filter(r => r.cycle === D.classYear);
    const strip = MONTHS.map((_, i) => obs.filter(r => r.month === monthKey(D.classYear, i)).length);
    const li = r => '<li><a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.title) + '</a> <span class="d">' + (r.month ? 'posted ' + fmt(r.date) : (r.dateKind ? esc(r.dateKind) + ' ' + fmt(r.date) : 'first seen ' + fmt(r.firstSeen))) + (r.lastSeen && r.lastSeen < D.today ? ' · closed by ' + fmt(r.lastSeen) : '') + '</span>' + (r.gradReq ? '<span class="note">' + esc(r.gradReq) + '</span>' : '') + '</li>';
    const ex = (c.examples || []).map(e => '<li>' + (e.source ? '<a href="' + esc(e.source) + '" target="_blank" rel="noopener">' + esc(e.title) + '</a>' : esc(e.title)) + ' <span class="d">' + esc([e.location || '', e.posted ? 'posted ' + fmt(e.posted) : ''].filter(Boolean).join(' · ')) + (e.closed ? ' · closed ' + fmt(e.closed) : '') + (e.cycle ? ' · class of ' + e.cycle : '') + '</span>' + (e.note ? '<span class="note">' + esc(e.note) + '</span>' : '') + '</li>').join('');
    const p = pat[c.pattern];
    const shown = obs.slice(0, 6);
    return '<article class="org" id="org-' + esc(org.replace(/\W+/g, '-')) + '"><h3>' + esc(org) + (p ? '<span class="tag ' + esc(c.pattern) + '">' + esc(p.name) + '</span>' : '') + '</h3>' +
      (c.window ? '<p class="window">' + esc(c.window) + '</p>' : '<p class="window">No curated notes yet; the observed postings below are what the radar has seen.</p>') +
      (c.notes ? '<p class="notes">' + esc(c.notes) + '</p>' : '') +
      (obs.length ? '<div class="strip">' + strip.map(n => '<i class="' + level(n) + '" title="' + n + '"></i>').join('') + '</div><div class="striplab"><span>Jun ' + (D.classYear - 1) + '</span><span>May ' + D.classYear + '</span></div>' : '') +
      '<h4>Seen this cycle (class of ' + D.classYear + ') · ' + obs.length + '</h4>' + (obs.length ? '<ul>' + shown.map(li).join('') + '</ul>' + (obs.length > shown.length ? '<div class="more">+ ' + (obs.length - shown.length) + ' more on the <a href="index.html">radar</a></div>' : '') : '<div class="more">Nothing yet this cycle.</div>') +
      (ex ? '<h4>Earlier cycles, checked examples</h4><ul>' + ex + '</ul>' : '') + '</article>';
  };
  document.getElementById('orgs').innerHTML = order.map(card).join('');

  document.getElementById('method').innerHTML = [
    'An entry-level posting here is one the radar rated Yes, or Maybe with a new-grad, entry-level, Engineer I, Associate or class-year title.',
    'The grid uses the date the board itself says a posting went up. Boards that re-date their postings daily (for example Aerospace Corp) or import in bulk have no trustworthy posted date, so their postings appear only in the organization cards, by the day the radar first saw them.',
    'Observed postings accumulate from ' + fmt(D.historySince) + ', when the radar started keeping history. Each year adds a cycle to compare; the earlier-cycle examples in the cards were checked by hand against public pages, mostly job aggregators, whose dates can be a few days off.',
    'A cycle runs June through May and is named for the class it hires, so a "class of 2027" posting in September 2026 is one that a May 2027 graduate can take.'
  ].map(s => '<li>' + s + '</li>').join('');

  render();
})();
</script>
</body>
</html>
"""


def main():
    data = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
    site = os.environ.get("SITE_DIR", os.path.join(ROOT, "site"))
    with open(os.path.join(data, "radar_out.json")) as f: out = json.load(f)
    try:
        with open(os.path.join(data, "history.json")) as f: history = json.load(f)
    except Exception: history = {"postings": {}}
    with open(os.path.join(ROOT, "calendar.json")) as f: cal = json.load(f)
    profile = None
    try:
        with open(os.environ.get("PROFILE") or os.path.join(ROOT, "profiles", f"{out.get('profile', 'kevin')}.json")) as f: profile = json.load(f)
    except Exception: pass
    html = build(out, history, cal, profile)
    os.makedirs(site, exist_ok=True)
    with open(os.path.join(site, "calendar.html"), "w") as f: f.write(html)
    print(f"site/calendar.html: {len(html) // 1024} KB, {len(postings(out, history))} entry-level postings")


if __name__ == "__main__":
    main()
