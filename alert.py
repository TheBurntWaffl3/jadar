#!/usr/bin/env python3
"""Daily alert from data/radar_out.json. Sends via ntfy and/or email, whichever is configured (GitHub Actions secrets):

  NTFY_TOPIC   (required for ntfy)   NTFY_SERVER (default https://ntfy.sh)   NTFY_TOKEN (optional access token)
  SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_TO (all required for email)   SMTP_PORT (default 587)   ALERT_FROM (default SMTP_USER)
  PAGE_URL     link to the dashboard (default: https://<owner>.github.io/<repo>/ from GITHUB_REPOSITORY)
  STATE_REPO, STATE_TOKEN, STATE_PATH (default state.json): the private repo the page syncs Kevin's saved/applied/hidden
               roles to; when set, hidden and applied roles are left out of the alert and saved ones are marked with *.

  QUIET_IF_EMPTY=1  send nothing when there are no new fits (the evening run)
  alerted.json in the data dir remembers which postings were already sent, so no posting is mailed twice.

With nothing configured, the message is only printed. Never sends anything to a job site."""
import json, os, sys, html, smtplib, urllib.request, datetime as dt
from email.message import EmailMessage

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
MAX_NEW = 8          # ntfy / plain text cap; the email lists every new fit
LEDGER = os.path.join(DATA, "alerted.json")

def load_alerted():
    try:
        with open(LEDGER) as f: return json.load(f)
    except Exception: return {}

def save_alerted(ledger, urls, today):
    cutoff = (today - dt.timedelta(days=45)).isoformat()
    ledger = {u: d for u, d in ledger.items() if d >= cutoff}
    for u in urls: ledger[u] = today.isoformat()
    os.makedirs(DATA, exist_ok=True)
    with open(LEDGER, "w") as f: json.dump(ledger, f, separators=(",", ":"))

def page_url():
    if os.environ.get("PAGE_URL"): return os.environ["PAGE_URL"]
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return ""

def load_state():
    """{url: status} from the private state repo the page syncs to (see build_page.py); {} when not configured or unreadable."""
    repo, token = os.environ.get("STATE_REPO"), os.environ.get("STATE_TOKEN")
    if not repo or not token: return {}
    import base64
    url = f"https://api.github.com/repos/{repo}/contents/{os.environ.get('STATE_PATH') or 'state.json'}"
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "job-radar"})
        with urllib.request.urlopen(req, timeout=30) as r: j = json.load(r)
        doc = json.loads(base64.b64decode(j["content"]).decode("utf-8"))
        return {u: (e.get("status") or "") for u, e in (doc.get("roles") or {}).items()}
    except Exception as e:
        print(f"state not read ({type(e).__name__}); alert ignores saved/applied/hidden"); return {}

def load_people():
    """{companyKey: n} Terps found per company from the private people.json written by finder.py; {} when unavailable."""
    repo, token = os.environ.get("STATE_REPO"), os.environ.get("STATE_TOKEN")
    if not repo or not token: return {}
    import base64, re
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/contents/{os.environ.get('PEOPLE_PATH') or 'people.json'}",
                                     headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "job-radar"})
        with urllib.request.urlopen(req, timeout=30) as r: j = json.load(r)
        doc = json.loads(base64.b64decode(j["content"]).decode("utf-8"))
        return {k: len(v.get("people") or []) for k, v in (doc.get("companies") or {}).items()}
    except Exception: return {}

def company_key(c):
    import re
    return re.sub(r"\s+", " ", re.sub(r"\s*\(.*?\)\s*", " ", c or "").split(" / ")[0]).strip()

