"""Turn Word-only right alignment (default-stop tabs + runs of spaces) into one right tab stop per line, so the file lays out
the same in Word and LibreOffice. Usage: normalize_tabs.py in.docx out.docx"""
import re, sys, zipfile
ORDER_AFTER = ("<w:spacing", "<w:ind", "<w:contextualSpacing", "<w:jc", "<w:rPr>", "</w:pPr>")
def add_stop(p, pos):
    tab = f'<w:tabs><w:tab w:val="right" w:pos="{pos}"/></w:tabs>'
    if "<w:tabs>" in p: return p
    if "<w:pPr>" not in p: return re.sub(r"(<w:p(?: [^>]*)?>)", r"\1<w:pPr>" + tab + "</w:pPr>", p, count=1)
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, flags=re.S).group(0); cut = min(ppr.index(k) for k in ORDER_AFTER if k in ppr)
    return p.replace(ppr, ppr[:cut] + tab + ppr[cut:], 1)
def rpr_of(run): m = re.search(r"<w:rPr>.*?</w:rPr>", run, flags=re.S); return m.group(0) if m else ""
def normalize(xml, textw):
    n = 0
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        runs = re.findall(r"<w:r[ >].*?</w:r>", p, flags=re.S)
        pad = next((i for i, r in enumerate(runs) if re.search(r"<w:t[^>]*> {5,}", r) or re.search(r" {5,}</w:t>", r)), None)
        if pad is None: continue
        head = p[:p.index(runs[0])]; tail = p[p.index(runs[-1]) + len(runs[-1]):]
        out = []; placed = False
        for i, r in enumerate(runs):
            r = r.replace("<w:tab/>", "")
            if i < pad: out.append(r); continue
            m = re.search(r"<w:t(?: xml:space=\"preserve\")?>([^<]*)</w:t>", r)
            if i == pad and m:
                before, after = re.split(r" {5,}", m.group(1), maxsplit=1) if re.search(r" {5,}", m.group(1)) else (m.group(1), "")
                rp = rpr_of(r); before, after = before.rstrip(), after.lstrip()
                if before: out.append(f"<w:r>{rp}<w:t xml:space=\"preserve\">{before}</w:t></w:r>")
                out.append(f"<w:r>{rp}<w:tab/></w:r>"); placed = True
                if after: out.append(f"<w:r>{rp}<w:t xml:space=\"preserve\">{after}</w:t></w:r>")
                continue
            if m and not m.group(1).strip(): continue  # whitespace-only run after the padding
            if m and not placed: out.append(f"<w:r>{rpr_of(r)}<w:tab/></w:r>"); placed = True
            out.append(r)
        ind = re.search(r'<w:ind [^>]*w:right="(\d+)"', p); right = int(ind.group(1)) if ind else 0
        q = add_stop(head + "".join(out) + tail, textw - right)
        xml = xml.replace(p, q, 1); n += 1
    return xml, n
if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    z = zipfile.ZipFile(src); x = z.read("word/document.xml").decode("utf8")
    pg = re.search(r'<w:pgSz w:w="(\d+)"', x); mar = re.search(r'<w:pgMar [^>]*w:right="(\d+)"[^>]*w:left="(\d+)"', x)
    textw = int(pg.group(1)) - int(mar.group(1)) - int(mar.group(2)) if pg and mar else 10800
    x, n = normalize(x, textw)
    zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
    for it in z.infolist(): zout.writestr(it, x.encode("utf8") if it.filename == "word/document.xml" else z.read(it.filename))
    zout.close(); print(f"normalized {n} lines; text width {textw} twips")
