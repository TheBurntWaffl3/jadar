#!/usr/bin/env python3
"""Board discovery: find job boards jadar does not scan yet (Kevin, 2026-11-25, after Cowboy Space was found missing:
"what else are we missing?"). Google (SerpApi/Serper, same keys as finder.py) is asked for job pages on the big ATS domains
with field words ("site:jobs.ashbyhq.com propulsion engineer"); every board id in the result links that is not in
sources.json is a candidate. Greenhouse/Lever/Ashby candidates are probed through their public APIs (the only hosts this
module ever fetches besides the search provider) for the job count and a few in-field titles. Candidates go to
data/discover.json (`new` until added to sources.json or listed in discover_ignore.txt). The morning audit reviews them.
Read-only: nothing is ever fetched from a job site's HTML. Query budget: QUERIES_PER_RUN per run, rotating through QUERIES.
"""
import json, os, re, sys, datetime as dt, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("RADAR_DATA") or ROOT
QUERIES_PER_RUN = int(os.environ.get("DISCOVER_MAX") or 15)
FIELDS = ["propulsion engineer", "thermal engineer", "structures engineer", "aerospace engineer", "test engineer",
          "mechanical engineer new grad", "GNC engineer", "nuclear engineer", "naval architect", "aerodynamics engineer",
          "systems engineer early career 2027"]
SITES = ["jobs.ashbyhq.com", "job-boards.greenhouse.io", "boards.greenhouse.io", "jobs.lever.co", "myworkdayjobs.com",
         "jobs.smartrecruiters.com", "ats.rippling.com"]
# one query per (site, field); rotated by a cursor kept in discover.json so every pair comes up every few weeks
QUERIES = [f"site:{s} \"{f}\"" for f in FIELDS for s in SITES]
FIELD_RX = re.compile(r"(?i)propulsion|thermal|structur|aero|mechanical|test|gnc|guidance|nuclear|naval|fluid|flight|space|launch|rocket|satellite|turbine|engine")

LINK_RX = [  # (ats, regex with group 1 = board id)
    ("ashby", re.compile(r"https?://jobs\.ashbyhq\.com/([A-Za-z0-9._-]+)")),
    ("greenhouse", re.compile(r"https?://(?:job-boards|boards)\.greenhouse\.io/([A-Za-z0-9._-]+)")),
    ("lever", re.compile(r"https?://jobs\.lever\.co/([A-Za-z0-9._-]+)")),
    ("workday", re.compile(r"https?://([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com/")),
    ("smartrecruiters", re.compile(r"https?://jobs\.smartrecruiters\.com/([A-Za-z0-9._-]+)")),
    ("rippling", re.compile(r"https?://ats\.rippling\.com/([A-Za-z0-9._-]+)")),
]
SKIP_IDS = {"embed", "jobs", "job", "en", "en-us", "en_us", "search", "careers"}

def parse_link(url):
    for ats, rx in LINK_RX:
        m = rx.match(url or "")
        if m and m.group(1).lower() not in SKIP_IDS: return ats, m.group(1)
    return None

def known_ids(sources):
    """ats:id keys for every board already in sources.json (lowercased)."""
    keys = set()
    for s in sources:
        t = s["type"]
        if t in ("greenhouse", "lever", "ashby", "smartrecruiters", "rippling"): keys.add(f"{t}:{s['id'].lower()}")
        if t == "workday": keys.add(f"workday:{s['tenant'].lower()}")
    return keys

def load_ignore(path=None):
    path = path or os.path.join(ROOT, "discover_ignore.txt")
    keys = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line: keys.add(line.lower())
    return keys

