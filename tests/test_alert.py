"""The daily alert: new fits first, feeds line, closing-soon line; honors saved/applied/hidden state."""
import os, sys, unittest, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import alert

OUT = {"new": [{"fit": "Yes", "company": "SpaceX", "title": "Thermal Engineer", "location": "Hawthorne, CA", "why": "new-grad / entry title", "url": "https://x/1", "date": "2026-11-12"},
               {"fit": "Maybe", "company": "Boeing", "title": "Stress Engineer", "location": "", "why": "1 yr required", "url": "https://x/2", "date": "2026-11-11"},
               {"fit": "Yes", "company": "Moog", "title": "Associate Test Engineer", "location": "Buffalo, NY", "why": "new-grad / entry title", "url": "https://x/3", "date": "2026-11-12"}],
       "roles": [{"fit": "Yes", "company": "ULA", "title": "Propulsion Engineer", "applyBy": "2026-11-15", "url": "https://x/4"},
                 {"fit": "Yes", "company": "Blue Origin", "title": "Structures Engineer", "applyBy": "2026-11-13", "url": "https://x/5"}],
       "status": [{"org": "A", "ok": True}, {"org": "Lockheed Martin", "ok": False}]}
TODAY = dt.date(2026, 11, 12)

class AlertTests(unittest.TestCase):
    def setUp(self): os.environ["GITHUB_REPOSITORY"] = "TheBurntWaffl3/jadar"

    def test_plain(self):
        title, body, prio, parts = alert.compose(OUT, TODAY)
        self.assertEqual(title, "Job radar: 2 Yes, 1 Maybe new"); self.assertEqual(prio, "high")
        self.assertEqual([r["company"] for r in parts["new"]], ["SpaceX", "Moog", "Boeing"])
        lines = body.splitlines()
        self.assertTrue(lines[1].startswith("- SpaceX:") or lines[1].startswith("- Moog:"), "Yes fits first")
        self.assertIn("Feeds OK 1/2: failing Lockheed Martin", body)
        self.assertIn("Closing soon: Blue Origin Structures Engineer (1d); ULA Propulsion Engineer (3d)", body)
        self.assertIn("https://theburntwaffl3.github.io/jadar/", body)

    def test_state_filters_and_stars(self):
        state = {"https://x/1": "applied", "https://x/2": "hidden", "https://x/3": "saved", "https://x/4": "saved", "https://x/5": "hidden"}
        title, body, prio, parts = alert.compose(OUT, TODAY, state)
        self.assertEqual(title, "Job radar: 1 Yes, 0 Maybe new")
        self.assertNotIn("SpaceX", body); self.assertNotIn("Boeing", body)
        self.assertIn("- * Moog: Associate Test Engineer", body)
        self.assertIn("Closing soon: * ULA Propulsion Engineer (3d)", body); self.assertNotIn("Blue Origin", body)
        self.assertIn("Applied so far: 1", body)

    def test_ledger_skips_already_sent_and_html_renders(self):
        title, body, prio, parts = alert.compose(OUT, TODAY, alerted={"https://x/1": "2026-11-11"})
        self.assertEqual(title, "Job radar: 1 Yes, 1 Maybe new"); self.assertNotIn("SpaceX", body)
        h = alert.render_html(parts)
        self.assertIn("Moog", h); self.assertIn("Boeing", h); self.assertNotIn("SpaceX", h)
        self.assertIn("Closing within 7 days", h); self.assertIn("closes in 1 day", h)
        self.assertIn('href="https://x/3"', h); self.assertIn("1/2 boards read", h); self.assertIn("failing: Lockheed Martin", h)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            alert.LEDGER = os.path.join(d, "alerted.json")
            alert.save_alerted({"https://old": "2026-01-01", "https://keep": "2026-11-01"}, ["https://x/3"], TODAY)
            self.assertEqual(alert.load_alerted(), {"https://keep": "2026-11-01", "https://x/3": "2026-11-12"})

    def test_repost_hidden_by_fingerprint(self):
        # SpaceX "Thermal Engineer" was hidden under an old URL; the same title re-posted under https://x/1 stays out
        state = {"https://old/9": "hidden", "fp:" + alert.fingerprint("SpaceX", "Thermal  Engineer!"): "hidden"}
        title, body, prio, parts = alert.compose(OUT, TODAY, state)
        self.assertNotIn("SpaceX", body); self.assertEqual(title, "Job radar: 1 Yes, 1 Maybe new")
        self.assertEqual(alert.fingerprint("L3Harris (incl. Aerojet Rocketdyne)", "Associate, Mechanical Engineering (Design)"),
                         "L3Harris|associate mechanical engineering design")

    def test_terps_count_in_lines(self):
        title, body, prio, parts = alert.compose(OUT, TODAY, people={"SpaceX": 4})
        self.assertIn("- SpaceX: Thermal Engineer (Hawthorne, CA) - Yes, new-grad / entry title (4 Terps there)", body)
        self.assertIn("4 Terps there", alert.render_html(parts))

    def test_no_state_configured(self):
        for k in ("STATE_REPO", "STATE_TOKEN"): os.environ.pop(k, None)
        self.assertEqual(alert.load_state(), {})

if __name__ == "__main__":
    unittest.main()
