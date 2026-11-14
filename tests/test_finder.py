"""Terps finder: query building, result parsing, scheduling, and the private-repo write (all network stubbed)."""
import os, sys, json, base64, unittest, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import finder

ITEMS = [{"title": "Jane Doe - Propulsion Engineer - Anduril Industries | LinkedIn", "link": "https://www.linkedin.com/in/janedoe?trk=x",
          "snippet": "University of Maryland · Aerospace Engineering ... Anduril"},
         {"title": "John Roe – Technical Recruiter – Anduril | LinkedIn", "link": "https://www.linkedin.com/in/johnroe", "snippet": "Terp"},
         {"title": "Anduril Industries | LinkedIn", "link": "https://www.linkedin.com/company/anduril", "snippet": "company page, not a person"}]

class FinderTests(unittest.TestCase):
    def test_company_key_matches_page_rule(self):
        self.assertEqual(finder.company_key("L3Harris (incl. Aerojet Rocketdyne)"), "L3Harris")
        self.assertEqual(finder.company_key("RTX (Raytheon, Pratt & Whitney, Collins)"), "RTX")
        self.assertEqual(finder.company_key("Voyager / Astrobotic-adjacent"), "Voyager")
        self.assertEqual(finder.company_key("Rocket Lab"), "Rocket Lab")

    def test_query_and_parse(self):
        self.assertEqual(finder.query_for("RTX"), '"University of Maryland" "Raytheon"')
        self.assertEqual(finder.query_for("Anduril", site_in_query=True), 'site:linkedin.com/in "University of Maryland" "Anduril"')
        p = finder.parse_items(ITEMS)
        self.assertEqual([x["name"] for x in p], ["Jane Doe", "John Roe"])
        self.assertEqual(p[0]["headline"], "Propulsion Engineer · Anduril Industries")
        self.assertEqual(p[0]["url"], "https://www.linkedin.com/in/janedoe")

    def test_plan_prefers_companies_with_most_fits_and_skips_fresh(self):
        out = {"roles": [{"fit": "Yes", "company": "Anduril"}, {"fit": "Maybe", "company": "Anduril"}, {"fit": "Yes", "company": "Boeing"},
                         {"fit": "No", "company": "Moog"}, {"fit": "Yes", "company": "SpaceX"}]}
        people = {"companies": {"Boeing": {"searched": "2026-11-12", "people": [{"name": "A Terp"}]}, "SpaceX": {"searched": "2026-10-01", "people": []}}}
        due, total = finder.plan(out, people, dt.date(2026, 11, 13), days=7, max_q=60)
        self.assertEqual(total, 3); self.assertEqual(due, [("Anduril", []), ("SpaceX", [])])
        due, _ = finder.plan(out, people, dt.date(2026, 11, 13), days=7, max_q=1); self.assertEqual(due, [("Anduril", [])])
        due, _ = finder.plan(out, people, dt.date(2026, 11, 13)); self.assertEqual(due, [("Anduril", []), ("SpaceX", [])], "defaults: 14 days, 15 per run")
        # Boeing searched yesterday but found nobody: retried today, not in two weeks; searched today -> not retried yet
        people["companies"]["Boeing"]["people"] = []
        due, _ = finder.plan(out, people, dt.date(2026, 11, 13), days=14)
        self.assertEqual([k for k, _ in due], ["Anduril", "Boeing", "SpaceX"])
        people["companies"]["Boeing"]["searched"] = "2026-11-13"
        due, _ = finder.plan(out, people, dt.date(2026, 11, 13), days=14); self.assertEqual([k for k, _ in due], ["Anduril", "SpaceX"])

    def test_big_companies_get_field_narrowed_searches(self):
        roles = [{"fit": "Yes", "company": "SpaceX", "discipline": d} for d in ["Propulsion"] * 5 + ["Structures"] * 3 + ["Thermal"] * 2]
        due, _ = finder.plan({"roles": roles}, {"companies": {}}, dt.date(2026, 11, 13))
        self.assertEqual(due, [("SpaceX", ["Propulsion", "Structures"])])
        self.assertEqual(finder.query_for("SpaceX", finder.FIELD_WORD["Structures"]), '"University of Maryland" "SpaceX" structural')
        due, _ = finder.plan({"roles": roles}, {"companies": {}}, dt.date(2026, 11, 13), max_q=2)
        self.assertEqual(due, [("SpaceX", ["Propulsion"])], "budget of 2 queries: base + one field")

    def test_end_to_end_with_stubbed_network(self):
        os.environ.update(SERPAPI_KEY="k", STATE_REPO="o/r", STATE_TOKEN="t"); os.environ.pop("SERPER_KEY", None)
        calls = []
        def fake(url, token=None, method="GET", body=None, headers=None):
            calls.append((method, url.split("?")[0], body))
            if "api.github.com" in url and method == "GET":
                import urllib.error
                raise urllib.error.HTTPError(url, 404, "nf", {}, None)
            if "serpapi.com/search.json" in url: return {"organic_results": ITEMS}
            if "google.serper.dev" in url: return {"organic": ITEMS}
            return {}
        people, sha = finder.load_people(fake); self.assertEqual(people, {"v": 1, "companies": {}}); self.assertIsNone(sha)
        q, found, ok = finder.search("Anduril", fake); self.assertEqual(len(found), 2); self.assertTrue(ok)
        self.assertTrue(any("serpapi.com/search.json" in c[1] for c in calls))
        os.environ.pop("SERPAPI_KEY"); os.environ["SERPER_KEY"] = "s"
        q2, found2, ok2 = finder.search("Anduril", fake); self.assertEqual(len(found2), 2); self.assertEqual(finder.provider(), "serper")
        os.environ.pop("SERPER_KEY"); self.assertIsNone(finder.provider())
        people["companies"]["Anduril"] = dict(searched="2026-11-13", query=q, people=found)
        finder.save_people(people, None, fake)
        put = [c for c in calls if c[0] == "PUT"][0]
        self.assertTrue(put[1].endswith("/repos/o/r/contents/people.json"))
        doc = json.loads(base64.b64decode(put[2]["content"]))
        self.assertEqual(doc["companies"]["Anduril"]["people"][0]["name"], "Jane Doe"); self.assertNotIn("sha", put[2])

    def test_ignored_site_restriction_is_not_recorded(self):
        os.environ.update(SERPAPI_KEY="k"); os.environ.pop("SERPER_KEY", None)
        junk = [{"title": "USAspending.gov", "link": "https://www.google.com/goto?url=abc", "snippet": ""}] * 5
        n = {"calls": 0}
        def fake(url, token=None, method="GET", body=None, headers=None):
            n["calls"] += 1; return {"organic_results": junk}
        q, found, ok = finder.search("Boeing", fake)
        self.assertEqual(found, []); self.assertFalse(ok); self.assertEqual(n["calls"], 3, "google_light retry, then inurl: phrasing")
        self.assertIn("inurl:linkedin.com/in", q); self.assertIn("[light]", q)
        # the light parser returns real links on the second attempt
        m = {"calls": 0}
        def light(url, token=None, method="GET", body=None, headers=None):
            m["calls"] += 1
            return {"organic_results": ITEMS} if "engine=google_light" in url else {"organic_results": junk}
        q, found, ok = finder.search("Boeing", light); self.assertTrue(ok); self.assertEqual(len(found), 2); self.assertEqual(m["calls"], 2)
        def empty(url, token=None, method="GET", body=None, headers=None): return {"organic_results": []}
        q, found, ok = finder.search("Boeing", empty); self.assertTrue(ok, "a genuinely empty answer counts as searched")

if __name__ == "__main__":
    unittest.main()
