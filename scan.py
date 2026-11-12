#!/usr/bin/env python3
"""Job Radar scanner. Read-only; fixed host allowlist from sources.json; robots.txt honored for HTML pages.

Usage: python3 -I scan.py [ORG ...]
Env:   PROFILE=profiles/kevin.json  RADAR_DATA=data (cache dir)  FULL=1 (re-read every description)  MAX_DETAIL=100000
"""
import json, re, sys, os, time, html, collections, urllib.request, urllib.parse, urllib.robotparser, datetime as dt
from concurrent.futures import ThreadPoolExecutor

# Bump when requirements() extraction changes: forces every description to be re-read instead of reusing cached facts.
RULES_VERSION = "2026-11-12.1"
ROOT = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT, "sources.json")) as _f: SRC = json.load(_f)
TODAY = dt.date.today()
DATA_DIR = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")

def load_profile(path=None):
    with open(path or os.environ.get("PROFILE") or os.path.join(ROOT, "profiles", "kevin.json")) as f: p = json.load(f)
    p["_major"] = re.compile("(?i)" + "|".join(re.escape(m) for m in p["majors"]))
    p["_gradYear"] = int(p["gradDate"][:4])
    p["_start"] = dt.date.fromisoformat(p["earliestStart"])
    return p
PROFILE = load_profile()

def host_of(u): return (urllib.parse.urlparse(u).hostname or "").lower()
ALLOWED = set()
def _hosts(s):
    t = s["type"]; h = lambda u: urllib.parse.urlparse(u).hostname
    if t == "workday": return [f"{s['tenant']}.wd{s['wd']}.myworkdayjobs.com"]
    if t == "eightfold": return [f"{s['tenant']}.eightfold.ai"]
    if t == "sitemap": return [h(u) for u in s["sitemaps"]]
    if t in ("rmk",): return [h(s["base"])]
    if t in ("paylocity", "htmllist"): return [h(s["list"])]
    if t == "oracle": return [s["host"]]
    if t == "bamboo": return [f"{s['id']}.bamboohr.com"]
    if t == "pinpoint": return [f"{s['id']}.pinpointhq.com"]
    if t == "rippling": return ["api.rippling.com"]
    if t == "apl": return ["careers.jhuapl.edu"]
    return []
for s in SRC:
    ALLOWED |= set(_hosts(s))
ALLOWED |= {"boards-api.greenhouse.io", "api.lever.co", "api.ashbyhq.com", "api.smartrecruiters.com"}

class Guard(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        if host_of(newurl) not in ALLOWED: raise RuntimeError(f"blocked redirect to {host_of(newurl)}")
        return super().redirect_request(req, fp, code, msg, hdrs, newurl)
OPENER = urllib.request.build_opener(Guard)
UA = "Mozilla/5.0 (compatible; personal-job-radar/2.0; read-only)"
_robots = {}

def robots_ok(url):
    h = host_of(url)
    if h not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            raw = fetch(f"https://{h}/robots.txt", check_robots=False, text=True)
            rp.parse(raw.splitlines())
        except Exception:
            rp.parse([])
        _robots[h] = rp
    return _robots[h].can_fetch(UA, url)

import threading
_last = {}; _lock = threading.Lock()
SLOW = {"lockheedmartin.eightfold.ai": 1.0, "ngc.eightfold.ai": 1.0}
def _throttle(h):
    gap = SLOW.get(h, 0.15)
    while True:
        with _lock:
            now = time.time(); t = _last.get(h, 0)
            if now - t >= gap: _last[h] = now; return
        time.sleep(gap - (now - t))

def fetch(url, body=None, check_robots=False, text=False, headers=None, tries=4):
    if host_of(url) not in ALLOWED: raise RuntimeError(f"host not allowlisted: {host_of(url)}")
    if check_robots and not robots_ok(url): raise RuntimeError("robots.txt disallows")
    data = json.dumps(body).encode() if body is not None else None
    hd = {"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", **(headers or {})}
    if data: hd["Content-Type"] = "application/json"
    for i in range(tries):
        _throttle(host_of(url))
        try:
            with OPENER.open(urllib.request.Request(url, data=data, headers=hd), timeout=40) as r:
                raw = r.read(100_000_001)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i + 1 < tries: time.sleep(5 * (i + 1) ** 2); continue
            raise
    if len(raw) > 100_000_000: raise RuntimeError("response too large")
    s = raw.decode("utf-8", "replace")
    return s if text else json.loads(s)

FIELD = re.compile(r"(hypersonic|thermal|aerotherm|thermo|heat transfer|propuls|rocket|\bengines?\b|combust|turbine|"
    r"structur|stress|loads|dynamic|vibration|test|aero|cfd|fluid|flight|vehicle|mechanical|mechanism|design engineer|"
    r"nuclear|reactor|fusion|plasma|criticality|radiation|naval|marine|ship|hull|submarine|"
    r"materials|analyst.*(thermal|struct|aero)|launch|payload|integration)", re.I)
NOT_FIELD = re.compile(r"(software|firmware|electrical|electronic|\brf\b|fpga|asic|cyber|network|\bit\b|data (engineer|scien)|"
    r"machine learning|\bai\b|civil|facilit|account|finance|sales|recruit|marketing|legal|counsel|supply chain|buyer|"
    r"procure|technician|machinist|welder|operator|electrician|mechanic\b|planner|scheduler|hr\b|payroll|security officer|"
    r"quality inspector|perception|sensor fusion|computer vision|distribution engineer|substation|power systems engineer|transmission line|utility|signal processing|communications|\bcomms?\b|intern\b|internship|co-?op\b|summer|kubernetes|devops|cloud|database|web\b|\bui\b|project manag|program manag|business|financial|cost |scheduling|estimat|proposal|filter|chemical|chemist|semiconductor|photonic|optical|antenna|power electronics|biolog|environmental health|safety officer|remediation|compliance engineer|curriculum|teaching assistant|security analyst|health and safety|full[- ]stack|site reliability|it infrastructure|infrastructure engineer \(|virtualization|enterprise products|communication|non-kinetic|cable harness|cable interconnect|cable and harness|industrial security|radiation protection tech)", re.I)
NON_US = re.compile(r"(?i)\b(germany|hamburg|munich|berlin|united kingdom|\buk\b|england|stafford|london|italy|torino|france|paris|poland|india|bangalore|bengaluru|canada|toronto|montreal|mexico|netherlands|delft|new zealand|christchurch|australia|japan|singapore|spain|sweden|norway|israel|ireland|czech|romania|brazil|china|korea)\b")
US_HINT = re.compile(r"(?i)united states|\busa?\b|, (al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b")
MGMT = re.compile(r"\b(manager|director|vice president|vp\b|head of|chief|fellow|principal|staff engineer|executive)\b", re.I)
ROLEWORD = re.compile(r"(engineer|scientist|analyst|architect|physicist)", re.I)

def in_scope(title, generic=False):
    base = ROLEWORD.search(title) and not NOT_FIELD.search(title) and not MGMT.search(title)
    return bool(base and (generic or FIELD.search(title)))

def discipline(t):
    t = t.lower()
    for k, rx in [("Thermal", r"therm|heat"), ("Propulsion", r"propul|rocket|\bengines?\b|combust|turbine"),
                  ("Structures", r"(?<!infra)struct|stress|loads|vibrat|dynamic"), ("Test", r"\btest"), ("Nuclear", r"nuclear|reactor|fusion|plasma|critical|radiat"),
                  ("Naval", r"naval|marine|\bship|hull|submarine|vessel"), ("Aero", r"aero|cfd|fluid|flight|hypersonic"),
                  ("Mechanical", r"mechanic|design")]:
        if re.search(rx, t): return k
    return "Other"

def strip_html(s):
    s = html.unescape(s or "")
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</div>|</h\d>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t\r\f\v]+", " ", s)

