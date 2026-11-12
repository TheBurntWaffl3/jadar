"""Regression tests for the fit rules in scan.py. Each case exists because of a real posting that was judged wrong once.

Run from the repo root:  python3 -I -m unittest discover -s tests -v
"""
import datetime as dt, json, os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import scan  # noqa: E402

TODAY = dt.date(2026, 11, 12)


class FitCase(unittest.TestCase):
    def setUp(self):
        scan.TODAY = TODAY
        self.p = scan.PROFILE  # Kevin: BS, aero/mech majors, grad 2027-05, start 2027-06-01

    def judge(self, text, title="Mechanical Engineer"):
        r = scan.requirements(text)
        f, why = scan.fit(self.p, r, title)
        return r, f, why


class TestNormalization(FitCase):
    def test_curly_apostrophe(self):
        r, f, why = self.judge("Bachelor’s degree in Aerospace Engineering required. 0-1 years of experience.")
        self.assertEqual(r["degree"], "BS")
        self.assertIsNone(r["majorReq"])
        self.assertEqual(f, "Yes")

    def test_us_period_does_not_end_sentence(self):
        # "U.S." used to end the bachelor's sentence early, hiding the 3-year minimum that followed it.
        r, f, why = self.judge("Bachelor's degree from a U.S. accredited program with 3 years of engineering experience. Must be a U.S. citizen.")
        self.assertEqual(r["minYears"], 3)
        self.assertEqual(r["citizenship"], "US citizen")
        self.assertEqual(f, "No")
        self.assertIn("3+ yrs", why)

    def test_spelled_number_with_digit(self):
        r, f, why = self.judge("Minimum of two (2) years of relevant experience.")
        self.assertEqual(r["minYears"], 2)
        self.assertEqual(f, "No")

    def test_parenthesized_plus(self):
        r, f, why = self.judge("Requires (2+) years of experience in structural analysis.")
        self.assertEqual(r["minYears"], 2)
        self.assertEqual(f, "No")


class TestMinimumsOnly(FitCase):
    def test_preferred_heading_cuts(self):
        r, f, why = self.judge("Basic Qualifications:\nBachelor's degree in mechanical engineering\n0-2 years of experience\n"
                               "Preferred Qualifications:\n5+ years of experience with CFD")
        self.assertEqual(r["minYears"], 0)
        self.assertEqual(f, "Yes")

    def test_other_preferred_spellings_cut(self):
        for head in ("Desired Skills:", "Nice to have:", "Bonus points:", "Plusses:"):
            r, f, why = self.judge(f"Required Qualifications:\nBachelor's degree in aerospace engineering\n{head}\n5+ years of industry experience")
            self.assertIsNone(r["minYears"], head)
            self.assertEqual(f, "Maybe", head)

    def test_additional_heading_does_not_cut(self):
        # "Additional Qualifications" is still a requirements section, never a preferred one.
        r, f, why = self.judge("Required Qualifications:\nBachelor's degree in aerospace engineering\n"
                               "Additional Qualifications:\n3+ years of experience with thermal analysis")
        self.assertEqual(r["minYears"], 3)
        self.assertEqual(f, "No")