def http_json(url, method="GET", body=None, headers=None):
    hd = {"Accept": "application/json", "User-Agent": "job-radar-discover (read-only)", **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    if data: hd["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hd, method=method), timeout=45) as r:
        return json.load(r)

def search(q, fetch):
    """-> list of {title, link, snippet} from the configured provider (SerpApi google_light gives direct links)."""
    if os.environ.get("SERPAPI_KEY"):
        params = {"engine": "google_light", "q": q, "num": 20, "api_key": os.environ["SERPAPI_KEY"], "hl": "en", "gl": "us"}
        j = fetch("https://serpapi.com/search.json?" + urllib.parse.urlencode(params))
        return [{"title": it.get("title") or "", "link": it.get("link") or "", "snippet": it.get("snippet") or ""} for it in j.get("organic_results", [])]
    if os.environ.get("SERPER_KEY"):
        j = fetch("https://google.serper.dev/search", "POST", {"q": q, "num": 20}, {"X-API-KEY": os.environ["SERPER_KEY"]})
        return [{"title": it.get("title") or "", "link": it.get("link") or "", "snippet": it.get("snippet") or ""} for it in j.get("organic", [])]
    return []

def probe(ats, bid, fetch):
    """Job count and a few in-field titles from the three public ATS APIs; None for the others (never fetched here)."""
    try:
        if ats == "greenhouse":
            j = fetch(f"https://boards-api.greenhouse.io/v1/boards/{bid}/jobs"); jobs = j.get("jobs", [])
            org = (fetch(f"https://boards-api.greenhouse.io/v1/boards/{bid}") or {}).get("name")
        elif ats == "lever":
            jobs = fetch(f"https://api.lever.co/v0/postings/{bid}?mode=json"); jobs = jobs if isinstance(jobs, list) else []; org = None
        elif ats == "ashby":
            j = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{bid}"); jobs = j.get("jobs", []); org = None
        else:
            return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return {"jobs": None, "error": f"{type(e).__name__}: {str(e)[:80]}"}
    titles = [x.get("title") or x.get("text") or "" for x in jobs]
    return {"jobs": len(jobs), "org": org, "inField": [t for t in titles if FIELD_RX.search(t)][:6]}

def company_from(title):
    """'Propulsion Engineer - Cowboy Space Corp.' / 'Cowboy Space Corp. | Propulsion Engineer' -> 'Cowboy Space Corp.' (best effort)."""
    parts = [p.strip() for p in re.split(r"\s[-|–·@]\s|\s+at\s+", title) if p.strip()]
    if len(parts) < 2: return None
    cands = [p for p in parts if not FIELD_RX.search(p)] or parts[1:]
    return cands[-1][:60]

def run(sources, state, fetch, today, max_q=QUERIES_PER_RUN, ignore=frozenset()):
    """One discovery run: the next max_q queries from the rotation; returns (state, new_keys). State: {cursor, boards{key: {...}}}."""
    known = known_ids(sources); boards = state.setdefault("boards", {}); cur = state.get("cursor", 0); new = []; n = 0
    for i in range(max_q):
        q = QUERIES[(cur + i) % len(QUERIES)]
        try: items = search(q, fetch)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            print(f"discover: stopped at query {i}: {type(e).__name__}: {str(e)[:120]}"); break
        n += 1
        for it in items:
            p = parse_link(it["link"])
            if not p: continue
            ats, bid = p; key = f"{ats}:{bid.lower()}"
            if key in known or key in ignore: continue
            b = boards.get(key)
            if b is None:
                b = {"ats": ats, "id": bid, "firstSeen": today.isoformat(), "query": q, "status": "new", "company": company_from(it["title"]),
                     "sample": [it["title"][:100]], "link": it["link"]}
                pr = probe(ats, bid, fetch)
                if pr: b.update(pr); b["company"] = pr.get("org") or b["company"]
                boards[key] = b; new.append(key)
            else:
                b["lastSeen"] = today.isoformat()
                if it["title"][:100] not in b["sample"] and len(b["sample"]) < 5: b["sample"].append(it["title"][:100])
    state["cursor"] = (cur + n) % len(QUERIES); state["updated"] = today.isoformat()
    for key in list(boards):  # boards added to sources.json since are done; keep the record for the history
        if key in known and boards[key]["status"] == "new": boards[key]["status"] = "added"
        if key in ignore and boards[key]["status"] == "new": boards[key]["status"] = "ignored"
    return state, new

DAYS = [int(x) for x in (os.environ.get("DISCOVER_DAYS") or "2,6").split(",")]  # weekday numbers (Mon=0): Wednesday and Sunday

def due(state, today, force=False):
    """Once a day on the configured weekdays (the scan runs three times a day); DISCOVER_FORCE / the `discover` input any time."""
    if force: return True
    return today.weekday() in DAYS and state.get("updated") != today.isoformat()

def main():
    if not (os.environ.get("SERPAPI_KEY") or os.environ.get("SERPER_KEY")): print("discover: no SERPAPI_KEY or SERPER_KEY; skipped"); return
    with open(os.path.join(ROOT, "sources.json"), encoding="utf-8") as f: sources = json.load(f)
    path = os.path.join(DATA, "discover.json")
    state = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    today = dt.date.today()
    if not due(state, today, bool(os.environ.get("DISCOVER_FORCE"))): print(f"discover: not due today ({today:%A}; runs Wed/Sun once); skipped"); return
    state, new = run(sources, state, http_json, today, ignore=load_ignore())
    with open(path, "w", encoding="utf-8") as f: json.dump(state, f, indent=1, sort_keys=True)
    pending = [k for k, b in state["boards"].items() if b["status"] == "new"]
    print(f"discover: {len(new)} new boards this run, {len(pending)} awaiting review (data/discover.json); cursor {state['cursor']}/{len(QUERIES)}")
    for k in new:
        b = state["boards"][k]; print(f"  {k}: {b.get('company') or '?'} · {b.get('jobs') if b.get('jobs') is not None else '-'} jobs · {'; '.join(b.get('inField') or [])[:120]}")

if __name__ == "__main__":
    main()
