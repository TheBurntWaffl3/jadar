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

class UrlSeniorTests(unittest.TestCase):
    def test_url_slug_says_senior(self):
        s = dict(org="X-energy", sector="Nuclear & fusion", type="workday")
        base = dict(title="Mechanical Design Engineer", location="Houston, TX", date="2026-11-16", dateKind="posted", desc_ok=True, fieldInDesc=True,
                    facts=scan.requirements("Bachelor's degree in mechanical engineering required. 1+ years of experience."), firstSeen="2026-11-16")
        r = scan.judge_entry(s, dict(base, url="https://xenergy.wd5.myworkdayjobs.com/en-US/X-energyUS/job/Houston-TX/Senior-Piping-and-Valve-Design-Engineer_R100796-1"))
        self.assertEqual((r["fit"], r["why"]), ("No", "senior per posting URL"))
        r = scan.judge_entry(s, dict(base, url="https://xenergy.wd5.myworkdayjobs.com/en-US/X-energyUS/job/Houston-TX/Mechanical-Design-Engineer_R101443"))
        self.assertEqual(r["fit"], "Maybe")
        r = scan.judge_entry(s, dict(base, title="2027 Early Career Mechanical Engineer", url="https://x.test/job/Senior-Program-2027-Early-Career-Mechanical-Engineer_R1"))
        self.assertNotEqual(r["fit"], "No", "an entry-level title wins over a slug word")
        # live run 2026-11-16: "staff"/"lead" in a slug are not seniority (MIT LL "Assistant Staff" is the entry level,
        # Curtiss-Wright "Manufacturing-Engineer-Staff" asked 0 years)
        for url in ("https://careers.ll.mit.edu/job/Lexington-Thermal-Engineer-Assistant-Staff-MA-02420/1432105100/",
                    "https://curtisswright.wd1.myworkdayjobs.com/en-US/CW_External_Career_Site/job/US-NY-Farmingdale-Sensors/Manufacturing-Engineer-Staff_JR13308-1"):
            r = scan.judge_entry(s, dict(base, title="Thermal Engineer - Assistant Staff", url=url))
            self.assertNotEqual(r["why"], "senior per posting URL", url)

class WeirdTitleTests(unittest.TestCase):
    """Kevin 2026-11-25: "if the title is weird but we match its requirements then it should still be listed". The title
    only needs a role word (and no out-of-field / management word); the description decides the field, on every board."""
    def test_title_without_field_word_is_judged_by_its_description(self):
        s = dict(org="Lockheed Martin", sector="Primes", type="eightfold")
        base = dict(title="Engineer Asc - Early Career", location="Orlando, FL", date="2026-11-16", dateKind="posted", desc_ok=True, firstSeen="2026-11-25",
                    url="https://lockheedmartin.eightfold.ai/careers/job/1", facts=scan.requirements("Basic Qualifications: Bachelors degree in a related discipline. 0-5 years of relevant experience."))
        r = scan.judge_entry(s, dict(base, fieldInDesc=True)); self.assertEqual(r["fit"], "Yes")
        self.assertIsNone(scan.judge_entry(s, dict(base, fieldInDesc=False)), "no field anywhere -> not listed")
        self.assertTrue(scan.in_scope("Engineer Asc - Early Career", True)); self.assertFalse(scan.in_scope("Software Engineer Asc", True))
        # 2026-11-25 coverage sweep false positives: AEVEX "Identity Intelligence Analyst Jr.", AST SpaceMobile "EDP - Industrial Engineering"
        self.assertFalse(scan.in_scope("Identity Intelligence Analyst Jr.", True)); self.assertFalse(scan.in_scope("Engineering Development Program (EDP) – Industrial Engineering – Micron Operations", True))
        self.assertTrue(scan.in_scope("Engineering Development Program (EDP) – Major Assembly- Integration- CSAT Structures", True))

    def test_run_source_records_dropped_titles(self):
        import contextlib, io
        s = dict(org="Fake Co", sector="Space", type="greenhouse", id="fake")
        rows = [dict(title="Software Engineer", url="https://x/sw", location="Austin, TX", date="2026-11-20", dateKind="posted", desc="Python"),
                dict(title="Director of Engineering", url="https://x/dir", location="Austin, TX", date="2026-11-20", dateKind="posted", desc="lead"),
                dict(title="Engineer I", url="https://x/eng", location="Austin, TX", date="2026-11-20", dateKind="posted", desc="We make sandwiches. Bachelor's degree. 0 years."),
                dict(title="Thermal Engineer I", url="https://x/th", location="Austin, TX", date="2026-11-20", dateKind="posted", desc="Thermal analysis. Bachelor's degree. 0 years.")]
        old = scan.ADAPT["greenhouse"]; scan.ADAPT["greenhouse"] = lambda src: iter(rows)
        try:
            with contextlib.redirect_stdout(io.StringIO()): _, out_rows, st, entries = scan.run_source(s, {}, True)
        finally: scan.ADAPT["greenhouse"] = old
        self.assertEqual([r["title"] for r in out_rows], ["Thermal Engineer I"])
        self.assertEqual({d["title"]: d["reason"] for d in st["dropped"]}, {"Software Engineer": "out-of-field word in title", "Director of Engineering": "management title", "Engineer I": "no field word in title or description"})