def compose(out, today=None, state=None, alerted=None, people=None):
    """-> (title, body, priority, parts). Body is plain text, phone-sized; `parts` feeds the HTML email.
    `state` = {url: saved|applied|hidden} from load_state(); `alerted` = {url: date} already sent (left out)."""
    today = today or dt.date.today(); state = state or {}; alerted = alerted or {}; people = people or {}
    rank = {"Yes": 0, "Maybe": 1}
    skip = {u for u, st in state.items() if st in ("hidden", "applied")} | set(alerted)
    star = lambda r: "* " if state.get(r["url"]) == "saved" else ""
    new = sorted([r for r in out.get("new", []) if r["fit"] in rank and r["url"] not in skip], key=lambda r: (rank[r["fit"]], r.get("date") or ""), reverse=False)
    new.sort(key=lambda r: rank[r["fit"]])
    lines = []
    if new:
        lines.append(f"{len(new)} new fit{'s' if len(new) != 1 else ''} ({sum(r['fit']=='Yes' for r in new)} Yes):")
        for r in new[:MAX_NEW]:
            loc = f" ({r['location']})" if r.get("location") else ""
            terps = people.get(company_key(r["company"]), 0)
            lines.append(f"- {star(r)}{r['company']}: {r['title']}{loc} - {r['fit']}, {r['why']}" + (f" ({terps} Terps there)" if terps else "") + f"\n  {r['url']}")
        if len(new) > MAX_NEW: lines.append(f"  ... and {len(new) - MAX_NEW} more on the page")
    else:
        lines.append("No new Yes/Maybe fits today.")
    st = out.get("status", [])
    ok = [s for s in st if s["ok"]]; bad = [s for s in st if not s["ok"]]
    lines.append(f"Feeds OK {len(ok)}/{len(st)}" + (": failing " + ", ".join(s["org"] for s in bad) if bad else ""))
    soon = []
    for r in out.get("roles", []):
        if r["fit"] in rank and r.get("applyBy") and r["url"] not in skip:
            try: days = (dt.date.fromisoformat(r["applyBy"]) - today).days
            except ValueError: continue
            if 0 <= days <= 7: soon.append((days, r))
    if soon:
        soon.sort(key=lambda x: (state.get(x[1]["url"]) != "saved", x[0]))  # saved roles first
        lines.append("Closing soon: " + "; ".join(f"{star(r)}{r['company']} {r['title']} ({d}d)" for d, r in soon[:6]))
    applied = sum(1 for st in state.values() if st == "applied")
    if applied: lines.append(f"Applied so far: {applied}")
    url = page_url()
    if url: lines.append(url)
    yes = sum(r["fit"] == "Yes" for r in new)
    title = f"Job radar: {yes} Yes, {len(new) - yes} Maybe new" if new else "Job radar: nothing new"
    if bad and not new: title += f" ({len(bad)} feed{'s' if len(bad) != 1 else ''} failing)"
    parts = dict(new=new, soon=soon, ok=len(ok), total=len(st), bad=[s["org"] for s in bad], applied=applied, url=url,
                 saved={u for u, s_ in state.items() if s_ == "saved"}, today=today, scanned=out.get("scanned", ""),
                 fits=sum(1 for r in out.get("roles", []) if r["fit"] in rank and r["url"] not in skip), people=people)
    return title, "\n".join(lines), ("high" if yes else "default"), parts

