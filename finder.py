#!/usr/bin/env python3
"""Terps finder: for every company with a Yes/Maybe fit, search public LinkedIn profiles of University of Maryland people
there, through a Google-results API: SerpApi (SERPAPI_KEY; free 250/month) or Serper (SERPER_KEY; 2,500 free once).
Google's own Custom Search JSON API is closed to new customers since 2026-01-20 and is not supported.
Results go to people.json in Kevin's PRIVATE state repo (never the public page or data branch). Read-only; nobody is contacted.

Env: SERPAPI_KEY or SERPER_KEY (search), STATE_REPO, STATE_TOKEN, PEOPLE_PATH (default people.json),
     RADAR_DATA (data dir with radar_out.json), FINDER_MAX (queries per run, default 15), FINDER_DAYS (re-search a company
     after this many days, default 14). ~83 companies / 14 days = ~180 searches a month, under SerpApi's free 250."""
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

# Field-narrowed searches for companies with many fits: discipline (as the page labels it) -> search word; `via` stores the
# lowercased discipline so the page can match a person to the role's field.
FIELD_WORD = {"Thermal": "thermal", "Propulsion": "propulsion", "Structures": "structural", "Test": "test", "Nuclear": "nuclear",
              "Naval": "naval", "Aero": "aerodynamics", "Mechanical": "mechanical"}
BIG = 8  # fits at or above this -> also search the company's top disciplines

def query_for(key, term=None, site_in_query=False):
    """The search text. SerpApi gets the site restriction as a parameter (as_sitesearch) because Google quietly drops a
    `site:` operator and auto-corrects when it finds few matches; Serper has no such parameter, so it keeps `site:` in the text."""
    return ("site:linkedin.com/in " if site_in_query else "") + f'{SCHOOL} "{ALIAS.get(key, key)}"' + (f" {term}" if term else "")

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

def provider():
    if os.environ.get("SERPAPI_KEY"): return "serpapi"
    if os.environ.get("SERPER_KEY"): return "serper"
    return None

def _serpapi(q, fetch, engine="google"):
    """SerpApi Google results. The default parser sometimes returns google.com/goto redirect links instead of the real URLs
    (seen 2026-11-14); `google_light` is SerpApi's simpler parser that gives direct links, used as the fallback."""
    params = {"engine": engine, "q": q, "num": 10, "api_key": os.environ["SERPAPI_KEY"], "hl": "en", "gl": "us", "google_domain": "google.com"}
    if engine == "google": params.update({"as_sitesearch": "linkedin.com", "nfpr": 1})
    j = fetch("https://serpapi.com/search.json?" + urllib.parse.urlencode(params))
    raw = j.get("organic_results", [])
    for it in raw:  # prefer a real link over a Google redirect when both are present
        if "google.com/goto" in (it.get("link") or "") and it.get("redirect_link") and "google.com" not in it["redirect_link"]: it["link"] = it["redirect_link"]
    return raw, j.get("error") or (j.get("search_information") or {}).get("organic_results_state")

def _serper(q, fetch):
    j = fetch("https://google.serper.dev/search", None, "POST", {"q": q, "num": 10}, {"X-API-KEY": os.environ["SERPER_KEY"]})
    return j.get("organic", []), j.get("message")

def search(key, fetch, term=None):
    """-> (query, people, usable). `usable` is False when Google ignored the site restriction (no linkedin.com links at all,
    or only google.com/goto redirects), which happens on some SERPs; the caller then does not treat the company as searched.
    One retry with a different phrasing (inurl:) before giving up. `fetch(url, token=None, method='GET', body=None, headers=None)`."""
    run = _serpapi if provider() == "serpapi" else _serper if provider() == "serper" else None
    if not run: raise RuntimeError("no search provider configured")
    tried = []
    attempts = [(query_for(key, term, site_in_query=True), {})]
    if provider() == "serpapi": attempts.append((query_for(key, term, site_in_query=True), {"engine": "google_light"}))
    attempts.append((f'inurl:linkedin.com/in {SCHOOL} "{ALIAS.get(key, key)}"' + (f" {term}" if term else ""), {}))
    for q, kw in attempts:
        raw, note = run(q, fetch, **kw); tried.append(q + (" [light]" if kw else ""))
        people = parse_items(raw)
        linked = sum(1 for it in raw if "linkedin.com" in (it.get("link") or ""))
        redirects = sum(1 for it in raw if "google.com/goto" in (it.get("link") or ""))
        print(f"  {q[:80]}{' [light]' if kw else ''} -> {len(raw)} results, {linked} on linkedin, {redirects} redirects, {len(people)} profiles"
              + (f" ({note})" if note and note not in ("Success", "Results for exact spelling") else ""))
        if people or linked: return q, people, True
        if raw and not linked:
            for it in raw[:2]: print(f"      skipped: {(it.get('link') or '')[:80]} | {(it.get('title') or '')[:60]}")
        if not raw: return q, [], True  # a genuine empty answer: nothing to find
    return " / ".join(tried), [], False