class RepostTests(unittest.TestCase):
    """Kevin 2026-11-26: a role that closed and came back (new URL, same company + title) or whose date jumped gets a Reposted tag."""
    def test_closed_then_back_under_new_url(self):
        cache = {"postings": {"https://x/old": {"company": "SpaceX", "title": "Thermal Engineer", "firstSeen": "2026-10-01", "lastSeen": "2026-11-10"}}}
        scan.record_closed(cache, "SpaceX", {}, "2026-11-11")  # the board no longer lists it
        self.assertNotIn("https://x/old", cache["postings"]); self.assertEqual(cache["closed"]["SpaceX|thermal engineer"]["closedOn"], "2026-11-11")
        entries = {"https://x/new": {"company": "SpaceX", "title": "Thermal Engineer", "date": "2026-11-25", "dateKind": "posted"}}
        rows = [{"url": "https://x/new"}]
        scan.mark_reposts(cache, "SpaceX", entries, rows, "2026-11-25")
        self.assertEqual(rows[0]["repost"], {"url": "https://x/old", "firstSeen": "2026-10-01", "closedOn": "2026-11-11"})
        self.assertEqual(entries["https://x/new"]["repost"]["closedOn"], "2026-11-11")

    def test_same_day_churn_and_other_companies_do_not_count(self):
        cache = {"postings": {}, "closed": {"SpaceX|thermal engineer": {"url": "https://x/old", "firstSeen": "2026-10-01", "closedOn": "2026-11-25"}}}
        entries = {"https://x/new": {"company": "SpaceX", "title": "Thermal Engineer", "date": "2026-11-25", "dateKind": "posted"},
                   "https://y/1": {"company": "Blue Origin", "title": "Thermal Engineer", "date": "2026-11-25", "dateKind": "posted"}}
        rows = [{"url": "https://x/new"}, {"url": "https://y/1"}]
        scan.mark_reposts(cache, "SpaceX", entries, rows, "2026-11-25")
        self.assertTrue(all("repost" not in r for r in rows), "closed and re-listed the same day is a glitch, not a re-post")

    def test_known_url_whose_date_jumps(self):
        cache = {"postings": {"https://x/1": {"company": "Rocket Lab", "title": "GNC Engineer I", "firstSeen": "2026-09-01", "date": "2026-09-01"}}}
        entries = {"https://x/1": {"company": "Rocket Lab", "title": "GNC Engineer I", "date": "2026-11-20", "dateKind": "posted"}}
        rows = [{"url": "https://x/1"}]
        scan.mark_reposts(cache, "Rocket Lab", entries, rows, "2026-11-25")
        self.assertEqual(rows[0]["repost"], {"url": "https://x/1", "firstSeen": "2026-09-01", "redated": "2026-09-01"})
        entries = {"https://x/1": {"company": "Rocket Lab", "title": "GNC Engineer I", "date": "2026-09-05", "dateKind": "posted"}}; rows = [{"url": "https://x/1"}]
        scan.mark_reposts(cache, "Rocket Lab", entries, rows, "2026-11-25"); self.assertNotIn("repost", rows[0], "a 4-day wobble is not a re-post")

    def test_judge_entry_carries_the_mark(self):
        s = dict(org="SpaceX", sector="Space", type="greenhouse")
        e = dict(title="Thermal Engineer", location="Hawthorne, CA", date="2026-11-25", dateKind="posted", desc_ok=True, fieldInDesc=True, firstSeen="2026-11-25",
                 url="https://x/new", facts=scan.requirements("Bachelor's degree. 0 years."), repost={"url": "https://x/old", "firstSeen": "2026-10-01", "closedOn": "2026-11-11"})
        self.assertEqual(scan.judge_entry(s, e)["repost"]["url"], "https://x/old")

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

    def test_failed_board_keeps_cache_and_shows_last_read(self):
        scan.main([])
        self.board.fail = True
        scan.TODAY = dt.date(2026, 11, 13)
        scan.main([])
        o = self.out()
        self.assertFalse(any(s["ok"] for s in o["status"]))
        self.assertEqual(len(self.cache()["postings"]), 6, "a board that did not answer keeps its cached postings")
        self.assertEqual(len(o["roles"]), 6, "its roles from the last read within 3 days are still shown")
        self.assertEqual([s["stale"] for s in o["status"]], [3, 3])
        scan.TODAY = dt.date(2026, 11, 20)  # last read is now older than STALE_DAYS
        scan.main([])
        self.assertEqual(self.out()["roles"], [])

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
