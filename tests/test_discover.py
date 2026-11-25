"""Board discovery: link parsing, known-board diffing, rotation, probing (network stubbed)."""
import os, sys, unittest, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discover

SOURCES = [{"id": "andurilindustries", "org": "Anduril", "type": "greenhouse"}, {"id": "shield", "org": "Shield AI", "type": "ashby"},
           {"tenant": "blueorigin", "wd": 5, "site": "BlueOrigin", "org": "Blue Origin", "type": "workday"}, {"id": "hermeus", "org": "Hermeus", "type": "lever"}]

def fake_fetch(url, method="GET", body=None, headers=None):
    if "serpapi.com" in url:
        return {"organic_results": [
            {"title": "Fluids Engineer Level 1 - Cowboy Space Corp.", "link": "https://jobs.ashbyhq.com/cowboyspace/aeba8bef-c701", "snippet": ""},
            {"title": "Propulsion Engineer | Shield AI", "link": "https://jobs.ashbyhq.com/shield/123", "snippet": ""},  # known
            {"title": "Thermal Engineer - Blue Origin", "link": "https://blueorigin.wd5.myworkdayjobs.com/en-US/BlueOrigin/job/x", "snippet": ""},  # known
            {"title": "Structures Engineer - Acme Rockets", "link": "https://acmerockets.wd1.myworkdayjobs.com/en-US/External/job/y", "snippet": ""},
            {"title": "Jobs", "link": "https://jobs.lever.co/ignoredco/abc", "snippet": ""},
            {"title": "Embedded Software - Boring Co", "link": "https://boards.greenhouse.io/embed/job_app?for=boringco", "snippet": ""}]}
    if "api.ashbyhq.com/posting-api/job-board/cowboyspace" in url:
        return {"jobs": [{"title": "Fluids Engineer Level 1"}, {"title": "Senior Accounts Payable Specialist"}, {"title": "TCA Mechanical Design Engineer Level 1"}]}
    raise AssertionError("unexpected fetch " + url)

class DiscoverTests(unittest.TestCase):
    def test_parse_link(self):
        self.assertEqual(discover.parse_link("https://jobs.ashbyhq.com/cowboyspace/aeba8bef"), ("ashby", "cowboyspace"))
        self.assertEqual(discover.parse_link("https://job-boards.greenhouse.io/freeformfuturecorp/jobs/4001"), ("greenhouse", "freeformfuturecorp"))
        self.assertEqual(discover.parse_link("https://jobs.lever.co/velo3d/1234"), ("lever", "velo3d"))
        self.assertEqual(discover.parse_link("https://rand.wd5.myworkdayjobs.com/en-US/External_Career_Site/job/x"), ("workday", "rand"))
        self.assertEqual(discover.parse_link("https://jobs.smartrecruiters.com/LLNL/7440"), ("smartrecruiters", "LLNL"))
        self.assertIsNone(discover.parse_link("https://boards.greenhouse.io/embed/job_app?for=x"))  # embed is not a board id
        self.assertIsNone(discover.parse_link("https://www.linkedin.com/jobs/view/1"))

    def test_run_diffs_probes_and_rotates(self):
        os.environ["SERPAPI_KEY"] = "test"
        try:
            state, new = discover.run(SOURCES, {}, fake_fetch, dt.date(2026, 11, 25), max_q=2, ignore={"lever:ignoredco"})
        finally:
            del os.environ["SERPAPI_KEY"]
        self.assertEqual(sorted(new), ["ashby:cowboyspace", "workday:acmerockets"])  # known boards and the ignored one are skipped
        cb = state["boards"]["ashby:cowboyspace"]
        self.assertEqual(cb["jobs"], 3); self.assertEqual(cb["inField"], ["Fluids Engineer Level 1", "TCA Mechanical Design Engineer Level 1"])
        self.assertEqual(cb["company"], "Cowboy Space Corp."); self.assertEqual(cb["status"], "new")
        self.assertIsNone(state["boards"]["workday:acmerockets"].get("jobs"))  # Workday is never probed from here
        self.assertEqual(state["cursor"], 2)
        # a second run after the board was added to sources.json marks it added and does not re-list it
        os.environ["SERPAPI_KEY"] = "test"
        try:
            state, new = discover.run(SOURCES + [{"id": "cowboyspace", "org": "Cowboy Space", "type": "ashby"}], state, fake_fetch, dt.date(2026, 11, 26), max_q=1, ignore={"lever:ignoredco"})
        finally:
            del os.environ["SERPAPI_KEY"]
        self.assertEqual(new, []); self.assertEqual(state["boards"]["ashby:cowboyspace"]["status"], "added"); self.assertEqual(state["cursor"], 3)

    def test_due_once_a_day_on_wed_and_sun(self):
        wed, thu, sun = dt.date(2026, 11, 25), dt.date(2026, 11, 26), dt.date(2026, 11, 29)
        self.assertTrue(discover.due({}, wed)); self.assertFalse(discover.due({"updated": "2026-11-25"}, wed))  # second run the same day
        self.assertFalse(discover.due({}, thu)); self.assertTrue(discover.due({}, thu, force=True)); self.assertTrue(discover.due({"updated": "2026-11-25"}, sun))

    def test_company_from_title(self):
        self.assertEqual(discover.company_from("Fluids Engineer Level 1 - Cowboy Space Corp."), "Cowboy Space Corp.")
        self.assertEqual(discover.company_from("Freeform | Additive Engineer (New Grad Summer 2027)"), "Freeform")
        self.assertIsNone(discover.company_from("Jobs"))

if __name__ == "__main__":
    unittest.main()