def http_json(url, token=None, method="GET", body=None, headers=None):
    hd = {"Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json", "User-Agent": "job-radar-finder", **(headers or {})}
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

def plan(out, people, today, days=14, max_q=15):
    """-> ([(companyKey, [disciplines to narrow by]), ...], companies with fits). Companies whose entry is missing or older
    than `days`, most fits first; a company with >= BIG fits also gets up to 2 field-narrowed searches. `max_q` caps queries."""
    counts, fields = {}, {}
    for r in out.get("roles", []):
        if r["fit"] in ("Yes", "Maybe"):
            k = company_key(r["company"]); counts[k] = counts.get(k, 0) + 1
            d = r.get("discipline")
            if d in FIELD_WORD: fields.setdefault(k, {})[d] = fields.setdefault(k, {}).get(d, 0) + 1
    cutoff = (today - dt.timedelta(days=days)).isoformat()
    ents = people.get("companies", {})
    # due: never searched, searched more than `days` ago, or searched with no result (retried the next day, not in 2 weeks)
    due = [k for k in counts if (ents.get(k, {}).get("searched") or "") < cutoff
           or (not ents.get(k, {}).get("people") and (ents.get(k, {}).get("searched") or "") < today.isoformat())]
    due.sort(key=lambda k: (-counts[k], k))
    todo, budget = [], max_q
    for k in due:
        narrow = [d for d, _ in sorted(fields.get(k, {}).items(), key=lambda x: -x[1])[:2]] if counts[k] >= BIG else []
        need = 1 + len(narrow)
        if need > budget:
            if budget >= 1: todo.append((k, narrow[:budget - 1])); budget = 0
            break
        todo.append((k, narrow)); budget -= need
    return todo, len(counts)

def main():
    if not provider(): print("finder: no SERPAPI_KEY or SERPER_KEY; skipped"); return
    for k in ("STATE_REPO", "STATE_TOKEN"):
        if not os.environ.get(k): print(f"finder: {k} not set; skipped"); return
    with open(os.path.join(DATA, "radar_out.json")) as f: out = json.load(f)
    today = dt.date.today()
    people, sha = load_people(http_json)
    due, total = plan(out, people, today, int(os.environ.get("FINDER_DAYS") or 14), int(os.environ.get("FINDER_MAX") or 15))
    print(f"finder ({provider()}): {total} companies with fits, {len(due)} due for a search this run")
    done = 0; found = 0; queries = 0; stop = False
    for key, narrow in due:
        merged, qs, usable = {}, [], False
        for term_d in [None] + narrow:
            term = FIELD_WORD[term_d] if term_d else None
            try:
                q, got, ok = search(key, http_json, term); queries += 1 + (0 if ok and got else 1)
            except urllib.error.HTTPError as e:
                try: detail = re.sub(r"\s+", " ", e.read().decode("utf-8", "replace"))[:400]
                except Exception: detail = ""
                print(f"finder: stopped at {key}: HTTP {e.code}. Provider said: {detail}"); stop = True; break
            qs.append(q); usable = usable or ok
            for p_ in got:
                p_["via"] = term_d.lower() if term_d else "base"
                merged.setdefault(p_["url"], p_)  # first hit wins (base first, then fields)
        if stop and not merged: break
        if usable or merged:
            people.setdefault("companies", {})[key] = dict(searched=today.isoformat(), query=" || ".join(qs), people=list(merged.values()))
            done += 1; found += len(merged)
        else:
            print(f"  {key}: Google ignored the site restriction on every query; left for the next run")
        if stop: break
    if done:
        people["v"] = 1; people["updated"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save_people(people, sha, http_json)
    print(f"finder: {queries} searches over {done} companies, {found} profiles found; people.json now covers {len(people.get('companies', {}))} companies")

if __name__ == "__main__":
    main()
