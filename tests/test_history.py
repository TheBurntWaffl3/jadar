"""history.json: every Yes/Maybe posting ever listed, never pruned; firstSeen kept, lastSeen moves, facts refreshed."""
import os, sys, json, unittest, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scan

def role(url, fit="Yes", title="Thermal Engineer I", **kw):
    r = dict(url=url, fit=fit, title=title, company="Fake Co", sector="Space", location="Hawthorne, CA", discipline="Thermal",
             date="2026-11-10", dateKind="posted", firstSeen="2026-11-10", minYears=0, gradReq=None, startWindow=None)
    r.update(kw); return r

class HistoryTests(unittest.TestCase):
    def test_upsert_keeps_first_seen_and_never_prunes(self):
        h = scan.load_history() if False else {"postings": {}}
        added = scan.update_history(h, [role("u/a"), role("u/b", fit="Maybe"), role("u/c", fit="No")], "2026-11-10")
        self.assertEqual(added, 2); self.assertNotIn("u/c", h["postings"], "No rows are not history")
        self.assertEqual(h["postings"]["u/a"]["firstSeen"], "2026-11-10")
        # next run: a is gone from the board, b changed title and fit, d is new
        added = scan.update_history(h, [role("u/b", fit="Yes", title="Thermal Engineer I (2027)", firstSeen="2026-11-10"), role("u/d", firstSeen="2026-11-12")], "2026-11-12")
        self.assertEqual(added, 1)
        self.assertIn("u/a", h["postings"]); self.assertEqual(h["postings"]["u/a"]["lastSeen"], "2026-11-10", "closed postings stay, lastSeen frozen")
        b = h["postings"]["u/b"]
        self.assertEqual((b["firstSeen"], b["lastSeen"], b["fit"], b["title"]), ("2026-11-10", "2026-11-12", "Yes", "Thermal Engineer I (2027)"))
        self.assertEqual(h["postings"]["u/d"]["firstSeen"], "2026-11-12")

    def test_load_history_tolerates_missing_file(self):
        saved = scan.DATA_DIR
        with tempfile.TemporaryDirectory() as d:
            scan.DATA_DIR = d
            try: self.assertEqual(scan.load_history(), {"postings": {}})
            finally: scan.DATA_DIR = saved

if __name__ == "__main__":
    unittest.main()