NUMW = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
YRS = re.compile(r"(?<![\d.])(\d{1,2}|zero|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:\(\d+\)\s*)?(?:\+|or more|plus)?\s*"
                 r"(?:(?:-|–|to)\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs?)\b(?:[^.\n]{0,80}?)\b(experience|exp\b|industry|engineering|relevant|related|work)", re.I)
ZERO_EXP = re.compile(r"(no (prior |professional )?experience (is )?required|\b0\s*(\+)?\s*years|new grad|recent grad|entry[- ]level (position|role|engineer)|early[- ]career (position|role|engineer|program))", re.I)
TITLE_ENTRY = re.compile(r"(?i)(new ?grad|graduate engineer|early[- ]career|entry[- ]level|university grad|college grad|recent grad|\bassociate\b[\w ,&/-]{0,50}?(engineer|scientist|analyst)|(engineer|scientist|analyst|physicist)[\w ,&/()-]{0,50}?\bassociate\b|engineer (i|1)\b|\blevel (i|1)\b|\b(i|1)\s*$|rotational|development program|\bLDP\b|\bEDP\b)")
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"

def requirements(text):
    t = (text or "").replace(chr(8217), "'").replace(chr(8216), "'")
    t = re.sub(r"\bU\.\s?S\.(?=\s|$)", "US", t)
    t = re.sub(r"(?i)\b(zero|one|two|three|four|five|six|seven|eight|nine|ten)\s*\(\d+\)", r"\1", t)
    t = re.sub(r"\((\d{1,2}\s*\+?)\)", r"\1", t)
    req = t
    rq = re.search(r"(?im)^\W*(basic|minimum|required|requirements|qualifications|what you.ll need|what you.ll bring|what qualifications|you have|must have|what we.re looking for|education/experience)\b", t)
    m = re.search(r"(?im)^\W*(preferred|desired|nice[- ]to[- ]have|bonus|plusses|pluses)\b[^\n]{0,45}$", t[rq.end() if rq else 0:])
    if m and (rq or re.search(r"(?i)qualif|skill|experience|requirement", m.group(0))):
        req = t[:(rq.end() if rq else 0) + m.start()]
    nums = []; school_ok = False
    for mm in YRS.finditer(req):
        v = mm.group(1).lower(); v = NUMW.get(v, v)
        try: v = int(v)
        except ValueError: continue
        line_end = len(req)
        for stop in ("\n", ". ", "* ", "•"):
            k = req.find(stop, mm.end())
            if k != -1: line_end = min(line_end, k)
        ctx = req[mm.start():line_end]
        prof = re.search(r"(?i)(professional|industry|post[- ]?grad|full[- ]time|work experience|paid)", req[max(0, mm.start() - 15):mm.end() + 25])
        sch = bool(not prof and re.search(r"(?i)(includ\w*|via|through|from|gained|count|such as|or equivalent|qualif)[^\n]{0,60}(project team|student|research|internship|co-?op|academic|coursework|university|college|school|competition|club|extra-?curricular)", ctx))
        ls = req.rfind("\n", 0, mm.start()) + 1
        tier = bool(re.search(r"(?i)^\W*(level|lvl\.?|tier|grade|band|engineer|scientist|analyst)?\s*(i{1,3}|iv|v|[1-5]|entry|junior|jr\.?|mid|senior|sr\.?|staff|principal)\b[^\n]{0,40}?[:\-–]", req[ls:mm.start()] + ":") or
                    re.search(r"(?i)\b(level|lvl)\s*(i{1,3}|iv|[1-5])\b", req[ls:mm.start()]))
        pre = req[max(ls, mm.start() - 120):mm.start()]
        if re.search(r"(?i)in lieu of|without a (bachelor|degree)|no degree|associate'?s degree|high school|\bged\b|in place of a degree", pre + ctx):
            continue
        if v <= 30: nums.append((v, sch, tier))
    bs_yrs = None
    mb = re.search(r"(?is)bachelor'?s?(?:(?! or )[^.\n]){0,120}?(?:and|with|plus|\+)\s*(?:a minimum of |minimum of |at least )?(\d{1,2}|zero|one|two|three|four|five)\s*\+?\s*(?:-\s*\d+\s*|to \w+\s*)?(?:years?|yrs?)", req)
    if mb:
        v = mb.group(1).lower(); bs_yrs = int(NUMW.get(v, v))
    if nums:
        tiered = [x for x in nums if x[2]]
        lo = min(tiered, key=lambda x: x[0]) if len(tiered) >= 2 else max(nums, key=lambda x: x[0])
        school_ok = lo[1]
    min_years = bs_yrs if bs_yrs is not None else (lo[0] if nums else None)
    if min_years is None and ZERO_EXP.search(t): min_years = 0

    deg = None
    for k, rx in [("PhD", r"\bph\.?d\b[^.\n]{0,40}required|requires? a ph\.?d"), ("MS", r"master'?s (degree )?(is )?required|requires? a master"),
                  ("BS", r"bachelor|b\.s\.|\bbs\b|\bbsc\b|\bbse\b|\bb\.?eng\b|undergraduate degree|4-year degree|four[- ]year degree")]:
        if re.search(rx, req, re.I): deg = k; break
    if re.search(r"(?i)\b(ms|m\.s\.|master'?s)( degree)? (degree )?in [^.\n]{0,80}(and|with) \d", req) and not re.search(r"(?i)bachelor|\bb\.?s\.?\b|\bbsc?\b|\bbse\b|undergraduate", req):
        deg = "MS"

    grad = None
    gm = re.search(rf"(?is)(graduat\w*|degree (conferred|completed|by)|complet\w* (your|their|a) degree)[^.\n]{{0,90}}?(({MONTHS})[a-z]*\.?\s*(20\d\d)|(20\d\d))[^.\n]{{0,60}}", t)
    if gm: grad = re.sub(r"\s+", " ", gm.group(0))[:160]
    start = None
    sm = re.search(rf"(?is)(start date|start dates|available to start|able to start|begin (work|employment|full[- ]time))[^.\n]{{0,80}}?(({MONTHS})[a-z]*\.?\s*(20\d\d)|summer 20\d\d|fall 20\d\d|spring 20\d\d|20\d\d)[^.\n]{{0,40}}", t)
    if sm: start = re.sub(r"\s+", " ", sm.group(0))[:140]

    clr = None
    if re.search(r"(?i)\b(ts/sci|top secret)", t): clr = "TS/SCI"
    elif re.search(r"(?i)\bq\b[ -]?(security )?clearance|doe q\b|\bdoe (l|q) ", t): clr = "DOE Q/L"
    elif re.search(r"(?i)\bsecret\b", t): clr = "Secret"
    elif re.search(r"(?i)security clearance|clearance", t): clr = "Clearance"
    ACTIVE = (r"(?i)(active|current|in-scope|existing)\b[^.\n]{0,60}?clearance[^.\n]{0,30}?\b(is |are )?(required|needed|must)\b|must (currently )?(hold|possess|have) an? (active|current)|"
              r"requires? (the candidate to (hold|have|possess) )?an? (active|current|in-scope)\b[^.\n]{0,40}clearance|requires? the candidate to (hold|have|possess) an? (ts/sci|top secret|secret)")
    act = [m for m in re.finditer(ACTIVE, t) if not re.search(r"(?i)prefer|a plus|desired|nice to have|ability to obtain|able to obtain|eligib",
           t[max(0, m.start() - 60):m.end()] + ("" if re.search(r"(?i)required|needed|must|requires", m.group(0)) else t[m.end():m.end() + 25]))]
    if clr and act:
        clr += " (active req.)"
    elif clr: clr += " (obtain)"

    cit = None
    if re.search(r"(?i)(u\.?s\.?|united states) citizen(ship)? (is |are )?(required|only)|must be an? (u\.?s\.?|united states) citizen|requires? (u\.?s\.?|us) citizenship|citizenship required", t): cit = "US citizen"
    elif re.search(r"(?i)\bitar\b|export control|u\.?s\.? person|us person", t): cit = "US person (ITAR)"
    sw = re.search(r"(?is)(?:start|begin|available|availability|onboard|join)[^.\n]{0,80}?within\s*(\d{1,3})\s*(?:(?:-|–|to)\s*(\d{1,3})\s*)?days?\s*of\s*(?:applying|application|apply|(?:an |the )?offer|being contacted)", t) or \
         re.search(r"(?i)(?:available|able|ready) to (?:start|begin) (?:work |full[- ]time )?immediately|immediate (?:start|availability) (?:is )?required", t)
    start_win = None
    if sw:
        start_win = f"start within {int(sw.group(2) or sw.group(1))} days of applying" if sw.lastindex else "immediate start (within ~30 days)"
        if re.search(r"(?i)(have|has) completed (their|your|all)? ?degree|degree (must be|requirements?) (completed|conferred)|completed their degree requirements", t):
            start_win += "; degree must be finished"
    apply_by = None
    for km in re.finditer(r"(?i)application deadline|deadline (to|for) appl|apply by|applications? (are |will be )?(due|accepted (until|through)|clos\w*)|"
                          r"closing date|close date|posting end date|posting (will )?(close|end)s?|position closes|accepting applications (until|through)|open until", t):
        win = t[km.end():km.end() + 260]
        dm = re.search(rf"(?i)\b(({MONTHS})[a-z]*\.?\s+\d{{1,2}}(st|nd|rd|th)?,?\s+20\d\d|\d{{1,2}}/\d{{1,2}}/20\d\d|20\d\d-\d\d-\d\d)", win)
        if not dm or re.search(r"(?i)until (the )?(position|role|requisition|search)? ?(is )?(filled|closed)|ongoing|qualified pool", win[:dm.start()]): continue
        d = iso(re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", dm.group(1)).replace(".", ""))
        if d and (TODAY - dt.timedelta(days=1)).isoformat() <= d <= (TODAY + dt.timedelta(days=365)).isoformat():
            apply_by = d; break
    g = re.search(r"(?i)\bgpa\b[^.\n]{0,30}?\b([23]\.\d{1,2})\b|\b([23]\.\d{1,2})\s*(?:/\s*4\.0\s*)?(?:or (?:higher|better|above)\s*)?(?:cumulative\s*)?(?:gpa|grade point)", req)
    gpa = (g.group(1) or g.group(2)) if g else None
    return dict(minYears=min_years, schoolExpOk=school_ok, degree=deg, majorSentence=major_sentence(req), gpaReq=gpa, startWindow=start_win, applyBy=apply_by, gradReq=grad, startReq=start, clearance=clr, citizenship=cit)

OTHER_MAJOR = re.compile(r"(?i)(aerospace|aeronautical|astronautical|mechanical|engineering mechanics|nuclear|electrical|electronics?|computer|chemical|civil|structural|materials?|industrial|systems|software|"
    r"manufacturing|biomedical|environmental|petroleum|mining|ocean|naval architecture|marine|radiation health|health)\s*(engineering|science|physics)?|"
    r"physics|chemistry|mathematics|math\b|computer science|naval architecture|accounting|finance|business")
def major_sentence(req):
    """The bachelor's-degree sentence (profile-independent; cached) that major_req() judges against a profile."""
    m = re.search(r"(?is)bachelor'?s?[^.\n]{0,220}", req) or re.search(r"(?is)\b(b\.s\.|bs|bsc|bse)\b[^.\n]{0,200}", req)
    if not m: return None
    return re.split(r"(?i)\b(with|and) (a minimum of |at least |minimum )?(\d|one|two|three|four|five)", m.group(0))[0]

def major_req(profile, sent):
    """None = fine for this profile; 'related: ...' = other majors named 'or related'; 'only: ...' = other majors only."""
    if not sent or profile["_major"].search(sent): return None
    named = sorted({re.sub(r"\s+", " ", x.group(0).strip().lower()) for x in OTHER_MAJOR.finditer(sent)})
    rest = OTHER_MAJOR.sub(" ", sent)
    if profile.get("anyEngineeringOk", True) and re.search(r"(?i)\bengineering\b|\bstem\b|technical (field|discipline|degree)", rest): return None
    if not named: return None
    if re.search(r"(?i)related|equivalent|similar|other (technical|science|engineering)", sent): return "related: " + ", ".join(named)
    return "only: " + ", ".join(named)

def fit(profile, r, title):
    """Judge extracted facts `r` (from requirements()) plus the title for a profile -> (fit, why).
    fit is 'Yes' / 'Maybe' / 'No'. `r['majorReq']` is filled in here if missing."""
    if "majorReq" not in r: r["majorReq"] = major_req(profile, r.get("majorSentence"))
    f, why = _fit(profile, r, title)
    if r.get("gpaReq") and f != "No": why += f"; min GPA {r['gpaReq']}"
    if r.get("applyBy") and f != "No": why += f"; apply by {r['applyBy']}"
    sw = r.get("startWindow")
    if sw and f != "No":
        days = int(re.search(r"\d+", sw).group(0))
        when = profile["_start"] - dt.timedelta(days=days)
        if TODAY < when:
            return "Maybe", f"{why}; {sw} - apply after {when.strftime('%b %-d, %Y')}"
    mj = r.get("majorReq") or ""
    if f == "Yes" and mj.startswith("related:"): return "Maybe", f"{why}; major not named ({mj[9:][:30]} or related)"
    return f, why

def _fit(profile, r, title):
    gy = profile["_gradYear"]; prev = str(gy - 1)
    y = r["minYears"]; entry = bool(TITLE_ENTRY.search(title)) or bool(re.search(rf"\b{gy}\b", title))
    senior = bool(re.search(r"(?i)\b(senior|sr\.?|lead|iii|iv|v|level [3-9])\b|\b[3-9]\s*$", title)) and not re.search(rf"\b{gy}\b", title)
    if r["degree"] in ("MS", "PhD") and r["degree"] != profile.get("degree"): return "No", f"{r['degree']} required"
    mj = r.get("majorReq") or ""
    if mj.startswith("only:"): return "No", "degree must be " + mj[6:][:40]
    if r["clearance"] and "active req" in r["clearance"] and not (profile.get("clearance") or {}).get("active"): return "No", "active clearance required"
    if r.get("citizenship") and profile.get("citizenship", "US") != "US": return "No", r["citizenship"] + " required"
    for k in ("gradReq", "startReq"):
        s = r.get(k) or ""
        yrs = [int(x) for x in re.findall(r"20\d\d", s)]
        if yrs and max(yrs) < gy and not re.search(r"(?i)between|through|or later|or after", s):
            return "No", ("grad window ends " if k == "gradReq" else "start ") + str(max(yrs))
    strong = bool(re.search(rf"(?i)\b{gy}\b|new ?grad|early[- ]career|entry[- ]level|recent grad|university grad|college grad|rotational|development program", title))
    if y is not None and y >= 2:
        if r.get("schoolExpOk") and y <= 3: return "Maybe", f"{y}+ yrs, but school/internship exp counts"
        if strong and y <= 3: return "Maybe", f"new-grad title but {y}+ yrs listed"
        return "No", f"{y}+ yrs required"
    if re.search(rf"\b{prev}\b", title) and not re.search(rf"\b{gy}\b|'{str(gy)[2:]}", title): return "Maybe", f"{prev} new-grad cycle - check grad window"
    note = f"{gy} grads named" if re.search(str(gy), (r.get("gradReq") or "") + (r.get("startReq") or "") + title) else ""
    if senior and not strong: return "No", "senior title"
    if entry: return "Yes", note or "new-grad / entry title"
    if y == 0: return "Yes", note or ("school/internship exp counts" if r.get("schoolExpOk") else "0 yrs required")
    if y == 1 and r.get("schoolExpOk"): return "Yes", "1 yr; school/internship exp counts"
    if y == 1: return "Maybe", "1 yr required"
    if re.search(r"(?i)\b(ii|2)\s*$|\b(ii|2)\b", title): return "Maybe", "level II, yrs not stated"
    return "Maybe", note or "yrs not stated"

def iso(x):
    if x in (None, ""): return None
    if isinstance(x, (int, float)): return dt.datetime.fromtimestamp(x / 1000, dt.timezone.utc).date().isoformat()
    x = str(x).strip()
    if re.match(r"\d{4}-\d\d-\d\d", x): return x[:10]
    if re.match(r"\d{4}/\d\d/\d\d", x): return x[:10].replace("/", "-")
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", x)
    if m: return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    for f in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y", "%d %b %Y", "%a %b %d %H:%M:%S %Y"):
        try: return dt.datetime.strptime(x.replace("UTC ", ""), f).date().isoformat()
        except ValueError: pass
    return None

def a_greenhouse(s):
    j = fetch(f"https://boards-api.greenhouse.io/v1/boards/{s['id']}/jobs?content=true")
    for p in j.get("jobs", []):
        yield dict(title=p.get("title", ""), location=(p.get("location") or {}).get("name", ""), url=p.get("absolute_url"),
                   date=iso(p.get("first_published")), dateKind="posted" if p.get("first_published") else None,
                   desc=strip_html(p.get("content", "")))

def a_rippling(s):
    base = f"https://api.rippling.com/platform/api/ats/v1/board/{s['id']}/jobs"
    for p in fetch(base):
        u = p.get("uuid")
        wl = p.get("workLocation") or {}
        yield dict(title=p.get("name", ""), location=wl.get("label", "") if isinstance(wl, dict) else str(wl), url=p.get("url"),
                   date=None, dateKind=None, rip=lambda u=u: fetch(f"{base}/{u}"))

def a_oracle(s):
    h, site = s["host"], s["site"]
    seen = set()
    for kw in ["engineer", "analyst", "scientist"]:
        url = (f"https://{h}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList"
               f"&finder=findReqs;siteNumber={site},keyword={kw},limit=200,sortBy=POSTING_DATES_DESC")
        items = fetch(url).get("items", [])
        for p in (items[0].get("requisitionList", []) if items else []):
            rid = p.get("Id")
            if rid in seen: continue
            seen.add(rid)
            yield dict(title=p.get("Title", ""), location=p.get("PrimaryLocation", ""), url=f"https://{h}/hcmUI/CandidateExperience/en/sites/{site}/job/{rid}",
                       date=iso(p.get("PostedDate")), dateKind="posted",
                       desc=lambda rid=rid: _ora(h, site, rid))
def _ora(h, site, rid):
    j = fetch(f'https://{h}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true&finder=ById;Id="{rid}",siteNumber={site}')
    it = (j.get("items") or [{}])[0]
    end = str(it.get("ExternalPostedEndDate") or "")[:10]
    return strip_html(" ".join(str(it.get(k) or "") for k in ("ExternalDescriptionStr", "ExternalQualificationsStr", "ExternalResponsibilitiesStr", "CorporateDescriptionStr"))) + (f"\nPosting end date: {end}" if end else "")

EF_TERMS = ["thermal engineer", "structural engineer", "stress engineer", "test engineer", "propulsion engineer", "mechanical engineer",
            "aerospace engineer", "aerodynamics", "hypersonic", "nuclear engineer", "early career engineer", "associate engineer", "engineer 2027"]
def a_eightfold(s):
    t, d = s["tenant"], s["domain"]; seen = set()
    for term in s.get("terms", EF_TERMS):
        for start in range(0, s.get("pages", 6) * 10, 10):
            q = urllib.parse.urlencode({"domain": d, "query": term, "start": start, "sort_by": "timestamp"})
            P = fetch(f"https://{t}.eightfold.ai/api/pcsx/search?{q}").get("data", {}).get("positions", [])
            for p in P:
                if p["id"] in seen: continue
                seen.add(p["id"])
                pid = p["id"]
                def det(pid=pid):
                    dd = fetch(f"https://{t}.eightfold.ai/api/pcsx/position_details?position_id={pid}&domain={d}&hl=en").get("data", {})
                    extra = " ".join(f"{k[12:]}: {v}" for k, v in dd.items() if k.startswith("efcustomText") and isinstance(v, (str, list)) and re.search(r"(?i)clearance|experience|citizen|degree", k))
                    return strip_html(dd.get("jobDescription", "")) + " " + extra
                yield dict(title=p.get("name", ""), location="; ".join(p.get("locations") or [])[:80],
                           url=p.get("publicUrl") or f"https://{t}.eightfold.ai/careers/job/{pid}",
                           date=dt.datetime.fromtimestamp(p.get("creationTs") or p["postedTs"], dt.timezone.utc).date().isoformat() if (p.get("creationTs") or p.get("postedTs")) else None,
                           dateKind="posted" if (p.get("creationTs") or p.get("postedTs")) else None, desc=det)
            if len(P) < 10: break

def a_rmk(s):
    base = s["base"]; seen = set()
    for q in s.get("terms", ["engineer", "analyst", "scientist"]):
        for start in range(0, 500, 25):
            page = fetch(f"{base}/search/?q={urllib.parse.quote(q)}&startrow={start}", text=True, check_robots=True)
            links = re.findall(r'href="(/job/[^"]+/\d+/)"[^>]*>([^<]+)<', page)
            if not links: break
            for path, title in links:
                if path in seen: continue
                seen.add(path)
                yield dict(title=html.unescape(title.strip()), location="", url=base + path, date=None, dateKind=None, page=True)
            if len(set(p for p, _ in links)) < 20: break

def a_pinpoint(s):
    for p in fetch(f"https://{s['id']}.pinpointhq.com/postings.json").get("data", []):
        loc = p.get("location") or {}
        yield dict(title=p.get("title", ""), location=", ".join(x for x in [loc.get("city"), loc.get("province")] if x) if isinstance(loc, dict) else "",
                   url=p.get("url"), date=None, dateKind=None, page=True)

def a_bamboo(s):
    base = f"https://{s['id']}.bamboohr.com/careers"
    for p in fetch(f"{base}/list").get("result", []):
        jid = p.get("id"); loc = p.get("location") or {}
        yield dict(title=p.get("jobOpeningName", ""), location=", ".join(x for x in [loc.get("city"), loc.get("state")] if x) if isinstance(loc, dict) else "",
                   url=f"{base}/{jid}", date=None, dateKind=None, bamboo=lambda jid=jid: fetch(f"{base}/{jid}/detail").get("result", {}).get("jobOpening", {}))

def a_paylocity(s):
    page = fetch(s["list"], text=True, check_robots=True)
    m = re.search(r"window\.pageData\s*=\s*(\{.*?\});\s*\n", page, re.S)
    for p in (json.loads(m.group(1)).get("Jobs", []) if m else []):
        yield dict(title=p.get("JobTitle", ""), location=p.get("LocationName", ""),
                   url=f"https://recruiting.paylocity.com/Recruiting/Jobs/Details/{p.get('JobId')}",
                   date=iso(p.get("PublishedDate")), dateKind="posted" if p.get("PublishedDate") else None, page=True)

def a_htmllist(s):
    seen = set()
    for i in range(s.get("maxpages", 40)):
        page = fetch(s["list"].format(i=i), text=True, check_robots=True)
        found = [(u, html.unescape(t).strip()) for u, t in re.findall(s["linkrx"], page)]
        new = list({u: (u, t) for u, t in found if u not in seen}.values())
        if not new: break
        for u, t in new:
            seen.add(u)
            yield dict(title=re.sub(r"\s+", " ", t), location="", url=u, date=None, dateKind=None, page=True)

def a_apl(s):
    seen = set()
    for kw in ["engineer", "2027", "entry level"]:
        q = urllib.parse.urlencode({"keywords": kw, "sortBy": "posted_date", "descending": "true", "limit": 100})
        for item in fetch(f"https://careers.jhuapl.edu/api/jobs?{q}").get("jobs", []):
            p = item.get("data", item); rid = p.get("req_id")
            if rid in seen: continue
            seen.add(rid)
            yield dict(title=p.get("title", ""), location="Laurel, MD", url=p.get("apply_url") or f"https://careers.jhuapl.edu/jobs/{rid}",
                       date=iso(p.get("posted_date")), dateKind="posted",
                       desc=lambda p=p: strip_html((p.get("description") or "") + " " + (p.get("qualifications") or "")))

def a_lever(s):
    for p in fetch(f"https://api.lever.co/v0/postings/{s['id']}?mode=json"):
        yield dict(title=p.get("text", ""), location=(p.get("categories") or {}).get("location", ""), url=p.get("hostedUrl"),
                   date=iso(p.get("createdAt")), dateKind="posted",
                   desc=lambda p=p: (p.get("descriptionPlain") or "") + "\n" + "\n".join(
                       l.get("text", "") + "\n" + strip_html(l.get("content", "")) for l in p.get("lists", [])) + "\n" + (p.get("additionalPlain") or ""))

def a_ashby(s):
    j = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{s['id']}")
    for p in j.get("jobs", []):
        yield dict(title=p.get("title", ""), location=p.get("location", ""), url=p.get("jobUrl"),
                   date=iso(p.get("publishedAt")), dateKind="posted",
                   desc=lambda p=p: p.get("descriptionPlain") or strip_html(p.get("descriptionHtml", "")))

def a_smartrecruiters(s):
    off = 0
    while off < 1000:
        j = fetch(f"https://api.smartrecruiters.com/v1/companies/{s['id']}/postings?limit=100&offset={off}")
        for p in j.get("content", []):
            u = f"https://api.smartrecruiters.com/v1/companies/{s['id']}/postings/{p['id']}"
            loc = p.get("location") or {}
            yield dict(title=p.get("name", ""), location=", ".join(x for x in [loc.get("city"), loc.get("region")] if x),
                       url=f"https://jobs.smartrecruiters.com/{s['id']}/{p['id']}", date=iso(p.get("releasedDate")), dateKind="posted",
                       desc=lambda u=u: " ".join(strip_html(v.get("text", "")) for v in (fetch(u).get("jobAd", {}).get("sections", {}) or {}).values()))
        off += 100
        if off >= j.get("totalFound", 0): break

WD_TERMS = ["engineer", "thermal engineer", "structural engineer", "test engineer", "propulsion engineer", "mechanical engineer",
            "aerospace engineer", "nuclear engineer", "naval architect", "stress engineer", "associate engineer", "engineer I", "2027"]
def a_workday(s):
    t, n, site = s["tenant"], s["wd"], s["site"]
    base = f"https://{t}.wd{n}.myworkdayjobs.com"
    seen = set()
    for term in s.get("terms", WD_TERMS):
        for off in (0, 20, 40):
            j = fetch(f"{base}/wday/cxs/{t}/{site}/jobs", {"appliedFacets": {}, "limit": 20, "offset": off, "searchText": term})
            posts = j.get("jobPostings", [])
            for p in posts:
                path = p.get("externalPath", "")
                if not path or path in seen: continue
                seen.add(path)
                def det(path=path):
                    d = fetch(f"{base}/wday/cxs/{t}/{site}{path}").get("jobPostingInfo", {})
                    return d
                yield dict(title=p.get("title", ""), location=p.get("locationsText", ""), url=f"{base}/en-US/{site}{path}",
                           date=None, dateKind=None, wd=det)
            if len(posts) < 20: break

def jsonld_jobs(page):
    out = []
    for blk in re.findall(r'(?is)<script[^>]+application/ld(?:\+|&#x2B;|&#43;|%2B)json[^>]*>(.*?)</script>', page):
        try: d = json.loads(blk.strip())
        except Exception: continue
        for x in (d if isinstance(d, list) else d.get("@graph", [d])):
            if isinstance(x, dict) and x.get("@type") == "JobPosting": out.append(x)
    return out

def a_sitemap(s):
    urls = []
    for sm in s["sitemaps"]:
        xml = fetch(sm, check_robots=False, text=True)
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
        subs = [l for l in locs if l.endswith(".xml") or "sitemap" in l.lower()]
        for sub in subs[:30]:
            if host_of(sub) in ALLOWED:
                try: locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", fetch(sub, text=True))
                except Exception: pass
        rx = re.compile(s.get("jobrx", r"/jobs?/"), re.I)
        urls += [l for l in locs if rx.search(l) and host_of(l) in ALLOWED]
    for u in dict.fromkeys(urls):
        slug_all = urllib.parse.unquote(u).replace("-", " ")
        yield dict(title=None, slug=slug_all, location="", url=u, date=None, dateKind=None, page=True)


ADAPT = dict(paylocity=a_paylocity, htmllist=a_htmllist, pinpoint=a_pinpoint, bamboo=a_bamboo, rmk=a_rmk, eightfold=a_eightfold, rippling=a_rippling, oracle=a_oracle, apl=a_apl, greenhouse=a_greenhouse, lever=a_lever, ashby=a_ashby, smartrecruiters=a_smartrecruiters, workday=a_workday, sitemap=a_sitemap)

MAX_DETAIL = int(os.environ.get("MAX_DETAIL", "100000"))
FACT_KEYS = ("minYears", "schoolExpOk", "degree", "majorSentence", "gpaReq", "startWindow", "applyBy", "gradReq", "startReq", "clearance", "citizenship")
DESC_FIELD = re.compile(r"(?i)(thermal|structur|stress|propuls|aerodynam|aerospace|mechanical engineer|nuclear|reactor|naval|marine|hull|test engineer|fluid|heat transfer)")

def needs_fetch(row):
    """True if the description is not already in hand (an extra request per posting)."""
    return callable(row.get("desc")) or any(row.get(k) for k in ("wd", "bamboo", "rip", "page"))

def enrich(s, row):
    if row.get("wd"):
        d = row.pop("wd")()
        row["title"] = d.get("title", row["title"])
        row["date"] = iso(d.get("startDate")); row["dateKind"] = "posted" if row["date"] else None
        row["desc"] = strip_html(d.get("jobDescription", "")) + (f"\nPosting end date: {d['endDate'][:10]}" if d.get("endDate") else "")
        return row
    if row.get("bamboo"):
        d = row.pop("bamboo")()
        row["desc"] = strip_html(d.get("description", "")) + " " + str(d.get("minimumExperience") or "")
        row["date"] = iso(d.get("datePosted")); row["dateKind"] = "posted" if row["date"] else None
        return row
    if row.get("rip"):
        d = row.pop("rip")()
        desc = d.get("description") or {}
        row["desc"] = strip_html(" ".join(str(v) for v in desc.values()) if isinstance(desc, dict) else str(desc))
        row["date"] = iso(d.get("createdOn")); row["dateKind"] = "posted" if row["date"] else None
        return row
    if row.get("page"):
        page = fetch(row.get("pageurl", row["url"]), text=True, check_robots=True)
        jl = jsonld_jobs(page)
        if jl:
            j = jl[0]
            row["title"] = row.get("title") or html.unescape(j.get("title", ""))
            row["date"] = iso(j.get("datePosted")); row["dateKind"] = "posted" if row["date"] else None
            loc = j.get("jobLocation") or {}
            if isinstance(loc, list): loc = loc[0] if loc else {}
            a = (loc or {}).get("address", {}) if isinstance(loc, dict) else {}
            if isinstance(a, dict): row["location"] = row["location"] or ", ".join(x for x in [a.get("addressLocality"), a.get("addressRegion")] if x)
            row["desc"] = strip_html(j.get("description", "")) + (f"\nPosting end date: {str(j['validThrough'])[:10]}" if j.get("validThrough") else "")
        md = re.search(r'itemprop="datePosted"[^>]*content="([^"]+)"', page) or re.search(r'\bpostedDate\s*[=:]\s*["\']([^"\']{6,40})["\']', page)
        if md and not row.get("date"):
            row["date"] = iso(md.group(1)); row["dateKind"] = "posted" if row["date"] else None
        if not jl:
            mt = re.search(r"(?is)<title>(.*?)</title>", page)
            row["title"] = row.get("title") or (html.unescape(mt.group(1)).split("|")[0].strip() if mt else "")
            row["desc"] = strip_html(page)
        return row
    d = row.get("desc")
    row["desc"] = d() if callable(d) else (d or "")
    return row

def load_cache():
    """{'rulesVersion', 'lastFullRead', 'postings': {url: entry}}. An entry holds the facts extracted from one posting's
    description (never the description itself), its list data, and firstSeen/lastSeen dates."""
    try:
        with open(CACHE_FILE) as f: c = json.load(f)
    except Exception: c = {}
    c.setdefault("postings", {}); c.setdefault("rulesVersion", None); c.setdefault("lastFullRead", None)
    if not c["postings"]:  # one-time import of the old seen.json (first-seen dates) if it is around
        try:
            with open(os.path.join(DATA_DIR, "seen.json")) as f: seen = json.load(f)
            for u, first in seen.items():
                c["postings"][u] = dict(firstSeen=first, lastSeen=first, legacy=True)
        except Exception: pass
    return c

def full_read_due(cache, force=False):
    if force or os.environ.get("FULL") == "1": return "forced"
    if cache.get("rulesVersion") != RULES_VERSION: return f"rules {cache.get('rulesVersion')} -> {RULES_VERSION}"
    if TODAY.weekday() == 6: return "weekly (Sunday)"
    return None

def run_source(s, cache=None, full=False, profile=PROFILE):
    """Read one organization's board. Returns (source, rows, status, entries) where entries are the cache entries
    (keyed by URL) for every in-scope posting listed this run."""
    cache = cache if cache is not None else {}
    t0 = time.time(); rows = []; err = None; total = 0; detailed = 0; reused = 0; entries = {}
    try:
        for row in ADAPT[s["type"]](s):
            total += 1
            title_for_scope = row.get("title") or row.get("slug") or ""
            if not in_scope(title_for_scope, s.get("generic")): continue
            u = row["url"]
            c = cache.get(u)
            if c and not full and c.get("facts") and needs_fetch(row) and c.get("company") == s["org"]:
                # Facts already extracted from this posting: reuse them, refresh list-level fields, skip the detail fetch.
                e = dict(c); e["title"] = row.get("title") or c.get("title") or ""
                e["location"] = row.get("location") or c.get("location") or ""
                if row.get("date"): e["date"], e["dateKind"] = row["date"], row.get("dateKind")
                reused += 1
            else:
                if detailed >= MAX_DETAIL: continue
                try:
                    row = enrich(s, row); detailed += 1
                except Exception as ex:
                    row.setdefault("desc", ""); row["detail_err"] = str(ex)[:80]
                if not row.get("title"): continue
                desc = row.get("desc") or ""
                e = dict(title=row["title"], location=row.get("location") or "", date=row.get("date"), dateKind=row.get("dateKind"),
                         desc_ok=bool(desc), detail_err=row.get("detail_err"), fieldInDesc=bool(DESC_FIELD.search(desc[:4000])),
                         facts=requirements(desc), firstSeen=(c or {}).get("firstSeen"))
            e.update(company=s["org"], sector=s["sector"], url=u, lastSeen=TODAY.isoformat()); e.pop("legacy", None)
            e["title"] = re.sub(r"(?i)\s*job details\s*$", "", e["title"]).strip()
            entries[u] = e
            if not in_scope(e["title"], s.get("generic")): continue
            if NON_US.search(e["location"]) and not US_HINT.search(e["location"]): continue
            if s.get("generic") and not FIELD.search(e["title"]) and not e.get("fieldInDesc"): continue
            disc = discipline(e["title"])
            if profile.get("fields") and disc != "Other" and disc not in profile["fields"]: continue
            rq = dict(e["facts"])
            if rq.get("applyBy") and rq["applyBy"] < TODAY.isoformat(): rq["applyBy"] = None  # deadline passed, posting still up
            f, why = fit(profile, rq, e["title"])
            rows.append(dict(company=s["org"], sector=s["sector"], title=e["title"], location=e["location"].strip(), url=u,
                             date=e.get("date"), dateKind=e.get("dateKind"), discipline=disc, **rq, fit=f, why=why,
                             desc_ok=bool(e.get("desc_ok")), firstSeen=e.get("firstSeen")))
    except Exception as ex:
        err = f"{type(ex).__name__}: {ex}"[:200]
    st = dict(org=s["org"], type=s["type"], ok=err is None, total=total, matches=len(rows), fetched=detailed, cached=reused, error=err, secs=round(time.time() - t0))
    return s, rows, st, entries

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    only = set(a for a in argv if not a.startswith("--"))
    srcs = [s for s in SRC if not only or s["org"] in only]
    cache = load_cache()
    had_state = bool(cache["postings"])  # first ever run: nothing is "new", just unknown
    full = full_read_due(cache, force="--full" in argv)
    print(f"profile {PROFILE['slug']}; rules {RULES_VERSION}; cache {len(cache['postings'])} postings; "
          f"{'FULL re-read: ' + full if full else 'incremental'}")
    roles, status = [], []
    with ThreadPoolExecutor(32) as ex:
        for s, rows, st, entries in ex.map(lambda s: run_source(s, cache["postings"], bool(full)), srcs):
            status.append(st); roles += rows
            if st["ok"]:  # the board answered: postings it no longer lists are closed
                for u in [u for u, e in cache["postings"].items() if e.get("company") == s["org"] and u not in entries]:
                    del cache["postings"][u]
            cache["postings"].update(entries)
    now = TODAY.isoformat()
    stale = (TODAY - dt.timedelta(days=60)).isoformat()
    for u in [u for u, e in cache["postings"].items() if (e.get("lastSeen") or "") < stale]: del cache["postings"][u]
    recent = {now, (TODAY - dt.timedelta(days=1)).isoformat(), (TODAY - dt.timedelta(days=2)).isoformat()}
    for st in status:
        mine = [r for r in roles if r["company"] == st["org"] and r.get("dateKind") == "posted"]
        if not mine: continue
        top, cnt = collections.Counter(r["date"] for r in mine).most_common(1)[0]
        if len(mine) >= 5 and cnt / len(mine) >= 0.8 and top < (TODAY - dt.timedelta(days=90)).isoformat():
            st["placeholderDate"] = top
            for r in mine:
                if r["date"] == top: r["date"], r["dateKind"] = None, None
            continue
        if cnt >= 10 and cnt / len(mine) >= 0.3 and top not in recent:
            st["bulkImport"] = top
            for r in mine:
                if r["date"] == top: r["dateKind"] = "on or before"
            continue
        if len(mine) >= 15 and sum(r["date"] in recent for r in mine) / len(mine) >= 0.6:
            st["refreshes"] = True
            for r in mine: r["dateKind"] = "refreshed"
    for r in roles:
        e = cache["postings"].get(r["url"]) or {}
        first = e.get("firstSeen") or now
        e["firstSeen"] = r["firstSeen"] = first
        if not r.get("date"):
            r["date"], r["dateKind"] = first, "first seen"
        r.pop("majorSentence", None)
    fitrank = {"Yes": 0, "Maybe": 1, "No": 2}
    roles.sort(key=lambda r: (fitrank.get(r["fit"], 3), r["date"] or ""), reverse=False)
    roles.sort(key=lambda r: r["date"] or "", reverse=True)
    roles.sort(key=lambda r: fitrank.get(r["fit"], 3))
    for i, r in enumerate(roles): r["id"] = f"r{i+1:04d}"
    yday = (TODAY - dt.timedelta(days=1)).isoformat()
    new = [r for r in roles if r["fit"] != "No" and ((r["dateKind"] == "posted" and r["date"] in (now, yday)) or
           (r["dateKind"] in ("first seen", "refreshed") and r["firstSeen"] == now and had_state))]
    if not only:  # a partial run (ORG args) must not count as a full read
        cache["rulesVersion"] = RULES_VERSION
        if full: cache["lastFullRead"] = now
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "radar_out.json"), "w") as f:
        json.dump(dict(scanned=dt.datetime.now(dt.timezone.utc).isoformat(), profile=PROFILE["slug"], rulesVersion=RULES_VERSION,
                       fullRead=full or None, roles=roles, new=new, status=status), f, indent=1)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, separators=(",", ":"))
    ok = sum(s["ok"] for s in status)
    print(f"{len(roles)} in-field roles ({sum(r['fit']=='Yes' for r in roles)} Yes, {sum(r['fit']=='Maybe' for r in roles)} Maybe), "
          f"{len(new)} new, {ok}/{len(status)} sources OK, {sum(s['fetched'] for s in status)} descriptions fetched, "
          f"{sum(s['cached'] for s in status)} reused from cache")
    for s in status:
        if not s["ok"]: print("FAIL", s["org"], s["error"])

if __name__ == "__main__":
    main()
