"""tailor.py: candidate selection, prompt safety, the draft record, and the no-config / no-master exits."""
import datetime as dt, json, os, sys, types, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tailor

TODAY = dt.date(2026, 11, 25)
ROLES = [
    {"url": "https://x/yes2027", "company": "Anduril", "title": "2027 New Grad GNC Engineer", "fit": "Yes", "timing": "2027", "date": "2026-11-20", "why": "2027 grads named", "location": "Costa Mesa, CA"},
    {"url": "https://x/yes", "company": "SpaceX", "title": "Thermal Engineer", "fit": "Yes", "timing": "unstated", "date": "2026-11-24", "why": "0 yrs required", "location": "Hawthorne, CA"},
    {"url": "https://x/maybe-saved", "company": "Blue Origin", "title": "Test Engineer", "fit": "Maybe", "timing": "unstated", "date": "2026-11-10", "why": "yrs not stated", "location": "Kent, WA"},
    {"url": "https://x/maybe", "company": "ULA", "title": "Loads Engineer", "fit": "Maybe", "timing": "unstated", "date": "2026-11-24", "why": "yrs not stated", "location": "Denver, CO"},
    {"url": "https://x/applied", "company": "Varda", "title": "Mechanical Engineer", "fit": "Yes", "timing": "2027", "date": "2026-11-24", "why": "", "location": "El Segundo, CA"},
    {"url": "https://x/drafted", "company": "Vast", "title": "Structures Engineer", "fit": "Yes", "timing": "2027", "date": "2026-11-24", "why": "", "location": "Long Beach, CA"},
    {"url": "https://x/redo", "company": "Stoke", "title": "Propulsion Engineer", "fit": "Yes", "timing": "2027", "date": "2026-11-01", "why": "", "location": "Kent, WA"},
]

class CandidateTests(unittest.TestCase):
    def test_order_and_skips(self):
        state = {"https://x/maybe-saved": "saved", "https://x/applied": "applied", "_doc": {"drafts": {"https://x/redo": {"status": "redo"}}}}
        drafts = {"v": 1, "drafts": {"https://x/drafted": {}, "https://x/redo": {}}}
        got = [r["url"] for r in tailor.candidates({"roles": ROLES}, state, drafts, TODAY, max_n=10)]
        self.assertEqual(got, ["https://x/maybe-saved", "https://x/yes2027", "https://x/redo", "https://x/yes"])
        self.assertEqual(len(tailor.candidates({"roles": ROLES}, state, drafts, TODAY, max_n=2)), 2)

    def test_posting_text_is_capped_and_labelled(self):
        t = tailor.posting_text(ROLES[1], "Thermal Engineer", "x" * 50000)
        self.assertLessEqual(len(t), tailor.MAX_DESC + 400); self.assertIn("Company: SpaceX", t); self.assertIn("POSTING:", t)

class FakeClient:
    """Stands in for anthropic.Anthropic(): records the request, returns a schema-shaped JSON text block."""
    def __init__(self, plan, stop="end_turn"):
        self.calls = []; self.plan = plan; self.stop = stop
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self.create))
    def create(self, **kw):
        self.calls.append(kw)
        block = types.SimpleNamespace(type="text", text=json.dumps(self.plan))
        return types.SimpleNamespace(stop_reason=self.stop, content=[block], usage=types.SimpleNamespace(input_tokens=1200, output_tokens=800, cache_read_input_tokens=900))

PLAN = {"summary": "Aerospace senior with thermal test experience.", "keywords": ["thermal", "LabVIEW"], "coverage": [{"keyword": "LabVIEW", "present": True, "where": "Rocket Lab bullet"}],
        "bullets": [{"section": "Rocket Lab", "original": "Built LabVIEW DAQ for preload tests", "revised": "Built a LabVIEW DAQ (load cell, dial indicators) for preload tests", "why": "DAQ named in minimum qualifications"}],
        "skills_line": "Test & Instrumentation: LabVIEW, DAQ", "section_order": ["Education", "Technical Experience"], "gaps": ["No thermal vacuum experience"], "note": "Confirm the DAQ channel count."}

class CallTests(unittest.TestCase):
    def test_request_shape_and_plan(self):
        c = FakeClient(PLAN)
        plan = tailor.tailor_one(c, "MASTER " * 100, ROLES[1], "Thermal Engineer", "Minimum qualifications: BS, LabVIEW. " * 20)
        kw = c.calls[0]
        self.assertEqual(kw["model"], "claude-opus-5-5"); self.assertEqual(kw["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(kw["fallbacks"], "default"); self.assertIn("server-side-fallback-2026-07-01", kw["betas"])
        self.assertTrue(all(b.get("cache_control") for b in kw["system"])); self.assertIn("Never invent", kw["system"][0]["text"])
        self.assertIn("MASTER MASTER", kw["system"][1]["text"]); self.assertIn("POSTING:", kw["messages"][0]["content"])
        self.assertEqual(plan["bullets"][0]["section"], "Rocket Lab"); self.assertEqual(plan["_usage"]["cached"], 900)

    def test_refusal_raises(self):
        with self.assertRaises(RuntimeError): tailor.tailor_one(FakeClient(PLAN, stop="refusal"), "m" * 300, ROLES[1], "T", "d" * 400)

class ExitTests(unittest.TestCase):
    def test_not_configured_does_nothing(self):
        for k in ("ANTHROPIC_API_KEY", "STATE_REPO", "STATE_TOKEN"): os.environ.pop(k, None)
        tailor.main()  # prints and returns; must not raise

    def test_drafts_url_follows_state_path(self):
        os.environ["STATE_REPO"] = "o/r"; os.environ.pop("STATE_PATH", None); os.environ.pop("DRAFTS_PATH", None)
        self.assertEqual(tailor.drafts_url(), "https://api.github.com/repos/o/r/contents/drafts.json")
        os.environ["STATE_PATH"] = "kevin/state.json"
        self.assertEqual(tailor.drafts_url(), "https://api.github.com/repos/o/r/contents/kevin/drafts.json")
        os.environ.pop("STATE_PATH"); os.environ.pop("STATE_REPO")

if __name__ == "__main__":
    unittest.main()
