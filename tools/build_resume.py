"""Build a tailored resume from the master .docx with a small edit plan, then export a PDF with LibreOffice.

  build_resume.py dump  master.docx                      -> paragraphs as JSON (index, kind, left/right text)
  build_resume.py apply master.docx plan.json out.docx   -> edited .docx (formatting kept; right-aligned dates kept)
  build_resume.py pdf   out.docx [outdir]                -> normalizes right alignment (tools/normalize_tabs.py), runs soffice,
                                                            prints the PDF path and page count

Plan (all indices refer to the dump of the master, i.e. the original order):
  {"set": {"15": "Thermal Engineering Lead, Founding Member ⟶ Jun 2025 – Present"},   # "⟶" splits left / right-aligned text
   "delete": [33],
   "insert_after": {"11": ["New bullet text"]},                                        # clones the formatting of paragraph 11
   "move": [{"range": [14, 18], "after": 25}]}                                           # whole blocks, applied last
Text is plain; the tool escapes it. Never invents anything: it only writes what the plan says.
"""
import html, json, os, re, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import normalize_tabs

P_RX = re.compile(r"<w:p[ >].*?</w:p>", re.S)
R_RX = re.compile(r"<w:r[ >].*?</w:r>", re.S)
T_RX = re.compile(r"<w:t(?: xml:space=\"preserve\")?>([^<]*)</w:t>")
SEP = "⟶"
TEXTW = 10800  # letter page, 0.5 in margins (set from the document in apply())

def read(path):
    z = zipfile.ZipFile(path); return z, z.read("word/document.xml").decode("utf8")

def write(z, xml, out):
    zo = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    for it in z.infolist(): zo.writestr(it, xml.encode("utf8") if it.filename == "word/document.xml" else z.read(it.filename))
    zo.close()

def rpr(run):
    m = re.search(r"<w:rPr>.*?</w:rPr>", run, re.S); return m.group(0) if m else ""

def ppr(p):
    m = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S); return m.group(0) if m else ""

TOK_RX = re.compile(r"<w:tab/>|<w:t(?: [^>]*)?>([^<]*)</w:t>")
def tokens(p):
    """The paragraph's text in order: '\t' for a tab, else the run text (unescaped)."""
    out = []
    for r in R_RX.findall(p):
        for m in TOK_RX.finditer(r): out.append("\t" if m.group(0) == "<w:tab/>" else html.unescape(m.group(1)))
    return out

def parts(p):
    """(left text, right text or None). The right-aligned part is what follows the LAST padding stretch (2+ tabs or 5+
    spaces, Word's way of pushing dates to the margin); a lone tab inside the left text is just a gap."""
    toks = tokens(p); s = "".join(toks)
    if '<w:tab w:val="right"' in p and "\t" in s:  # our own layout: one tab at a right tab stop
        i = s.rindex("\t"); return re.sub(r"\s+", " ", s[:i]).strip(), s[i + 1:].strip()
    best = None
    for m in re.finditer(r"(?:\t[\t ]*\t|\t? {5,}\t?|\t)[\t ]*", s):
        if m.end() < len(s) and s[m.end():].strip() and (m.group(0).count("\t") >= 2 or re.search(r" {5,}", m.group(0))): best = m
    if best: return re.sub(r"\s+", " ", s[:best.start()]).strip(), s[best.end():].strip()
    return re.sub(r"\s+", " ", s).strip(), None

def padded(p):
    """True when a right part exists and is still pushed by tabs/spaces rather than a tab stop of our own."""
    return parts(p)[1] is not None and "<w:tab w:val=\"right\"" not in p

def kind(p):
    body = p.split("</w:pPr>")[-1]
    return "bullet" if "<w:numPr>" in p else "heading" if ("<w:pBdr>" in p or "<w:u " in body) else "bold" if "<w:b/>" in body[:500] else "text"

def dump(path):
    _, xml = read(path); out = []
    for i, p in enumerate(P_RX.findall(xml)):
        l, r = parts(p); out.append(dict(index=i, kind=kind(p), text=l + (f" {SEP} {r}" if r else "")))
    return out

def text_runs(p):
    return [r for r in R_RX.findall(p) if T_RX.search(r) and T_RX.search(r).group(1).strip()]

