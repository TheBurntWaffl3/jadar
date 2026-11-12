import json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build_dash, build_page

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "radar_out.sample.json")

class PageTests(unittest.TestCase):
    def setUp(self):
        self.out = json.load(open(FIXTURE)); self.src = json.load(open(os.path.join(ROOT, "sources.json")))

    def test_datasets(self):
        roles, orgs = build_dash.datasets(self.out, self.src)
        self.assertEqual(len(roles), len(self.out["roles"]))
        self.assertEqual(set(roles[0]), set(build_dash.KEEP))
        by = {o["org"]: o for o in orgs}
        self.assertEqual(by["Joby"]["status"], "Failing"); self.assertIn("503", by["Joby"]["note"])
        self.assertEqual(by["Boeing"]["roles"], 2); self.assertEqual(by["Boeing"]["fits"], 0)
        self.assertEqual(by["Kratos"]["status"], "Not covered yet")

    def test_build_page_writes_html(self):
        with tempfile.TemporaryDirectory() as d:
            data, site = os.path.join(d, "data"), os.path.join(d, "site")
            os.makedirs(data); json.dump(self.out, open(os.path.join(data, "radar_out.json"), "w"))
            os.environ["RADAR_DATA"], os.environ["SITE_DIR"] = data, site
            try: build_page.main()
            finally: os.environ.pop("RADAR_DATA"); os.environ.pop("SITE_DIR")
            html = open(os.path.join(site, "index.html")).read()
        self.assertIn("Thermal Engineer, New Grad (Starship)", html)
        self.assertIn("Kratos", html)
        self.assertIn("Kevin Kyle", html)
        blob = json.loads(html.split('<script id="data" type="application/json">')[1].split("</script>")[0].replace("<\\/", "</"))
        self.assertEqual(sum(r["fit"] == "Yes" for r in blob["roles"]), 5)
        self.assertEqual(sum(r["fit"] == "Maybe" for r in blob["roles"]), 4)
        self.assertEqual(blob["today"], "2026-11-12")
        self.assertIn("https://boards.greenhouse.io/spacex/jobs/1001", blob["new"])
        self.assertNotIn("<script src", html); self.assertNotIn("https://cdn", html)

if __name__ == "__main__":
    unittest.main()
