#!/usr/bin/env python3
"""Daily alert from data/radar_out.json. Sends via ntfy and/or email, whichever is configured (GitHub Actions secrets):

  NTFY_TOPIC   (required for ntfy)   NTFY_SERVER (default https://ntfy.sh)   NTFY_TOKEN (optional access token)
  SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_TO (all required for email)   SMTP_PORT (default 587)   ALERT_FROM (default SMTP_USER)
  PAGE_URL     link to the dashboard (default: https://<owner>.github.io/<repo>/ from GITHUB_REPOSITORY)

With nothing configured, the message is only printed. Never sends anything to a job site."""
import json, os, sys, smtplib, urllib.request, datetime as dt
from email.message import EmailMessage

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
MAX_NEW = 8

def page_url():
    if os.environ.get("PAGE_URL"): return os.environ["PAGE_URL"]
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return ""

def compose(out, today=None):
    """-> (title, body, priority). Body is plain text, phone-sized."""
    today = today or dt.date.today()
    rank = {"Yes": 0, "Maybe": 1}
    new = sorted([r for r in out.get("new", []) if r["fit"] in rank], key=lambda r: (rank[r["fit"]], r.get("date") or ""), reverse=False)
    new.sort(key=lambda r: rank[r["fit"]])
    lines = []
    if new:
        lines.append(f"{len(new)} new fit{'s' if len(new) != 1 else ''} ({sum(r['fit']=='Yes' for r in new)} Yes):")
        for r in new[:MAX_NEW]:
            loc = f" ({r['location']})" if r.get("location") else ""
            lines.append(f"- {r['company']}: {r['title']}{loc} - {r['fit']}, {r['why']}\n  {r['url']}")
        if len(new) > MAX_NEW: lines.append(f"  ... and {len(new) - MAX_NEW} more on the page")
    else:
        lines.append("No new Yes/Maybe fits today.")
    st = out.get("status", [])
    ok = [s for s in st if s["ok"]]; bad = [s for s in st if not s["ok"]]
    lines.append(f"Feeds OK {len(ok)}/{len(st)}" + (": failing " + ", ".join(s["org"] for s in bad) if bad else ""))
    soon = []
    for r in out.get("roles", []):
        if r["fit"] in rank and r.get("applyBy"):
            try: days = (dt.date.fromisoformat(r["applyBy"]) - today).days
            except ValueError: continue
            if 0 <= days <= 7: soon.append((days, r))
    if soon:
        soon.sort(key=lambda x: x[0])
        lines.append("Closing soon: " + "; ".join(f"{r['company']} {r['title']} ({d}d)" for d, r in soon[:6]))
    url = page_url()
    if url: lines.append(url)
    yes = sum(r["fit"] == "Yes" for r in new)
    title = f"Job radar: {yes} Yes, {len(new) - yes} Maybe new" if new else "Job radar: nothing new"
    if bad and not new: title += f" ({len(bad)} feed{'s' if len(bad) != 1 else ''} failing)"
    return title, "\n".join(lines), ("high" if yes else "default")

def send_ntfy(title, body, priority):
    server = (os.environ.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    hd = {"Title": title, "Priority": priority, "Tags": "satellite", "Content-Type": "text/plain; charset=utf-8"}
    if os.environ.get("NTFY_TOKEN"): hd["Authorization"] = "Bearer " + os.environ["NTFY_TOKEN"]
    url = page_url()
    if url: hd["Click"] = url
    req = urllib.request.Request(f"{server}/{os.environ['NTFY_TOPIC']}", data=body.encode(), headers=hd, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r: return r.status

def send_email(title, body):
    msg = EmailMessage(); msg["Subject"] = title
    msg["From"] = os.environ.get("ALERT_FROM") or os.environ["SMTP_USER"]; msg["To"] = os.environ["ALERT_TO"]
    msg.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT") or "587"), timeout=60) as s:
        s.starttls(); s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(msg)

def main():
    with open(os.path.join(DATA, "radar_out.json")) as f: out = json.load(f)
    title, body, prio = compose(out)
    print(title); print(body)
    sent = []
    if os.environ.get("NTFY_TOPIC"):
        send_ntfy(title, body, prio); sent.append("ntfy")
    if all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_TO")):
        send_email(title, body); sent.append("email")
    print("sent via " + ", ".join(sent) if sent else "no alert channel configured (set NTFY_TOPIC or SMTP_* secrets); printed only")

if __name__ == "__main__":
    main()