class TestYears(FitCase):
    def test_stated_years_beat_entry_title(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. 3+ years of experience required.", "Thermal Engineer I")
        self.assertEqual(r["minYears"], 3)
        self.assertEqual(f, "No")
        self.assertIn("3+ yrs required", why)

    def test_tiered_posting_uses_entry_tier(self):
        r, f, why = self.judge("Bachelor's degree in aerospace engineering.\nLevel I: 0-2 years of experience\nLevel II: 2-5 years of experience\n"
                               "Level III: 5+ years of experience", "Structural Engineer")
        self.assertEqual(r["minYears"], 0)
        self.assertEqual(f, "Yes")

    def test_untiered_uses_max_minimum(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. 2+ years of experience with CAD. 4+ years of experience with FEA.")
        self.assertEqual(r["minYears"], 4)
        self.assertEqual(f, "No")

    def test_no_degree_path_experience_skipped(self):
        r, f, why = self.judge("Bachelor's degree in engineering, or Associate's degree with five years of experience.")
        self.assertIsNone(r["minYears"])
        self.assertEqual(f, "Maybe")
        r, f, why = self.judge("Bachelor's degree in aerospace engineering. High school diploma and 4 years of experience in lieu of a degree.")
        self.assertIsNone(r["minYears"])
        self.assertEqual(f, "Maybe")
        r, f, why = self.judge("Bachelor's degree in mechanical engineering, or 6 years of experience in lieu of a degree.")
        self.assertIsNone(r["minYears"])

    def test_equivalent_combination_is_a_real_minimum(self):
        # Boeing
        r, f, why = self.judge("Bachelor's degree and 3+ years of related work experience or an equivalent combination of education and experience",
                               "Structural Analysis Engineer")
        self.assertEqual(r["minYears"], 3)
        self.assertEqual(f, "No")
        self.assertIn("3+ yrs required", why)


class TestSchoolExperience(FitCase):
    def test_counts_on_same_line(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. 2+ years of relevant experience, including internships and co-ops.")
        self.assertEqual(r["minYears"], 2)
        self.assertTrue(r["schoolExpOk"])
        self.assertEqual(f, "Maybe")
        self.assertIn("school/internship exp counts", why)

    def test_does_not_count_on_other_line(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering.\n2+ years of relevant experience.\nWe value internship and student project team experience.")
        self.assertEqual(r["minYears"], 2)
        self.assertFalse(r["schoolExpOk"])
        self.assertEqual(f, "No")

    def test_one_year_with_school_is_yes(self):
        r, f, why = self.judge("Bachelor's degree in aerospace engineering. 1+ years of experience, including internships or research.")
        self.assertEqual(r["minYears"], 1)
        self.assertEqual(f, "Yes")


class TestMajor(FitCase):
    def test_other_majors_only_is_no(self):
        # BWXT Radiation Shielding
        r, f, why = self.judge("Basic Qualifications:\nBachelor's degree in nuclear engineering or radiation health physics\n0-2 years of experience",
                               "Radiation Shielding Engineer")
        self.assertTrue(r["majorReq"].startswith("only:"), r["majorReq"])
        self.assertEqual(f, "No")
        self.assertTrue(why.startswith("degree must be nuclear engineering"), why)

    def test_other_major_or_related_downgrades_yes_to_maybe(self):
        r, f, why = self.judge("Bachelor of Science in Electrical Engineering or related field. 0-2 years experience", "Test Engineer")
        self.assertEqual(r["majorReq"], "related: electrical engineering")
        self.assertEqual(f, "Maybe")
        self.assertIn("major not named (electrical engineering or related)", why)

    def test_his_major_named_is_fine(self):
        for s in ("Bachelor's degree in Aerospace, Mechanical, or Electrical Engineering",
                  "Bachelor's degree in Aeronautical or Astronautical Engineering",
                  "Bachelor's degree in Engineering Mechanics or Physics"):
            self.assertIsNone(scan.major_req(self.p, s), s)

    def test_any_engineering_stem_technical_fine(self):
        for s in ("Bachelor's degree in any engineering discipline. 0-1 years of experience",
                  "Bachelor's degree in a STEM field. 0-1 years of experience",
                  "Bachelor's in a technical discipline. 0-1 years of experience",
                  "Bachelor's degree in Engineering, Physics, or a related technical field. 0-1 years of experience"):
            r, f, why = self.judge(s)
            self.assertIsNone(r["majorReq"], s)
            self.assertEqual(f, "Yes", s)


class TestDegreeAndClearance(FitCase):
    def test_ms_phd_required_is_no(self):
        r, f, why = self.judge("Master's degree required in aerospace engineering.")
        self.assertEqual(r["degree"], "MS"); self.assertEqual(f, "No"); self.assertEqual(why, "MS required")
        r, f, why = self.judge("PhD in aerospace engineering required.")
        self.assertEqual(r["degree"], "PhD"); self.assertEqual(f, "No")
        r, f, why = self.judge("MS in Mechanical Engineering with 2 years of experience.")  # no bachelor's path at all
        self.assertEqual(r["degree"], "MS"); self.assertEqual(f, "No")
        r, f, why = self.judge("Bachelor's degree in mechanical engineering required. Master's degree preferred. 0-2 years of experience")
        self.assertEqual(r["degree"], "BS"); self.assertEqual(f, "Yes")

    def test_active_clearance_required_is_no(self):
        cases = ["This position requires an active Secret clearance.",
                 "Current in-scope Secret clearance required, Top Secret preferred.",
                 "Active and existing security clearance required.",
                 "This position requires the candidate to hold a TS/SCI clearance with polygraph."]
        for text in cases:
            r, f, why = self.judge("Bachelor's degree in aerospace engineering. 0-1 years of experience. " + text, "Thermal Engineer")
            self.assertIn("active req", r["clearance"] or "", text)
            self.assertEqual(f, "No", text)
            self.assertEqual(why, "active clearance required", text)
        r = scan.requirements("Current in-scope Secret clearance required, Top Secret preferred.")
        self.assertEqual(r["clearance"], "TS/SCI (active req.)")

    def test_obtainable_clearance_is_not_no(self):
        for text in ["Preferred: Active DoD SECRET clearance.",
                     "Must have the ability to obtain a Secret clearance.",
                     "Must be able to obtain and maintain a DoD security clearance."]:
            r, f, why = self.judge("Bachelor's degree in aerospace engineering. 0-1 years of experience. " + text, "Thermal Engineer")
            self.assertIn("obtain", r["clearance"] or "", text)
            self.assertEqual(f, "Yes", text)


class TestWindows(FitCase):
    def test_grad_window_before_2027_is_no(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. Must graduate by May 2026.", "New Grad Mechanical Engineer")
        self.assertIn("2026", r["gradReq"]); self.assertEqual(f, "No"); self.assertEqual(why, "grad window ends 2026")
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. Expected graduation date of December 2026.", "Associate Engineer")
        self.assertEqual(f, "No")

    def test_start_before_2027_is_no(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. Start date: June 2026.", "New Grad Mechanical Engineer")
        self.assertIn("2026", r["startReq"]); self.assertEqual(f, "No"); self.assertEqual(why, "start 2026")

    def test_2027_grads_named_is_yes(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. Graduating in December 2026 or May 2027.", "Engineer, New Grad")
        self.assertEqual(f, "Yes"); self.assertEqual(why, "2027 grads named")

    def test_2026_title_is_maybe(self):
        r, f, why = self.judge("BS in Mechanical Engineering. 0+ years", "2026 New Grad Mechanical Engineer")
        self.assertEqual(f, "Maybe"); self.assertIn("2026 new-grad cycle", why)

    def test_2027_title_is_yes(self):
        r, f, why = self.judge("BS in Mechanical Engineering.", "Mechanical Engineer (2027 Grads)")
        self.assertEqual(f, "Yes"); self.assertEqual(why, "2027 grads named")

    def test_start_window_relativity(self):
        r, f, why = self.judge("Candidates must be available to begin within 30-60 days of applying. Bachelor of Science in Mechanical Engineering",
                               "Propulsion Engineer")
        self.assertEqual(r["startWindow"], "start within 60 days of applying")
        self.assertEqual(f, "Maybe")
        self.assertIn("apply after Apr 2, 2027", why)
        r, f, why = self.judge("Bachelor's in aerospace engineering. Must be available to start immediately.", "Test Engineer")
        self.assertEqual(r["startWindow"], "immediate start (within ~30 days)")
        self.assertEqual(f, "Maybe"); self.assertIn("apply after May 2, 2027", why)


class TestGpaAndDeadlines(FitCase):
    def test_gpa(self):
        r, f, why = self.judge("Bachelor's degree in aerospace engineering. Minimum GPA of 3.0 required. 0-1 years of experience")
        self.assertEqual(r["gpaReq"], "3.0"); self.assertEqual(f, "Yes"); self.assertIn("min GPA 3.0", why)
        r = scan.requirements("Bachelor's degree in aerospace engineering. 3.2 GPA or higher.")
        self.assertEqual(r["gpaReq"], "3.2")

    def test_deadlines(self):
        r, f, why = self.judge("Bachelor's degree in aerospace engineering. 0-1 years of experience. Application Deadline: Nov 30, 2026")
        self.assertEqual(r["applyBy"], "2026-11-30"); self.assertEqual(f, "Yes"); self.assertIn("apply by 2026-11-30", why)
        self.assertEqual(scan.requirements("Posting end date: 2026-12-15")["applyBy"], "2026-12-15")  # Workday endDate / Oracle / validThrough
        self.assertEqual(scan.requirements("Apply by December 1st, 2026")["applyBy"], "2026-12-01")
        self.assertEqual(scan.requirements("Applications accepted until 12/31/2026")["applyBy"], "2026-12-31")

    def test_deadline_skips_until_filled_and_stale(self):
        self.assertIsNone(scan.requirements("Applications accepted until the position is filled.")["applyBy"])
        self.assertIsNone(scan.requirements("Posting closes: ongoing")["applyBy"])
        self.assertIsNone(scan.requirements("Application Deadline: Jan 15, 2026")["applyBy"])  # already passed
        r, f, why = self.judge("Bachelor's in mechanical engineering. 0-1 years of experience. Open until filled.")
        self.assertIsNone(r["applyBy"]); self.assertNotIn("apply by", why)


class TestTitles(FitCase):
    def test_entry_level_titles(self):
        for t in ("Associate, Instrumentation and Controls Engineer", "Nuclear Engineer (Associate)", "Engineer I, Thermal",
                  "Early Career Structural Engineer", "Entry Level Test Engineer", "Mechanical Engineer, New Grad",
                  "Engineering Development Program - Propulsion", "Rotational Engineer"):
            r, f, why = self.judge("Bachelor's degree in mechanical engineering.", t)
            self.assertEqual(f, "Yes", t)

    def test_senior_and_level_titles(self):
        r, f, why = self.judge("Bachelor's degree in mechanical engineering.", "Senior Thermal Engineer")
        self.assertEqual(f, "No"); self.assertEqual(why, "senior title")
        r, f, why = self.judge("Bachelor's degree in mechanical engineering.", "Structural Engineer III")
        self.assertEqual(f, "No")
        r, f, why = self.judge("Bachelor's degree in mechanical engineering.", "Structural Engineer II")
        self.assertEqual(f, "Maybe"); self.assertIn("level II", why)
        r, f, why = self.judge("Bachelor's degree in mechanical engineering.", "Thermal Engineer")
        self.assertEqual(f, "Maybe"); self.assertEqual(why, "yrs not stated")
        r, f, why = self.judge("Bachelor's degree in mechanical engineering. 1 year of experience required.", "Thermal Engineer")
        self.assertEqual(f, "Maybe"); self.assertEqual(why, "1 yr required")

    def test_out_of_field_dropped(self):
        for t in ("Security Analyst", "Health and Safety Engineer", "Full-Stack Engineer", "Site Reliability Engineer",
                  "IT Infrastructure Engineer", "Communication Systems Engineer", "Cable Harness Engineer", "Software Engineer, Flight",
                  "Thermal Engineering Intern", "Mechanical Engineering Co-op", "Engineering Manager, Propulsion", "Principal Structures Engineer",
                  "Electrical Engineer"):
            self.assertFalse(scan.in_scope(t), t)

    def test_in_field_kept(self):
        for t in ("Mechanical Engineer - Cable Magnets", "Nuclear Safety Analyst", "Flight Safety Analyst",
                  "Fluid Systems Engineer, Starlink Infrastructure", "Thermal Engineer", "Structural Analysis Engineer",
                  "Propulsion Test Engineer", "Naval Architect"):
            self.assertTrue(scan.in_scope(t), t)
        self.assertTrue(scan.in_scope("Engineer I", generic=True))      # generic boards: field checked in the description
        self.assertFalse(scan.in_scope("Engineer I", generic=False))
        self.assertEqual(scan.discipline("Nuclear Safety Analyst"), "Nuclear")
        self.assertEqual(scan.discipline("Mechanical Engineer - Cable Magnets"), "Mechanical")


class TestLocations(unittest.TestCase):
    def test_uk_locations_are_not_us(self):
        # GE Aerospace "Modern Engineering Apprenticeship, Prestwick, 2027 intake" leaked into the first live run
        for loc in ("Prestwick", "Glasgow, Scotland", "Cardiff, Wales", "Cheltenham, United Kingdom", "Munich, Germany", "Kruibeke, Belgium"):
            self.assertTrue(scan.NON_US.search(loc) and not scan.US_HINT.search(loc), loc)
        for loc in ("Huntsville, AL", "El Segundo, CA", "Laurel, MD", "United States - Remote", "Washington, DC"):
            self.assertFalse(scan.NON_US.search(loc) and not scan.US_HINT.search(loc), loc)
        self.assertFalse(scan.in_scope("Modern Engineering Apprenticeship, Prestwick, 2027 intake"))
        self.assertFalse(scan.in_scope("Mechanical Engineering Apprentice"))

class TestSecondProfile(unittest.TestCase):
    def setUp(self):
        scan.TODAY = TODAY
        with open(os.path.join(ROOT, "profiles", "kevin.json")) as f: p = json.load(f)
        p.update(name="Test Friend", slug="friend", majors=["nuclear"], gradDate="2028-05", earliestStart="2028-06-01")
        fd, self.path = tempfile.mkstemp(suffix=".json"); os.close(fd)
        with open(self.path, "w") as f: json.dump(p, f)
        self.p = scan.load_profile(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_major_and_year_follow_profile(self):
        sent = "Bachelor's degree in nuclear engineering or radiation health physics"
        self.assertIsNone(scan.major_req(self.p, sent))
        self.assertEqual(scan.major_req(scan.PROFILE, sent), "only: nuclear engineering, radiation health physics")
        r = scan.requirements("Bachelor's degree in electrical engineering or related field. 0-1 years of experience")
        self.assertEqual(scan.fit(self.p, dict(r), "Mechanical Engineer"), ("Maybe", "0 yrs required; major not named (electrical engineering or related)"))
        # Kevin's own majors are "other" majors for a friend: mechanical-only is a No for the nuclear profile, fine for Kevin.
        r = scan.requirements("Bachelor's degree in mechanical engineering. 0-1 years of experience")
        self.assertEqual(scan.fit(self.p, dict(r), "Mechanical Engineer"), ("No", "degree must be mechanical engineering"))
        self.assertEqual(scan.fit(scan.PROFILE, dict(r), "Mechanical Engineer")[0], "Yes")
        r = scan.requirements("Bachelor's degree in engineering. 0-1 years of experience")
        f, why = scan.fit(self.p, dict(r), "2027 New Grad Mechanical Engineer")
        self.assertEqual(f, "Maybe"); self.assertIn("2027 new-grad cycle", why)
        f, why = scan.fit(self.p, dict(r), "2028 New Grad Mechanical Engineer")
        self.assertEqual((f, why), ("Yes", "2028 grads named"))
        r = scan.requirements("Bachelor's degree in nuclear engineering. Must graduate by May 2027.")
        self.assertEqual(scan.fit(self.p, r, "Nuclear Engineer")[0], "No")
        r = scan.requirements("Bachelor's degree in nuclear engineering. Must be available to begin within 60 days of applying.")
        self.assertIn("apply after Apr 2, 2028", scan.fit(self.p, r, "Nuclear Engineer")[1])


if __name__ == "__main__":
    unittest.main()


class TestExtras(unittest.TestCase):
    """Extra listing facts (salary, work mode, employment type, travel, relocation, requirements snippet)."""
    def setUp(self): scan.TODAY = TODAY

    def test_salary_range_per_year(self):
        r = scan.requirements("The pay range for this role is $95,000 - $130,000 per year. 401k match up to $5,000.")
        self.assertEqual((r["salary"], r["salaryMin"], r["salaryMax"]), ("$95,000–$130,000/yr", 95000, 130000))
        r = scan.requirements("Compensation: $95K–$130K")
        self.assertEqual((r["salary"], r["salaryMin"], r["salaryMax"]), ("$95,000–$130,000/yr", 95000, 130000))
        r = scan.requirements("Salary range USD 95,000 to 130,000 annually")
        self.assertEqual(r["salary"], "$95,000–$130,000/yr")

    def test_salary_hourly_annualized(self):
        r = scan.requirements("Hourly rate: $45.00 - $52.00 per hour")
        self.assertEqual((r["salary"], r["salaryMin"], r["salaryMax"]), ("$45–$52/hr", 93600, 108160))

    def test_salary_single_number_skips_bonuses(self):
        r = scan.requirements("We offer a $1,000 sign-on bonus. This role has a base salary of $85,000.")
        self.assertEqual((r["salary"], r["salaryMin"], r["salaryMax"]), ("$85,000/yr", 85000, 85000))
        r = scan.requirements("$500 referral bonus. Benefits include a 401k match.")
        self.assertIsNone(r["salary"])

    def test_work_mode(self):
        self.assertEqual(scan.requirements("This position is hybrid (3 days on site).")["workMode"], "Hybrid")
        self.assertEqual(scan.requirements("This role is not eligible for remote work.")["workMode"], "On-site")
        self.assertEqual(scan.requirements("Location: Remote (US). Occasional onsite visits.")["workMode"], "Remote")
        self.assertEqual(scan.requirements("Work on-site at our Hawthorne factory.")["workMode"], "On-site")

    def test_employment_travel_relocation(self):
        r = scan.requirements("Full-time. Ability to travel up to 25% of the time. Relocation assistance is available.")
        self.assertEqual((r["employment"], r["travel"], r["relocation"]), ("Full-time", "up to 25%", True))
        r = scan.requirements("Part time contract. Travel: 10-20%. No relocation assistance.")
        self.assertEqual((r["employment"], r["travel"], r["relocation"]), ("Part-time", "10-20%", False))
        self.assertEqual(scan.requirements("Occasional travel to test sites.")["travel"], "occasional")
        self.assertEqual(scan.requirements("Temporary 6-month assignment.")["employment"], "Temporary")

    def test_req_snippet(self):
        r = scan.requirements("Basic Qualifications:\n- BS in Mechanical Engineering\n- 0-2 years of experience\n- CAD skills\n\nPreferred Qualifications:\n- FEA")
        self.assertEqual(r["reqSnippet"], "BS in Mechanical Engineering · 0-2 years of experience · CAD skills")
        long = "Requirements:\n" + "\n".join(f"- bullet number {i} with some words in it" for i in range(40))
        snip = scan.requirements(long)["reqSnippet"]
        self.assertLessEqual(len(snip), 501); self.assertTrue(snip.endswith("…")); self.assertTrue(snip.startswith("bullet number 0"))
        self.assertIsNone(scan.requirements("No heading here. 2+ years of experience.")["reqSnippet"])

    def test_absent_fields_and_fit_unchanged(self):
        r = scan.requirements("Bachelor's degree and 3+ years of related work experience or an equivalent combination of education and experience")
        for k in ("salary", "salaryMin", "salaryMax", "workMode", "employment", "travel", "relocation", "reqSnippet"):
            self.assertIsNone(r[k], k)
        self.assertEqual(scan.fit(scan.PROFILE, r, "Structural Analysis Engineer"), ("No", "3+ yrs required"))
