import json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build_dash, build_page

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "radar_out.sample.json")

def embedded(html):
    return json.loads(html.split('<script id="data" type="application/json">')[1].split("</script>")[0].replace("<\\/", "</"))

class PageTests(unittest.TestCase):
    def test_terps_found_block(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle")
        self.assertIn("people.json", html)
        self.assertIn("Terps found here", html)
        self.assertIn("Connect sync in Data to see Terps found at this company.", html)
        self.assertIn("linkedin\\.com", html)           # host check on every profile link
        self.assertIn("Not searched yet (next weekly run).", html)
        for leak in ("Jane Doe", '"companies"', "janedoe"):  # people data is fetched at runtime, never embedded
            self.assertNotIn(leak, html)

    def test_terps_links(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle")
        self.assertIn("linkedin.com/school/university-of-maryland/people/?keywords=", html)
        self.assertIn("terrapinsconnect.umd.edu", html)
        self.assertIn("function division(", html)

    def setUp(self):
        with open(FIXTURE) as f: self.out = json.load(f)
        with open(os.path.join(ROOT, "sources.json")) as f: self.src = json.load(f)

    def test_datasets(self):
        roles, orgs = build_dash.datasets(self.out, self.src)
        self.assertEqual(len(roles), len(self.out["roles"]))
        self.assertTrue(set(build_dash.KEEP) <= set(roles[0]))
        by = {o["org"]: o for o in orgs}
        self.assertEqual(by["Joby"]["status"], "Failing"); self.assertIn("503", by["Joby"]["note"])
        self.assertEqual(by["Boeing"]["roles"], 2); self.assertEqual(by["Boeing"]["fits"], 0)
        self.assertEqual(by["Kratos"]["status"], "Not covered yet")

    def test_build_page_writes_html(self):
        with tempfile.TemporaryDirectory() as d:
            data, site = os.path.join(d, "data"), os.path.join(d, "site")
            os.makedirs(data)
            with open(os.path.join(data, "radar_out.json"), "w") as f: json.dump(self.out, f)
            os.environ["RADAR_DATA"], os.environ["SITE_DIR"] = data, site
            try: build_page.main()
            finally: os.environ.pop("RADAR_DATA"); os.environ.pop("SITE_DIR")
            with open(os.path.join(site, "index.html")) as f: html = f.read()
        self.assertIn("Thermal Engineer, New Grad (Starship)", html)
        self.assertIn("Kratos", html)
        self.assertIn("Kevin Kyle", html)
        self.assertIn('id="sort"', html); self.assertIn("Apply-by soonest", html); self.assertIn('data-sort="salary"', html)
        self.assertIn('id="boards-toggle"', html); self.assertIn("Show boards", html)
        blob = embedded(html)
        self.assertEqual(sum(r["fit"] == "Yes" for r in blob["roles"]), 5)
        self.assertEqual(sum(r["fit"] == "Maybe" for r in blob["roles"]), 4)
        self.assertEqual(blob["today"], "2026-11-12")
        self.assertIn("https://boards.greenhouse.io/spacex/jobs/1001", blob["new"])
        r1 = next(r for r in blob["roles"] if r["id"] == "r0001")
        self.assertEqual(r1["salary"], "$95,000–$130,000/yr"); self.assertEqual(r1["salaryMax"], 130000); self.assertIn("Thermal Desktop", r1["reqSnippet"])
        self.assertNotIn("gpaReq", r1, "null fields are left out of the embedded data")
        self.assertTrue(all(r.get("reqSnippet") is None for r in blob["roles"] if r["fit"] == "No"), "No rows carry no requirements excerpt")
        self.assertTrue(all(r["reqSnippet"] for r in blob["roles"] if r["id"] in ("r0001", "r0002")))
        self.assertNotIn("<script src", html); self.assertNotIn("https://cdn", html)

    def test_per_role_state_ui(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle")
        for tab in ("Inbox", "Saved", "Applied", "Disliked", "All"): self.assertIn(f'>{tab}<span class="badge mono"', html)
        self.assertIn("jadar.state.v1", html); self.assertIn("jadar.sync.v1", html)
        self.assertIn("https://api.github.com/repos/", html); self.assertIn("jadar-state.json", html)
        for act in ("save", "applied", "hide"): self.assertIn(f'data-act="{act}"', html)
        self.assertIn('data-note="1"', html); self.assertIn('id="export-btn"', html); self.assertIn('id="import-file"', html); self.assertIn('id="clear-hidden"', html)
        # nothing secret is baked into the page: no token-like strings, and the sync settings are only ever a storage key name
        self.assertNotIn("github_pat_", html); self.assertNotIn("ghp_", html)
        self.assertEqual(html.count("jadar.sync.v1"), 1)
        self.assertNotIn("api.github.com/repos/TheBurntWaffl3/jadar-state", html, "the sync URL is built at runtime from the browser's own settings")

    def test_page_tolerates_old_data_without_extras(self):
        out = json.loads(json.dumps(self.out))
        for r in out["roles"]:
            for k in build_page.EXTRA: r.pop(k, None)
        html = build_page.build(out, self.src, "Kevin Kyle")
        blob = embedded(html)
        self.assertTrue(all(r.get("salary") is None and r.get("reqSnippet") is None for r in blob["roles"]))

if __name__ == "__main__":
    unittest.main()
