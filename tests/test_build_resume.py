"""tools/build_resume.py: dump / plan apply / right-alignment rewrite on a hand-built docx (no LibreOffice needed)."""
import importlib.util, json, os, re, sys, tempfile, unittest, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
spec = importlib.util.spec_from_file_location("build_resume", os.path.join(ROOT, "tools", "build_resume.py")); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)

def para(text, bold=False, bullet=False, right=None, tabs=4, label=None):
    rp = "<w:rPr><w:b/></w:rPr>" if bold else "<w:rPr><w:sz w:val=\"21\"/></w:rPr>"
    ppr = "<w:pPr>" + ("<w:numPr><w:ilvl w:val=\"0\"/><w:numId w:val=\"1\"/></w:numPr>" if bullet else "") + "<w:spacing w:after=\"0\"/></w:pPr>"
    runs = ""
    if label: runs += f"<w:r><w:rPr><w:b/></w:rPr><w:t xml:space=\"preserve\">{label}</w:t></w:r><w:r>{rp}<w:t xml:space=\"preserve\">{text}</w:t></w:r>"
    else: runs += f"<w:r>{rp}<w:t>{text}</w:t></w:r>"
    if right: runs += "<w:r>" + "<w:tab/>" * tabs + "<w:t xml:space=\"preserve\">      </w:t></w:r>" + f"<w:r><w:rPr><w:i/></w:rPr><w:t>{right}</w:t></w:r>"
    return "<w:p>" + ppr + runs + "</w:p>"

def make_docx(path, paras):
    body = "".join(paras) + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="270" w:right="720" w:bottom="270" w:left="720" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
    doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + body + "</w:body></w:document>"
    z = zipfile.ZipFile(path, "w")
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr("word/document.xml", doc); z.close()

PARAS = [para("Kevin Kyle", bold=True), para("EDUCATION"), para("University of Maryland, College Park", bold=True, right="Expected May 2027"),
         para(" Computational Structural Mechanics, Aeroelasticity", label="Coursework:"), para("TECHNICAL EXPERIENCE"),
         para("Rocket Lab", bold=True, right="Silver Spring, MD"), para("R&amp;D Engineering Intern", right="Feb – May 2026", tabs=11),
         para("Built LabVIEW DAQ for preload tests", bullet=True), para("Authored preload test procedure and results report", bullet=True),
         para("Hypersonic Design Team", bold=True, right="College Park, MD"), para("Thermal Engineering Co-Lead", right="Jun 2025 – Present"),
         para("Automated CFD-to-FEA heat flux mapping", bullet=True), para("SKILLS"), para(" MATLAB, Python", label="Software:")]

class BuildResumeTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.master = os.path.join(self.d, "master.docx"); make_docx(self.master, PARAS)

    def test_dump(self):
        d = B.dump(self.master)
        self.assertEqual([x["kind"] for x in d[:3]], ["bold", "text", "bold"]); self.assertEqual(d[2]["text"], "University of Maryland, College Park ⟶ Expected May 2027")
        self.assertEqual(d[6]["text"], "R&D Engineering Intern ⟶ Feb – May 2026"); self.assertEqual(d[7]["kind"], "bullet"); self.assertEqual(d[3]["text"], "Coursework: Computational Structural Mechanics, Aeroelasticity")

    def test_apply(self):
        plan = {"set": {"10": "Thermal Engineering Lead ⟶ Jun 2025 – Present", "8": "Authored preload test procedure and post-test summaries", "3": "Coursework: Aeroelasticity, Heat & Mass Transfer"},
                "delete": [7], "insert_after": {"11": ["Built a 1-D MATLAB aerothermal solver"]}, "move": [{"range": [9, 11], "after": 4}]}
        out = os.path.join(self.d, "out.docx"); B.apply(self.master, plan, out)
        d = B.dump(out); texts = [x["text"] for x in d]
        self.assertEqual(texts[5], "Hypersonic Design Team ⟶ College Park, MD", "moved block right after TECHNICAL EXPERIENCE")
        self.assertEqual(texts[6], "Thermal Engineering Lead ⟶ Jun 2025 – Present"); self.assertEqual(texts[8], "Built a 1-D MATLAB aerothermal solver")
        self.assertNotIn("Built LabVIEW DAQ for preload tests", texts); self.assertIn("Authored preload test procedure and post-test summaries", texts)
        self.assertEqual(texts[3], "Coursework: Aeroelasticity, Heat & Mass Transfer")
        xml = zipfile.ZipFile(out).read("word/document.xml").decode()
        ps = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
        for p in ps:
            if B.parts(p)[1]: self.assertIn('<w:tab w:val="right" w:pos="10800"/>', p); self.assertEqual(p.count("<w:tab/>"), 1); self.assertNotIn("      ", p)
        cw = next(p for p in ps if "Coursework" in p); self.assertIn("<w:b/></w:rPr><w:t xml:space=\"preserve\">Coursework:</w:t>", cw, "bold label kept")
        self.assertIn("<w:numPr>", next(p for p in ps if "post-test summaries" in p), "bullet formatting kept")
        self.assertIn("&amp;", xml); self.assertIn("<w:sectPr>", xml)

    def test_move_after_itself_is_ignored(self):
        out = os.path.join(self.d, "out2.docx"); B.apply(self.master, {"move": [{"range": [9, 11], "after": 10}]}, out)
        self.assertEqual([x["text"] for x in B.dump(out)][:5], [x["text"] for x in B.dump(self.master)][:5])

if __name__ == "__main__":
    unittest.main()
