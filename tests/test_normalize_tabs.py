"""tools/normalize_tabs.py: Word-only right alignment (default-stop tabs + space runs) -> one right tab stop per line."""
import importlib.util, os, re, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("normalize_tabs", os.path.join(ROOT, "tools", "normalize_tabs.py")); N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)

P1 = ('<w:p><w:pPr><w:spacing w:after="0"/><w:rPr><w:i/></w:rPr></w:pPr><w:r><w:rPr><w:sz w:val="21"/></w:rPr><w:t>B.S., Aerospace Engineering</w:t></w:r>'
      '<w:r><w:tab/><w:tab/><w:tab/></w:r><w:r><w:rPr><w:i/></w:rPr><w:t xml:space="preserve">                      Cumulative GPA:  3.88</w:t></w:r></w:p>')
P2 = ('<w:p><w:pPr><w:widowControl w:val="0"/><w:spacing w:before="40"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>Rocket Lab</w:t></w:r><w:r><w:rPr><w:sz w:val="22"/></w:rPr><w:tab/></w:r>'
      '<w:r><w:tab/><w:tab/><w:t xml:space="preserve">               </w:t></w:r><w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t>Silver Spring, MD</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r></w:p>')
P3 = '<w:p><w:pPr><w:ind w:right="90"/></w:pPr><w:r><w:t>Coursework: nothing to align here</w:t></w:r></w:p>'

class NormalizeTests(unittest.TestCase):
    def test_lines(self):
        xml, n = N.normalize("<w:body>" + P1 + P2 + P3 + "</w:body>", 10800)
        self.assertEqual(n, 2)
        ps = re.findall(r"<w:p>.*?</w:p>", xml)
        for p in ps[:2]:
            self.assertEqual(p.count("<w:tab/>"), 1, p); self.assertNotIn("     ", p); self.assertIn('<w:tab w:val="right" w:pos="10800"/>', p)
            self.assertLess(p.index("<w:tabs>"), p.index("<w:spacing"))  # OOXML order inside pPr
        self.assertIn("<w:t>B.S., Aerospace Engineering</w:t>", ps[0]); self.assertIn('<w:t xml:space="preserve">Cumulative GPA:  3.88</w:t>', ps[0])
        self.assertIn("<w:t>Rocket Lab</w:t>", ps[1]); self.assertIn("<w:t>Silver Spring, MD</w:t>", ps[1])
        self.assertTrue(ps[1].index("<w:tab/>") < ps[1].index("Silver Spring"))
        self.assertEqual(ps[2], P3, "untouched")

    def test_right_indent_moves_the_stop(self):
        xml, n = N.normalize(P1.replace('<w:spacing w:after="0"/>', '<w:ind w:right="90"/><w:spacing w:after="0"/>'), 10800)
        self.assertIn('w:pos="10710"', xml); self.assertLess(xml.index("<w:tabs>"), xml.index("<w:ind"))

if __name__ == "__main__":
    unittest.main()