def render_html(parts):
    """The email body: a short digest in the page's look (black header, blue accent), inline styles only."""
    e = html.escape; p = parts
    def row(r, extra=""):
        terps = p.get("people", {}).get(company_key(r["company"]), 0)
        meta = " · ".join(x for x in [r.get("location") or "", r.get("salary") or "", extra, (f"{terps} Terps there" if terps else "")] if x)
        saved = ' <span style="color:#2f5bea">★</span>' if r["url"] in p["saved"] else ""
        color = "#0ca30c" if r["fit"] == "Yes" else "#2f5bea"
        return (f'<tr><td style="padding:10px 0;border-bottom:1px solid #ececee;vertical-align:top">'
                f'<div style="font:12px/1.4 Menlo,Consolas,monospace;letter-spacing:.06em;text-transform:uppercase;color:{color}">{e(r["fit"])}'
                f'<span style="color:#737379"> · {e(r["company"])}</span></div>'
                f'<a href="{e(r["url"])}" style="font:600 16px/1.3 \'Inter Tight\',system-ui,sans-serif;color:#0b0b0c;text-decoration:none">{e(r["title"])}</a>{saved}'
                f'<div style="font:13px/1.4 system-ui,sans-serif;color:#737379">{e(meta)}</div>'
                f'<div style="font:13px/1.4 system-ui,sans-serif;color:#3f3f44">{e(r.get("why") or "")}</div></td></tr>')
    new = p["new"]; yes = [r for r in new if r["fit"] == "Yes"]; maybe = [r for r in new if r["fit"] == "Maybe"]
    sections = []
    if yes: sections.append('<h2 style="font:600 14px/1 system-ui,sans-serif;margin:22px 0 4px">Yes</h2><table style="border-collapse:collapse;width:100%">' + "".join(row(r) for r in yes) + "</table>")
    if maybe: sections.append('<h2 style="font:600 14px/1 system-ui,sans-serif;margin:22px 0 4px">Maybe</h2><table style="border-collapse:collapse;width:100%">' + "".join(row(r) for r in maybe) + "</table>")
    if not new: sections.append('<p style="font:15px system-ui,sans-serif;color:#737379;margin:18px 0">No new Yes/Maybe fits since the last email.</p>')
    if p["soon"]:
        sections.append('<h2 style="font:600 14px/1 system-ui,sans-serif;margin:22px 0 4px">Closing within 7 days</h2><table style="border-collapse:collapse;width:100%">' +
                        "".join(row(r, f"closes in {d} day{'s' if d != 1 else ''}" if d else "closes today") for d, r in p["soon"][:8]) + "</table>")
    feeds = f'{p["ok"]}/{p["total"]} boards read' + (f' · failing: {e(", ".join(p["bad"]))}' if p["bad"] else "")
    head = (f'<div style="background:#0b0b0c;color:#fff;border-radius:16px;padding:20px 22px">'
            f'<div style="font:600 28px/1 \'Inter Tight\',system-ui,sans-serif;letter-spacing:-.02em">Job radar.</div>'
            f'<div style="font:11px/1.6 Menlo,Consolas,monospace;letter-spacing:.08em;text-transform:uppercase;color:#9a9aa0;margin-top:8px">'
            f'{len(new)} new · {p["fits"]} open fits · {e(feeds)}' + (f' · {p["applied"]} applied' if p["applied"] else "") + "</div></div>")
    foot = (f'<p style="font:13px system-ui,sans-serif;color:#737379;margin:24px 0 0">'
            + (f'<a href="{e(p["url"])}" style="color:#2f5bea">Open the radar</a> · ' if p["url"] else "")
            + 'Read-only scan; nothing is applied to automatically.</p>')
    return ('<!doctype html><html><body style="margin:0;background:#fff;color:#0b0b0c"><div style="max-width:640px;margin:0 auto;padding:16px">'
            + head + "".join(sections) + foot + "</div></body></html>")

def send_ntfy(title, body, priority):
    server = (os.environ.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    hd = {"Title": title, "Priority": priority, "Tags": "satellite", "Content-Type": "text/plain; charset=utf-8"}
    if os.environ.get("NTFY_TOKEN"): hd["Authorization"] = "Bearer " + os.environ["NTFY_TOKEN"]
    url = page_url()
    if url: hd["Click"] = url
    req = urllib.request.Request(f"{server}/{os.environ['NTFY_TOPIC']}", data=body.encode(), headers=hd, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r: return r.status

def send_email(title, body, html_body=None):
    msg = EmailMessage(); msg["Subject"] = title
    msg["From"] = os.environ.get("ALERT_FROM") or os.environ["SMTP_USER"]; msg["To"] = os.environ["ALERT_TO"]
    msg.set_content(body)
    if html_body: msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT") or "587"), timeout=60) as s:
        s.starttls(); s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(msg)

def main():
    with open(os.path.join(DATA, "radar_out.json")) as f: out = json.load(f)
    today = dt.date.today(); ledger = load_alerted()
    title, body, prio, parts = compose(out, today, state=load_state(), alerted=ledger, people=load_people())
    print(title); print(body)
    if os.environ.get("QUIET_IF_EMPTY") == "1" and not parts["new"]:
        print("nothing new since the last alert; quiet run, nothing sent"); return
    sent = []
    if os.environ.get("NTFY_TOPIC"):
        send_ntfy(title, body, prio); sent.append("ntfy")
    if all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_TO")):
        send_email(title, body, render_html(parts)); sent.append("email")
    if sent:
        save_alerted(ledger, [r["url"] for r in parts["new"]], today)
        print("sent via " + ", ".join(sent) + f"; {len(parts['new'])} postings recorded in alerted.json")
    else:
        print("no alert channel configured (set NTFY_TOPIC or SMTP_* secrets); printed only")

if __name__ == "__main__":
    main()
