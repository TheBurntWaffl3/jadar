"""Tailoring queue for the resume session on Kevin's PC (2026-11-26: "the pipeline should be automatic").

Morning run only. Builds the same queue the Resumes page shows (Yes roles + saved Maybe roles, minus hidden / applied /
done / skipped and minus roles that already have a PDF in the private repo's resumes/ folder), writes it with a ready brief
per role to `tailor_queue.json` in the private state repo. A scheduled task on Kevin's PC reads that file, makes the
resumes and pushes the PDFs; the Resumes page then shows them. Nothing here touches the public page or this repo.

Env: STATE_REPO, STATE_TOKEN (STATE_PATH optional), RADAR_DATA, QUEUE_MAX (default 25). Never fails the run.
(Named tailor_queue.py because `queue` is a stdlib module the scanner's thread pool needs.)
"""
import base64, datetime as dt, json, os, re, sys, urllib.error
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
import alert, finder

DATA = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))

def slug(company, title):
    """Same as the Resumes page's slug(): companyKey + title, lowercased, every run of non-alphanumerics -> '-' (so the
    joiner becomes a single hyphen too), trimmed, 90 chars. E.g. lockheed-martin-systems-engineer-asc-early-career."""
    return re.sub(r"[^a-z0-9]+", "-", (alert.company_key(company) + "__" + (title or "")).lower()).strip("-")[:90]

def _dir():
    p = os.environ.get("STATE_PATH") or "state.json"
    return p.rsplit("/", 1)[0] + "/" if "/" in p else ""

def _url(name): return f"https://api.github.com/repos/{os.environ['STATE_REPO']}/contents/{_dir()}{name}"

def list_files(fetch):
    try: return [f["name"] for f in fetch(_url("resumes"), os.environ["STATE_TOKEN"]) if f.get("type") == "file"]
    except urllib.error.HTTPError as e:
        if e.code == 404: return []
        raise

def load_queue(fetch):
    try:
        j = fetch(_url("tailor_queue.json"), os.environ["STATE_TOKEN"]); return j.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise

def save_queue(doc, sha, fetch):
    body = {"message": f"Tailoring queue {dt.date.today().isoformat()}", "content": base64.b64encode(json.dumps(doc, indent=1).encode()).decode()}
    if sha: body["sha"] = sha
    fetch(_url("tailor_queue.json"), os.environ["STATE_TOKEN"], "PUT", body)

def fmt_long(iso):
    try: return dt.date.fromisoformat(iso).strftime("%B %d, %Y").replace(" 0", " ")
    except (ValueError, TypeError): return iso or ""

def brief(r):
    """The same text the Resumes page's Copy brief produces."""
    lines = ["Tailor my resume for this posting. Read-only: do not apply, sign in or submit anything.",
             f"Company: {r['company']}", f"Role: {r['title']}", f"Link: {r['url']}", f"Location: {r['location']}" if r.get("location") else "",
             f"Radar verdict: {r['fit']}" + (f" ({r['why']})" if r.get("why") else ""), f"Apply by: {fmt_long(r['applyBy'])}" if r.get("applyBy") else "",
             f"Pay listed: {r['salary']}" if r.get("salary") else "", "", "Minimum qualifications from the posting:", r.get("reqSnippet") or "(none extracted; read the posting)", "",
             "Start from the master resume and the confirmed facts in CLAUDE.md. Keep one page. Lead with what this posting asks for; rephrase, reorder and select only, never invent.",
             f"Save the PDF to the jadar-state repo as resumes/{slug(r['company'], r['title'])}.pdf (that exact name attaches it to the role on the Resumes page)."]
    return "\n".join(x for x in lines if x != "")

def build_queue(out, state, files, max_n=25):
    """Ordered queue: saved roles first, then roles naming 2027, then newest. Skips hidden/applied, done/skipped marks, and
    roles whose PDF already exists (filename starts with the slug)."""
    doc = state.get("_doc") or {}; marks = doc.get("tailor") or {}
    names = [f.lower() for f in files]
    items = []
    for r in out.get("roles", []):
        st = state.get(r["url"]); saved = st == "saved"
        if st in ("hidden", "applied") or (marks.get(r["url"]) or {}).get("status") in ("done", "skip"): continue
        if not (r["fit"] == "Yes" or (saved and r["fit"] == "Maybe")): continue
        sl = slug(r["company"], r["title"])
        if any(n.startswith(sl) for n in names): continue
        key = (0 if saved else 1, 0 if r.get("timing") == "2027" else 1, -(int((r.get("date") or "0000-00-00").replace("-", "") or 0)))
        items.append((key, dict(url=r["url"], company=r["company"], title=r["title"], slug=sl, fit=r["fit"], why=r.get("why") or "", location=r.get("location") or "",
                                date=r.get("date"), applyBy=r.get("applyBy"), salary=r.get("salary"), saved=saved, timing=r.get("timing"), reqSnippet=r.get("reqSnippet") or "")))
    items.sort(key=lambda x: x[0])
    rows = [it for _, it in items[:max_n]]
    for it in rows: it["brief"] = brief(it)
    return rows

def main():
    missing = [k for k in ("STATE_REPO", "STATE_TOKEN") if not os.environ.get(k)]
    if missing: print("queue: not configured (" + ", ".join(missing) + "); nothing done"); return
    with open(os.path.join(DATA, "radar_out.json")) as f: out = json.load(f)
    state = alert.load_state(); files = list_files(finder.http_json)
    rows = build_queue(out, state, files, int(os.environ.get("QUEUE_MAX") or 25))
    doc = dict(v=1, generatedAt=dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), scanned=out.get("scanned"), count=len(rows),
               note="Written by the jadar morning run. Make the PDFs in order; name each resumes/<slug>.pdf; roles with a PDF already in resumes/ are not listed.", items=rows)
    save_queue(doc, load_queue(finder.http_json), finder.http_json)
    print(f"queue: {len(rows)} roles queued ({sum(1 for r in rows if r['saved'])} saved, {sum(1 for r in rows if r['timing'] == '2027')} naming 2027); {len(files)} PDFs already in resumes/")

if __name__ == "__main__":
    try: main()
    except Exception as ex: print(f"queue: {type(ex).__name__}: {str(ex)[:200]}; nothing more done")