def set_text(p, new):
    """Rewrite a paragraph's runs to say `new`, keeping its pPr, the first text run's formatting for the left part, the last
    text run's formatting for the right-aligned part, and a bold label prefix ("Coursework:") when the new text keeps it."""
    left, right = (new.split(SEP, 1) + [None])[:2] if SEP in new else (new, None)
    left = left.strip(); right = right.strip() if right else None
    runs = text_runs(p); first = rpr(runs[0]) if runs else ""; last = rpr(runs[-1]) if runs else first
    label = html.unescape(T_RX.search(runs[0]).group(1)) if runs else ""
    out = []
    if len(runs) >= 2 and label.strip() and left.startswith(label.rstrip()) and rpr(runs[0]) != rpr(runs[1]):
        out.append(f"<w:r>{first}<w:t xml:space=\"preserve\">{html.escape(label, quote=False)}</w:t></w:r>")
        out.append(f"<w:r>{rpr(runs[1])}<w:t xml:space=\"preserve\">{html.escape(left[len(label):], quote=False)}</w:t></w:r>")
    else:
        out.append(f"<w:r>{first}<w:t xml:space=\"preserve\">{html.escape(left, quote=False)}</w:t></w:r>")
    pp = ppr(p)
    if right is not None:
        out.append(f"<w:r>{last}<w:tab/></w:r><w:r>{last}<w:t xml:space=\"preserve\">{html.escape(right, quote=False)}</w:t></w:r>")
        if "<w:tabs>" not in pp: pp = normalize_tabs.add_stop("<w:p>" + (pp or "<w:pPr></w:pPr>") + "</w:p>", TEXTW)[5:-6]
    head = re.match(r"<w:p(?: [^>]*)?>", p).group(0)
    return head + pp + "".join(out) + "</w:p>"

def apply(master, plan, out):
    global TEXTW
    z, xml = read(master); ps = P_RX.findall(xml)
    pg = re.search(r'<w:pgSz w:w="(\d+)"', xml); mar = re.search(r'<w:pgMar [^>]*w:right="(\d+)"[^>]*w:left="(\d+)"', xml)
    if pg and mar: TEXTW = int(pg.group(1)) - int(mar.group(1)) - int(mar.group(2))
    spans = [(m.start(), m.end()) for m in P_RX.finditer(xml)]
    blocks = [[p] for p in ps]  # per original index: the paragraph(s) that replace it
    for k, v in (plan.get("set") or {}).items(): blocks[int(k)] = [set_text(ps[int(k)], v)]
    for k, texts in (plan.get("insert_after") or {}).items():
        i = int(k); blocks[i] = blocks[i] + [set_text(ps[i], t) for t in texts]
    for i in plan.get("delete") or []: blocks[int(i)] = []
    order = list(range(len(ps)))
    for mv in plan.get("move") or []:
        a, b = mv["range"]
        if a <= mv["after"] <= b: continue  # a block cannot be moved after itself
        seg = [i for i in order if a <= i <= b]; rest = [i for i in order if not (a <= i <= b)]
        at = rest.index(mv["after"]) + 1 if mv["after"] in rest else len(rest); order = rest[:at] + seg + rest[at:]
    for i in order:  # every date line gets a real right tab stop, so LibreOffice and Word lay it out the same
        blocks[i] = [set_text(b, f"{parts(b)[0]} {SEP} {parts(b)[1]}") if padded(b) else b for b in blocks[i]]
    body = "".join("".join(blocks[i]) for i in order)
    new_xml = xml[:spans[0][0]] + body + xml[spans[-1][1]:]
    write(z, new_xml, out); return len(order)

def pdf(docx, outdir=None):
    outdir = outdir or os.path.dirname(os.path.abspath(docx)) or "."; os.makedirs(outdir, exist_ok=True)
    norm = os.path.join(outdir, "_norm_" + os.path.basename(docx))
    z, xml = read(docx)
    pg = re.search(r'<w:pgSz w:w="(\d+)"', xml); mar = re.search(r'<w:pgMar [^>]*w:right="(\d+)"[^>]*w:left="(\d+)"', xml)
    textw = int(pg.group(1)) - int(mar.group(1)) - int(mar.group(2)) if pg and mar else 10800
    xml, n = normalize_tabs.normalize(xml, textw); write(z, xml, norm)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, norm], check=True, capture_output=True, timeout=180)
    produced = os.path.join(outdir, os.path.splitext(os.path.basename(norm))[0] + ".pdf")
    final = os.path.join(outdir, os.path.splitext(os.path.basename(docx))[0] + ".pdf"); os.replace(produced, final); os.remove(norm)
    info = subprocess.run(["pdfinfo", final], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1)) if re.search(r"Pages:\s+(\d+)", info) else -1
    return final, pages, n

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dump": print(json.dumps(dump(sys.argv[2]), ensure_ascii=False, indent=1))
    elif cmd == "apply":
        with open(sys.argv[3]) as f: plan = json.load(f)
        print("paragraphs:", apply(sys.argv[2], plan, sys.argv[4]))
    elif cmd == "pdf":
        final, pages, n = pdf(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None); print(f"{final} pages={pages} normalized_lines={n}")
    else: print(__doc__)
