"""tailor_queue.py: the tailoring queue written for the resume session on Kevin's PC."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tailor_queue as Q

ROLES = [
    {"url": "https://x/a", "company": "Lockheed Martin", "title": "Systems Engineer Asc - Early Career", "fit": "Yes", "timing": "unstated", "date": "2026-11-16", "why": "new-grad / entry title", "location": "Orlando, FL", "reqSnippet": "0-5 years", "applyBy": "2026-12-05", "salary": "$80,000/yr"},
    {"url": "https://x/b", "company": "Anduril", "title": "2027 New Grad GNC Engineer", "fit": "Yes", "timing": "2027", "date": "2026-11-20", "why": "2027 grads named", "location": "Costa Mesa, CA"},
    {"url": "https://x/c", "company": "Blue Origin", "title": "Test Engineer", "fit": "Maybe", "timing": "unstated", "date": "2026-11-10", "why": "yrs not stated", "location": "Kent, WA"},
    {"url": "https://x/d", "company": "ULA", "title": "Loads Engineer", "fit": "Maybe", "timing": "unstated", "date": "2026-11-24", "why": "yrs not stated"},
    {"url": "https://x/e", "company": "Varda", "title": "Mechanical Engineer", "fit": "Yes", "timing": "2027", "date": "2026-11-24", "why": ""},
    {"url": "https://x/f", "company": "Vast", "title": "Structures Engineer", "fit": "Yes", "timing": "2027", "date": "2026-11-24", "why": ""},
    {"url": "https://x/g", "company": "Stoke", "title": "Propulsion Engineer", "fit": "Yes", "timing": "unstated", "date": "2026-11-01", "why": ""},
]

class QueueTests(unittest.TestCase):
    def test_slug_matches_the_page(self):
        self.assertEqual(Q.slug("Lockheed Martin", "Systems Engineer Asc - Early Career"), "lockheed-martin-systems-engineer-asc-early-career")
        self.assertEqual(Q.slug("L3Harris (incl. Aerojet Rocketdyne)", "Engineer I/II"), "l3harris-engineer-i-ii")

    def test_order_and_skips(self):
        import datetime as dt
        state = {"https://x/c": "saved", "https://x/e": "applied", "_doc": {"tailor": {"https://x/f": {"status": "skip"}}}}
        today = dt.date(2026, 11, 26)
        rows = Q.build_queue({"roles": ROLES}, state, files=["stoke-propulsion-engineer.pdf", "old.pdf"], today=today)
        self.assertEqual([r["url"] for r in rows], ["https://x/c", "https://x/b", "https://x/a"])  # saved, then 2027, then newest; d is Maybe unsaved, e applied, f skipped, g has a PDF
        self.assertEqual(len(Q.build_queue({"roles": ROLES}, state, [], max_n=2, today=today)), 2)
        # a role first seen within 3 days outranks older 2027 roles (the build wakes for new batches)
        roles = [dict(ROLES[0], firstSeen="2026-11-25"), dict(ROLES[1], firstSeen="2026-11-10")]
        rows = Q.build_queue({"roles": roles}, {}, [], today=today)
        self.assertEqual([r["url"] for r in rows], ["https://x/a", "https://x/b"]); self.assertTrue(rows[0]["fresh"]); self.assertFalse(rows[1]["fresh"])

    def test_brief(self):
        rows = Q.build_queue({"roles": ROLES[:1]}, {}, [])
        b = rows[0]["brief"]
        for needle in ("Read-only", "Company: Lockheed Martin", "Link: https://x/a", "Apply by: December 5, 2026", "Pay listed: $80,000/yr", "0-5 years",
                       "resumes/lockheed-martin-systems-engineer-asc-early-career.pdf", "never invent"):
            self.assertIn(needle, b, needle)

    def test_not_configured(self):
        for k in ("STATE_REPO", "STATE_TOKEN"): os.environ.pop(k, None)
        Q.main()  # prints and returns

if __name__ == "__main__":
    unittest.main()
