import json, os, shutil, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build_dash, build_page

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "radar_out.sample.json")

def embedded(html):
    return json.loads(html.split('<script id="data" type="application/json">')[1].split("</script>")[0].replace("<\\/", "</"))

class PageTests(unittest.TestCase):
    def test_immediate_roles_hidden_by_default(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle")
        self.assertIn("immediate-start role", html); self.assertIn('id="imm-note"', html); self.assertIn("hidden until spring", html)
        self.assertIn("tasap-hidden", html)
        self.assertTrue(any(r.get("timing") == "immediate" for r in self.out["roles"]), "fixture keeps an immediate-start role")

    def test_timing_sort_filter_pills(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle")
        i = html.index('id="sort"'); first = html[i:].index("<option")
        self.assertTrue(html[i + first:].startswith('<option value="fit2027">Sort: Fit · 2027 first</option>'), "2027-first is the first sort option")
        self.assertIn("sort: 'fit2027'", html, "and the default")
        self.assertIn('id="only2027"', html); self.assertIn("2027 only", html)
        for o in ("Says 2027", "States a window", "Not stated", "Immediate start"): self.assertIn(o, html)
        for c in ("tag t2027", "tag twindow", "tag tasap"): self.assertIn(c, html)
        self.assertIn("kv('Timing'", html)
        self.assertEqual({r["timing"] for r in self.out["roles"]}, {"2027", "window", "unstated", "immediate"}, "fixture covers all four")

    def test_filters(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle")
        for needle in ("jadar.filters.v1", "DMV (MD · DC · VA)", "West Coast (CA OR WA AK HI)", "More filters", "Clear filters",
                       "function parseLoc(", 'id="loc"', 'id="pay"', 'id="closing"', "has Terps found", "new today", "only roles that state pay"):
            self.assertIn(needle, html)
        locs = [r["location"] for r in self.out["roles"]]
        self.assertTrue(any(", WA" in l for l in locs) and any(", CA" in l for l in locs) and any("Remote" in l for l in locs))

    def test_terps_found_block(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle")
        self.assertIn("people.json", html)
        self.assertIn("Terps found here", html)
        self.assertIn("Connect sync in Data to see Terps found at this company.", html)
        self.assertIn("linkedin\\.com", html)           # host check on every profile link
        self.assertIn("Not searched yet (next weekly run).", html)
        for leak in ("Jane Doe", '"companies"', "janedoe"):  # people data is fetched at runtime, never embedded
            self.assertNotIn(leak, html)

    def test_repost_terps_toggle_and_draft_note(self):
        html = build_page.build(self.out, self.src, "Kevin Kyle", {"name": "Kevin Kyle", "majors": ["aerospace"], "gradDate": "2027-05"})
        # 1. re-post fingerprint
        self.assertIn("const fpOf = r => companyKey(r.company) + '|' + norm(r.title)", html)
        self.assertIn("(re-post)", html); self.assertIn("function fpMap()", html); self.assertIn("effStatus", html)
        # 2. Terps ranking toggle
        self.assertIn("jadar.terps.v1", html); self.assertIn(">Likely to reply<", html); self.assertIn('data-terps="all"', html)
        self.assertIn("function rankPeople(", html); self.assertIn("same field", html); self.assertIn("recent grad", html)
        # 3. draft note: default template baked from the profile, editable template stored under its own key, copy only
        self.assertIn("jadar.notetpl.v1", html)
        blob = embedded(html)
        self.assertIn("University of Maryland aerospace engineering senior (graduating May 2027)", blob["noteTemplate"])
        self.assertTrue(blob["noteTemplate"].endswith("Thanks so much,\nKevin"))
        self.assertIn("{first}", blob["noteTemplate"]); self.assertIn("{title}", blob["noteTemplate"]); self.assertIn("{company}", blob["noteTemplate"])
        self.assertIn('data-draft="', html); self.assertIn('data-copy="1"', html); self.assertIn("navigator.clipboard.writeText", html)
        self.assertNotIn("sendBeacon", html); self.assertNotIn("mailto:", html)
        for leak in ("Jane Doe", '"companies"', "janedoe"): self.assertNotIn(leak, html)
        # the fixture's re-post row is present: same company + title, different URL
        ids = {r["id"]: r for r in blob["roles"]}
        self.assertEqual((ids["r0014"]["company"], ids["r0014"]["title"]), (ids["r0002"]["company"], ids["r0002"]["title"])); self.assertNotEqual(ids["r0014"]["url"], ids["r0002"]["url"])
        self.assertEqual(build_page.note_template(None).split("\n")[-1], "Kevin")
        self.assertIn("nuclear engineering senior (graduating December 2028)", build_page.note_template({"name": "Pat Q", "majors": ["nuclear"], "gradDate": "2028-12"}))

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
        self.assertEqual(sum(r["fit"] == "Yes" for r in blob["roles"]), 6)
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


class FilterPersistenceTests(unittest.TestCase):
    def test_filters_do_not_persist(self):
        # 2026-11-18: a reload starts with every filter clear; only sort/dir and the More-filters toggle are remembered
        with open(FIXTURE) as f: out = json.load(f)
        with open(os.path.join(ROOT, "sources.json")) as f: src = json.load(f)
        html = build_page.build(out, src, "Kevin Kyle")
        save = html[html.index("function saveFilters()"):html.index("\n", html.index("function saveFilters()"))]
        self.assertIn("{v: 2, sort: state.sort, dir: state.dir, more: state.more}", save)
        for k in ("fit:", "q:", "loc:", "timing:"): self.assertNotIn(k, save)
        load = html[html.index("function loadFilters()"):html.index("\n", html.index("state.more = !!o.more"))]
        self.assertNotIn("FILTER_DEFAULTS", load)

class SourcesTests(unittest.TestCase):
    """sources.html: every board, its public link, what the last run saw, and the not-covered list."""
    def setUp(self):
        with open(FIXTURE) as f: self.out = json.load(f)
        with open(os.path.join(ROOT, "sources.json")) as f: self.src = json.load(f)
        self.html = build_page.build_sources(self.out, self.src, "Kevin Kyle")

    def test_rows_and_links(self):
        data = embedded(self.html); rows = {r["org"]: r for r in data["sources"]}
        for x in self.out["status"]: self.assertIn(x["org"], rows)
        for o, *_ in build_page.build_dash.GAPS: self.assertEqual(rows[o]["status"], "Not covered yet")
        ok = [r for r in data["sources"] if r["status"] == "OK"]
        self.assertTrue(ok); self.assertTrue(all(r["scanned"] == self.out.get("scanned") for r in ok))
        self.assertTrue(all(r["url"] for r in ok), [r["org"] for r in ok if not r["url"]])
        for needle in ('aria-current="page">Sources</a>', "Last scanned", "Boards we scan.", "sources.html"): self.assertIn(needle, self.html, needle)

    def test_board_urls(self):
        self.assertEqual(build_page.board_url({"type": "greenhouse", "id": "spacex"}), "https://job-boards.greenhouse.io/spacex")
        self.assertEqual(build_page.board_url({"type": "workday", "tenant": "blueorigin", "wd": 5, "site": "BlueOrigin"}), "https://blueorigin.wd5.myworkdayjobs.com/BlueOrigin")
        self.assertEqual(build_page.board_url({"type": "sitemap", "sitemaps": ["https://careers.l3harris.com/sitemap.xml"]}), "https://careers.l3harris.com")
        self.assertIsNone(build_page.board_url({"type": "greenhouse"}))

class TrackerTests(unittest.TestCase):
    """tracker.html: second page, same state file, no roles or personal data embedded."""

    def setUp(self):
        self.html = build_page.build_tracker("Kevin Kyle", today="2026-11-12")

    def test_pipeline_board(self):
        # 2026-11-25: Kevin "can't say I've been rejected or moved to first interview" -> a drag-and-drop stage board
        for needle in ("Pipeline.", 'id="board"', 'id="funnel"', "function moveTo(", "function markApplied(", "app.history", "data-view=\"table\"", "stage-interview", "Mark applied"):
            self.assertIn(needle, self.html, needle)

    def test_follow_up_and_up_next(self):
        for needle in ("Needs follow-up", "needsFollowUp", "FU_DAYS = 14", "Followed up today", 'id="upnext"', "Up next.", "stats five"):
            self.assertIn(needle, self.html, needle)

    def test_main_writes_both_pages(self):
        with tempfile.TemporaryDirectory() as d:
            data = os.path.join(d, "data"); site = os.path.join(d, "site"); os.makedirs(data)
            shutil.copy(FIXTURE, os.path.join(data, "radar_out.json"))
            env = dict(os.environ, RADAR_DATA=data, SITE_DIR=site)
            subprocess.run([sys.executable, "-I", build_page.__file__], check=True, env=env, cwd=ROOT, capture_output=True)
            self.assertTrue(os.path.exists(os.path.join(site, "index.html")))
            self.assertTrue(os.path.exists(os.path.join(site, "sources.html")))
            with open(os.path.join(site, "tracker.html")) as f: tracker = f.read()
            with open(os.path.join(site, "index.html")) as f: index = f.read()
        self.assertIn("<title>Tracker</title>", tracker)
        # both pages carry the nav and the same shared JS module (same storage keys, same merge, same sync)
        for html in (index, tracker):
            self.assertIn('href="index.html"', html); self.assertIn('href="tracker.html"', html)
            self.assertIn("window.JADAR = ", html); self.assertIn("'jadar.state.v1'", html); self.assertIn("'jadar.sync.v1'", html)
        self.assertIn('href="index.html" aria-current="page"', index)
        self.assertIn('href="tracker.html" aria-current="page"', tracker)

    def test_columns_statuses_import_panel(self):
        for col in ["Company", "Position", "Benefits", "Applied", "Posted", "Pay range", "Expected response", "First response", "Dates", "Contacted", "Status", "Notes"]:
            self.assertIn(f">{col}<", self.html, col)
        for st in ["applied", "screen", "interview", "offer", "rejected", "closed", "withdrawn"]:
            self.assertIn(f"'{st}'", self.html)
        self.assertIn("Import from your sheet", self.html); self.assertIn('id="tsv"', self.html)
        self.assertIn("Company, Position, Benefits, Applied, Posted, Pay Range, Expected Response, First Response, Dates, Appl. Link, Contacted", self.html)
        self.assertIn('id="export-csv"', self.html); self.assertIn('id="add-toggle"', self.html)
        self.assertIn('id="conn-add"', self.html); self.assertIn('id="place-add"', self.html)
        self.assertIn("st-rejected", self.html); self.assertIn("st-interview", self.html); self.assertIn("st-offer", self.html)

    def test_embeds_no_roles_or_personal_data(self):
        data = embedded(self.html)
        self.assertEqual(set(data), {"today", "profileName"})
        self.assertEqual(data["today"], "2026-11-12")
        with open(FIXTURE) as f: fx = json.load(f)
        for r in fx["roles"]:
            self.assertNotIn(r["url"], self.html); self.assertNotIn(r["title"], self.html)
        self.assertNotIn("Jane Doe", self.html); self.assertNotIn("ghp_", self.html)

    def test_radar_marks_applied_with_tracker_fields(self):
        # the radar page's setStatus seeds app.appliedOn / pay / posted and snapshots salary + date for the tracker
        self.assertIn("e.app.appliedOn = D.today", build_page.TEMPLATE)
        self.assertIn("if (!e.app.pay && r.salary) e.app.pay = r.salary", build_page.TEMPLATE)
        self.assertIn("if (r.salary) s.salary = r.salary; if (r.date) s.date = r.date", build_page.TEMPLATE)
        self.assertIn("function adoptManual()", build_page.TEMPLATE)
        # merge carries manual rows and the tracker lists
        self.assertIn("out.manual[k] = newer(a.manual[k], b.manual[k])", build_page.SHARED_JS)
        self.assertIn("out.tracker = newer(a.tracker, b.tracker)", build_page.SHARED_JS)
