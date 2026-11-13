#!/usr/bin/env python3
"""Terps finder: for every company with a Yes/Maybe fit, search public LinkedIn profiles of University of Maryland people
there, via Google Programmable Search (an engine restricted to linkedin.com/in). Results go to people.json in Kevin's
PRIVATE state repo (never the public page or data branch). Read-only; nobody is contacted.

Env: GOOGLE_CSE_ID, GOOGLE_CSE_KEY (search), STATE_REPO, STATE_TOKEN, STATE_PATH-like PEOPLE_PATH (default people.json),
     RADAR_DATA (data dir with radar_out.json), FINDER_MAX (queries per run, default 60; Google's free quota is 100/day),
     FINDER_DAYS (re-search a company after this many days, default 7)."""
import json, os, re, sys, base64, urllib.request, urllib.parse, urllib.error, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
SCHOOL = '"University of Maryland"'
# Search alias when the board name isn't what people write on their profiles.
ALIAS = {"RTX": "Raytheon", "HII": "Huntington Ingalls", "JHU APL": "Johns Hopkins Applied Physics Laboratory",
         "Electric Boat": "General Dynamics Electric Boat", "NASA JPL": "Jet Propulsion Laboratory",
         "Aerospace Corp": "The Aerospace Corporation", "Sierra Nevada Corp": "Sierra Nevada Corporation",
         "Penn State ARL": "Penn State Applied Research Laboratory", "GE Vernova": "GE Vernova", "MIT Lincoln Lab": "MIT Lincoln Laboratory",
         "Bath Iron Works": "Bath Iron Works", "Naval Nuclear Laboratory": "Naval Nuclear Laboratory", "Commonwealth Fusion": "Commonwealth Fusion Systems",
         "Voyager": "Voyager Technologies", "Blue Origin": "Blue Origin", "LLNL": "Lawrence Livermore National Laboratory",
         "LANL": "Los Alamos National Laboratory", "GTRI": "Georgia Tech Research Institute", "ULA": "United Launch Alliance"}

def company_key(c):
    """Same rule as the page's companyKey(): strip parentheticals, part before ' / ', collapse spaces."""
    return re.sub(r"\s+", " ", re.sub(r"\s*\(.*?\)\s*", " ", c or "").split(" / ")[0]).strip()

def query_for(key):
    return f'{SCHOOL} "{ALIAS.get(key, key)}"'

def parse_items(items):
    """Google CSE items -> people entries. Titles look like 'Jane Doe - Propulsion Engineer - Anduril | LinkedIn'."""
    out = []
    for it in items or []:
        url = it.get("link") or ""
        if not re.match(r"^https?://([a-z]{2,3}\.)?linkedin\.com/in/", url): continue
        title = re.sub(r"\s*[|\-–]\s*LinkedIn\s*$", "", it.get("title") or "").strip()
        parts = [p.strip() for p in re.split(r"\s+[-–|]\s+", title) if p.strip()]
        name = parts[0] if parts else title
        headline = " · ".join(parts[1:])[:140]
        snippet = re.sub(r"\s+", " ", it.get("snippet") or "")[:200]
        if name: out.append(dict(name=name[:80], headline=headline, url=url.split("?")[0], snippet=snippet))
    return out

def search(key, fetch):
    q = query_for(key)
    url = "https://www.googleapis.com/customsearch/v1?" + urllib.parse.urlencode(
        {"key": os.environ["GOOGLE_CSE_KEY"], "cx": os.environ["GOOGLE_CSE_ID"], "q": q, "num": 10})
    return q, parse_items(fetch(url).get("items", []))

def http_json(url, token=None, method="GET", body=None):
    hd = {"Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json", "User-Agent": "job-radar-finder"}
    if token: hd["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    if data: hd["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hd, method=method), timeout=60) as r:
        return json.load(r)

def gh_url():
    return f"https://api.github.com/repos/{os.environ['STATE_REPO']}/contents/{os.environ.get('PEOPLE_PATH') or 'people.json'}"

def load_people(fetch):
    try:
        j = fetch(gh_url(), os.environ["STATE_TOKEN"])
        return json.loads(base64.b64decode(j["content"]).decode("utf-8")), j.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404: return {"v": 1, "companies": {}}, None
        raise

def save_people(doc, sha, fetch):
    body = {"message": f"Terps finder {dt.date.today().isoformat()}", "content": base64.b64encode(json.dumps(doc, separators=(",", ":")).encode()).decode()}
    if sha: body["sha"] = sha
    fetch(gh_url(), os.environ["STATE_TOKEN"], "PUT", body)

def plan(out, people, today, days=7, max_q=60):
    """Companies with Yes/Maybe fits whose entry is missing or older than `days`, most fits first, capped."""
    counts = {}
    for r in out.get("roles", []):
        if r["fit"] in ("Yes", "Maybe"): counts[company_key(r["company"])] = counts.get(company_key(r["company"]), 0) + 1
    cutoff = (today - dt.timedelta(days=days)).isoformat()
    due = [k for k in counts if (people.get("companies", {}).get(k, {}).get("searched") or "") < cutoff]
    due.sort(key=lambda k: (-counts[k], k))
    return due[:max_q], len(counts)

def main():
    for k in ("GOOGLE_CSE_ID", "GOOGLE_CSE_KEY", "STATE_REPO", "STATE_TOKEN"):
        if not os.environ.get(k): print(f"finder: {k} not set; skipped"); return
    with open(os.path.join(DATA, "radar_out.json")) as f: out = json.load(f)
    today = dt.date.today()
    people, sha = load_people(http_json)
    due, total = plan(out, people, today, int(os.environ.get("FINDER_DAYS") or 7), int(os.environ.get("FINDER_MAX") or 60))
    print(f"finder: {total} companies with fits, {len(due)} due for a search")
    done = 0; found = 0
    for key in due:
        try:
            q, found_people = search(key, lambda u: http_json(u))
        except urllib.error.HTTPError as e:
            try: detail = re.sub(r"\s+", " ", e.read().decode("utf-8", "replace"))[:400]
            except Exception: detail = ""
            print(f"finder: stopped at {key}: HTTP {e.code}. Google said: {detail}"); break
        people.setdefault("companies", {})[key] = dict(searched=today.isoformat(), query=q, people=found_people)
        done += 1; found += len(found_people)
    if done:
        people["v"] = 1; people["updated"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save_people(people, sha, http_json)
    print(f"finder: searched {done} companies, {found} profiles found; people.json now covers {len(people.get('companies', {}))} companies")

if __name__ == "__main__":
    main()
