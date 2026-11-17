"""Hiring calendar page: entry-level filter, cycle bucketing, history merge, and the rendered page."""
import json, os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build_calendar

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "radar_out.sample.json")

def embedded(html):
    return json.loads(html.split('<script id="data" type="application/json">')[1].split("</script>")[0].replace("<\\/", "</"))

class CalendarTests(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE) as f: self.out = json.load(f)
        with open(os.path.join(ROOT, "calendar.json")) as f: self.cal = json.load(f)
        self.history = {"postings": {
            "https://boards.greenhouse.io/spacex/jobs/900": dict(company="SpaceX", title="New Graduate Engineer, Mechanical (Starship)", location="Starbase, TX", fit="Yes",
                                                              date="2025-08-19", dateKind="posted", firstSeen="2025-08-19", lastSeen="2026-01-15"),
            "https://example.test/maybe-senior": dict(company="Boeing", title="Structural Analysis Engineer", location="Everett, WA", fit="Maybe",
                                                      date="2026-07-01", dateKind="posted", firstSeen="2026-07-01", lastSeen="2026-09-01"),
            "https://example.test/aero": dict(company="Aerospace Corp", title="2027 Thermal Analyst", location="El Segundo, CA", fit="Yes",
                                              date="2026-11-11", dateKind="refreshed", firstSeen="2026-10-02", lastSeen="2026-11-12"),
        }}

    def test_is_entry(self):
        self.assertTrue(build_calendar.is_entry(dict(fit="Yes", title="Structural Analysis Engineer")))
        self.assertTrue(build_calendar.is_entry(dict(fit="Maybe", title="2026 New Grad Mechanical Engineer")))
        self.assertTrue(build_calendar.is_entry(dict(fit="Maybe", title="Mechanical Engineer I")))
        self.assertTrue(build_calendar.is_entry(dict(fit="Maybe", title="New Graduate Engineer, Mechanical - '26/'27 (Starlink)")))
        self.assertFalse(build_calendar.is_entry(dict(fit="Maybe", title="Structural Analysis Engineer")))
        self.assertFalse(build_calendar.is_entry(dict(fit="No", title="Entry Level Engineer")))

    def test_cycle_of(self):
        self.assertEqual(build_calendar.cycle_of("2026-06-01"), 2027)
        self.assertEqual(build_calendar.cycle_of("2026-05-31"), 2026)
        self.assertEqual(build_calendar.cycle_of("2027-05-24"), 2027)

    def test_postings_merge_and_buckets(self):
        rows = build_calendar.postings(self.out, self.history)
        by = {r["url"]: r for r in rows}
        self.assertIn("https://boards.greenhouse.io/spacex/jobs/900", by, "closed postings from history stay")
        self.assertEqual(by["https://boards.greenhouse.io/spacex/jobs/900"]["cycle"], 2026)
        self.assertEqual(by["https://boards.greenhouse.io/spacex/jobs/900"]["month"], "2025-08")
        self.assertNotIn("https://example.test/maybe-senior", by, "a Maybe without an entry title is not an entry posting")
        aero = by["https://example.test/aero"]
        self.assertIsNone(aero.get("month"), "refreshed dates do not go on the grid")
        self.assertEqual(aero["cycle"], 2027, "undated postings fall into the cycle of their first-seen date")
        cur = by["https://boards.greenhouse.io/spacex/jobs/1001"]
        self.assertEqual((cur["month"], cur["cycle"], cur["fit"]), ("2026-11", 2027, "Yes"))
        self.assertTrue(all(r["fit"] in ("Yes", "Maybe") for r in rows))
        self.assertTrue(all("firstSeen" in r or "date" in r for r in rows))

    def test_build_writes_page(self):
        with tempfile.TemporaryDirectory() as d:
            data, site = os.path.join(d, "data"), os.path.join(d, "site")
            os.makedirs(data)
            with open(os.path.join(data, "radar_out.json"), "w") as f: json.dump(self.out, f)
            with open(os.path.join(data, "history.json"), "w") as f: json.dump(self.history, f)
            os.environ["RADAR_DATA"], os.environ["SITE_DIR"] = data, site
            try: build_calendar.main()
            finally: os.environ.pop("RADAR_DATA"); os.environ.pop("SITE_DIR")
            with open(os.path.join(site, "calendar.html")) as f: html = f.read()
        self.assertIn("When entry-level roles open", html)
        self.assertIn("Class-year pool", html); self.assertIn("Hire-now Level 1", html)
        self.assertIn('href="index.html"', html)
        self.assertNotIn("<script src", html); self.assertNotIn("https://cdn", html)
        blob = embedded(html)
        self.assertEqual(blob["classYear"], 2027); self.assertEqual(blob["today"], "2026-11-12")
        self.assertEqual(blob["historySince"], "2025-08-19")
        orgs = {o["org"] for o in blob["orgs"]}
        self.assertIn("Boeing", orgs); self.assertIn("SpaceX", orgs)
        ex = next(o for o in blob["orgs"] if o["org"] == "Boeing")["examples"]
        self.assertTrue(any(e.get("posted") == "2026-02-27" for e in ex))
        self.assertTrue(all(e.get("source", "").startswith("http") for o in blob["orgs"] for e in o["examples"]), "every curated example cites its page")

    def test_main_without_history_file(self):
        with tempfile.TemporaryDirectory() as d:
            data, site = os.path.join(d, "data"), os.path.join(d, "site")
            os.makedirs(data)
            with open(os.path.join(data, "radar_out.json"), "w") as f: json.dump(self.out, f)
            os.environ["RADAR_DATA"], os.environ["SITE_DIR"] = data, site
            try: build_calendar.main()
            finally: os.environ.pop("RADAR_DATA"); os.environ.pop("SITE_DIR")
            self.assertTrue(os.path.exists(os.path.join(site, "calendar.html")))

    def test_curated_orgs_exist_in_sources(self):
        with open(os.path.join(ROOT, "sources.json")) as f: names = {s["org"] for s in json.load(f)}
        for o in self.cal["orgs"]: self.assertIn(o["org"], names, f"calendar.json org {o['org']!r} must match sources.json")
        ids = {p["id"] for p in self.cal["patterns"]}
        for o in self.cal["orgs"]: self.assertIn(o["pattern"], ids)

if __name__ == "__main__":
    unittest.main()
