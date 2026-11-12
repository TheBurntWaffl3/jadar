"""Incremental cache: list every run, fetch descriptions only for unknown postings, re-judge all, drop closed ones."""
import os, sys, json, unittest, tempfile, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scan

DESC = {"a": "Bachelor's degree in Aerospace Engineering. 0-2 years of experience. Application Deadline: Nov 30, 2026",
        "b": "Master's degree required. 5+ years of experience",
        "c": "BS in Mechanical Engineering. Requires an active Secret clearance"}
TITLE = {"a": "Thermal Engineer I", "b": "Structures Engineer", "c": "Propulsion Engineer", "d": "New Grad Test Engineer"}

class Board:
    """A fake adapter: `listed` is what the board lists; every description read is counted."""
    def __init__(self): self.listed = list(DESC); self.fetches = 0; self.fail = False
    def __call__(self, s):
        if self.fail: raise RuntimeError("HTTP Error 503")
        for k in self.listed:  # each org has its own host, as real boards do
            def desc(k=k):
                self.fetches += 1; return DESC[k]
            yield dict(title=TITLE[k], location="Hawthorne, CA", url=f"https://{s['org'].split()[0].lower()}.test/{k}",
                       date="2026-11-10", dateKind="posted", desc=desc)

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); d = self.tmp.name
        self.board = Board()
        self.saved = (scan.SRC, scan.ADAPT.get("fake"), scan.DATA_DIR, scan.CACHE_FILE, scan.TODAY)
        scan.SRC = [dict(org="Fake Co", sector="Space", type="fake"), dict(org="Other Co", sector="Space", type="fake")]
        scan.ADAPT["fake"] = self.board
        scan.DATA_DIR = d; scan.CACHE_FILE = os.path.join(d, "cache.json")
        scan.TODAY = dt.date(2026, 11, 12)  # a Thursday: no weekly full read
        os.environ.pop("FULL", None)

    def tearDown(self):
        scan.SRC, fake, scan.DATA_DIR, scan.CACHE_FILE, scan.TODAY = self.saved
        scan.ADAPT.pop("fake", None); self.tmp.cleanup()

    def out(self):
        with open(os.path.join(scan.DATA_DIR, "radar_out.json")) as f: return json.load(f)
    def cache(self):
        with open(scan.CACHE_FILE) as f: return json.load(f)

    def test_second_run_reuses_facts_and_keeps_first_seen(self):
        scan.main([])
        o1 = self.out(); c1 = self.cache()
        self.assertEqual(self.board.fetches, 6)  # 3 postings x 2 orgs, all unknown
        self.assertEqual({r["url"][-1]: r["fit"] for r in o1["roles"] if r["company"] == "Fake Co"}, {"a": "Yes", "b": "No", "c": "No"})
        self.assertEqual(c1["rulesVersion"], scan.RULES_VERSION)
        self.assertTrue(all("desc" not in e and "facts" in e for e in c1["postings"].values()), "cache holds facts, never descriptions")
        self.assertEqual(c1["postings"]["https://fake.test/a"]["facts"]["applyBy"], "2026-11-30")
        scan.TODAY = dt.date(2026, 11, 13)
        scan.main([])
        o2 = self.out()
        self.assertEqual(self.board.fetches, 6, "nothing new listed: no description fetched")
        self.assertEqual([s["cached"] for s in o2["status"]], [3, 3])
        a = next(r for r in o2["roles"] if r["url"].endswith("/a") and r["company"] == "Fake Co")
        self.assertEqual(a["firstSeen"], "2026-11-12")
        self.assertIn("apply by 2026-11-30", a["why"])

    def test_new_posting_fetched_closed_posting_dropped(self):
        scan.main([]); self.assertEqual(self.board.fetches, 6)
        DESC["d"] = "BS in Aerospace Engineering. New grad welcome."
        self.board.listed = ["a", "d"]  # b and c closed, d new
        try:
            scan.main([])
            self.assertEqual(self.board.fetches, 8, "only the new posting is read (once per org)")
            self.assertEqual(sorted(u[-1] for u in self.cache()["postings"]), ["a", "a", "d", "d"])
            self.assertEqual(sorted(r["url"][-1] for r in self.out()["roles"]), ["a", "a", "d", "d"])
        finally:
            DESC.pop("d")

    def test_failed_board_keeps_cache(self):
        scan.main([])
        self.board.fail = True
        scan.main([])
        o = self.out()
        self.assertFalse(any(s["ok"] for s in o["status"]))
        self.assertEqual(len(self.cache()["postings"]), 6, "a board that did not answer keeps its cached postings")
        self.assertEqual(o["roles"], [])

    def test_rules_change_and_full_flag_force_reread(self):
        scan.main([]); self.assertEqual(self.board.fetches, 6)
        c = self.cache(); c["rulesVersion"] = "old"
        with open(scan.CACHE_FILE, "w") as f: json.dump(c, f)
        scan.main([]); self.assertEqual(self.board.fetches, 12)
        self.assertTrue(self.out()["fullRead"].startswith("rules"))
        scan.main([]); self.assertEqual(self.board.fetches, 12, "back to incremental once the version matches")
        scan.main(["--full"]); self.assertEqual(self.board.fetches, 18)
        scan.TODAY = dt.date(2026, 11, 15)  # Sunday
        scan.main([]); self.assertEqual(self.board.fetches, 24)
        self.assertEqual(self.out()["fullRead"], "weekly (Sunday)")

    def test_new_detection_needs_prior_state(self):
        self.board.listed = ["a"]
        scan.main([])
        self.assertEqual([r["url"] for r in self.out()["new"]], [], "first ever run: 'posted' on 2026-11-10 is not today/yesterday")
        scan.TODAY = dt.date(2026, 11, 11)
        scan.main([])
        self.assertEqual(len(self.out()["new"]), 2, "posted yesterday counts as new for both orgs")

if __name__ == "__main__":
    unittest.main()
