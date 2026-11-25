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


class TestPreferredHeadings(unittest.TestCase):
    def test_rocket_lab_nice_to_have_heading(self):
        # Rocket Lab (Wallops Island) "Test and Launch Operations Engineer I": the 2+ years line sits under
        # "THESE QUALIFICATIONS WOULD BE NICE TO HAVE" and was read as the minimum (it is 1+).
        txt = ("QUALIFICATIONS TEST & LAUNCH OPERATIONS ENGINEER I\n"
               "Bachelor's Degree in Engineering (preferably Aerospace, Mechanical, Electrical, Chemical, or Mechatronic Engineering)\n"
               "1+ years of experience in engineering design, test and/or operations, electrical/software engineering\n"
               "2+ years of relevant experience will be considered in lieu of a degree\n"
               "THESE QUALIFICATIONS WOULD BE NICE TO HAVE\n"
               "2+ years of experience in engineering design, test, and/or operations\n"
               "Background in Avionics equipment design/operations\n")
        r = scan.requirements(txt)
        self.assertEqual(r["minYears"], 1)
        self.assertEqual(scan.fit(scan.PROFILE, r, "Test and Launch Operations Engineer I")[0], "Yes")
        self.assertIn("1+ years of experience", r["reqSnippet"]); self.assertNotIn("Background in Avionics", r["reqSnippet"])

    def test_other_heading_shapes_and_non_headings(self):
        base = "Minimum Qualifications:\nBS in Mechanical Engineering\n0-1 years of experience\n"
        for heading in ("What would be a plus:", "It would be great if you have", "Bonus points:", "NICE TO HAVE", "Desired skills"):
            r = scan.requirements(base + heading + "\n5+ years of experience with FEA\n")
            self.assertEqual(r["minYears"], 0, heading)
        # a bullet that merely says 'preferred' must not cut the requirements short
        r = scan.requirements("Minimum Qualifications:\nBS in Mechanical Engineering\nExperience with ANSYS preferred\n3+ years of experience required\n")
        self.assertEqual(r["minYears"], 3)

class TestScopeWords(unittest.TestCase):
    def test_composites_and_propellant_are_in_field(self):
        # Castelion 2026-11-17: these manufacturing roles were dropped for lacking a field word while
        # "Manufacturing Engineer, Solid Rocket Motors" passed
        self.assertTrue(scan.in_scope("Manufacturing Engineer – Composite Motor Cases"))
        self.assertTrue(scan.in_scope("Manufacturing Engineer, Propellant"))
        self.assertEqual(scan.discipline("Manufacturing Engineer – Composite Motor Cases"), "Structures")
        self.assertEqual(scan.discipline("Manufacturing Engineer, Propellant"), "Propulsion")
        self.assertFalse(scan.in_scope("Manufacturing Engineer - General"))
        self.assertFalse(scan.in_scope("Composites Engineering Tech - 1st Shift"))  # GE Aerospace 2026-11-17: a technician role
        self.assertFalse(scan.in_scope("Mid Level Radio Frequency Engineer", True))  # Amentum 2026-11-18
        # generic boards (Leidos, Electric Boat, Aerospace Corp, Westinghouse) let these through as Yes/Maybe on 2026-11-17
        for t in ("Data Analyst", "Middleware Engineer", "Platform Engineer", "Enterprise Architect", "GIS Production Engineer",
                  "Scientist I - Inhalation Toxicologist Research Scientist", "BIM Engineer", "Computer Systems Analyst",
                  "Intermediate Health Physicist", "2027 Battery Engineer", "2027 Entry Level DSP & SDR Engineer",
                  "2027 Time and Frequency Systems Scientist", "ENGINEER METROLOGY 1", "Imbedded Engineer I/II", "SONAR Systems Engineer",
                  "Simulator Operation Engineer", "2027 Systems Architect", "Systems Analyst", "Digital Enterprise Design Disclosure Engineer",
                  "Quality Control Analyst - Work Package Control (Hawaii)", "Part-Time Research Support - Biomedical Engineering (Wong)"):
            self.assertFalse(scan.in_scope(t, True), t)
        for t in ("Mechanical Engineer - Battery Pack, Satellites (Starlink)", "Nuclear Safety Analyst", "Flight Safety Analyst", "Structural Analyst"):
            self.assertTrue(scan.in_scope(t, True), t)

class TestTitleLevels(unittest.TestCase):
    def test_phd_and_leading_staff_titles(self):
        r = scan.requirements("Bachelor's degree in aerospace engineering. 0+ years of experience.")
        self.assertEqual(scan.fit(scan.PROFILE, r, "2027 PhD Graduate - Trajectory Optimization Engineer")[0], "No")
        self.assertEqual(scan.fit(scan.PROFILE, r, "Staff GNC Analysis Engineer")[0], "No")
        self.assertNotEqual(scan.fit(scan.PROFILE, r, "Thermal Engineer - Assistant Staff")[0], "No")
        self.assertEqual(scan.fit(scan.PROFILE, r, "2027 Graduate - Missile GNC Engineer")[0], "Yes")
        self.assertEqual(scan.fit(scan.PROFILE, r, "Membrane Science and Engineering Post-master Student"), ("No", "MS title"))
        self.assertEqual(scan.fit(scan.PROFILE, r, "Computational Materials Scientist - Postdoctoral Researcher")[0], "No")
        self.assertNotEqual(scan.fit(scan.PROFILE, r, "AOT-IC Post-Bachelor's Engineering")[0], "No")

class TestGraduateDegrees(unittest.TestCase):
    def test_phd_named_as_the_degree(self):
        # Aerospace Corp "2027 Particle Induced Radiation Effects Scientist" (2026-11-18): Yes with "2027 grads named"
        t = ("Minimum Requirements:\n* PhD degree from an accredited college/university program in electrical engineering, physics, or related "
             "discipline (pursuing or conferred within last 12 months)\n* 0-1 year of industry work experience\n* Transcripts")
        r = scan.requirements(t); self.assertEqual(r["degree"], "PhD")
        self.assertEqual(scan.fit(scan.PROFILE, r, "2027 Particle Induced Radiation Effects Scientist"), ("No", "PhD required"))
        r = scan.requirements("Requirements\n* Master's degree in aerospace engineering from an accredited program\n* Strong fundamentals")
        self.assertEqual(r["degree"], "MS")
        r = scan.requirements("Requirements\n* MS or PhD in mechanical engineering\n* 0 years")
        self.assertEqual(r["degree"], "MS")
        # a bachelor's path anywhere keeps it BS
        r = scan.requirements("Requirements\n* Bachelor's, Master's or PhD in aerospace engineering\n* 0-2 years")
        self.assertEqual(r["degree"], "BS")
        r = scan.requirements("Requirements\n* BS in mechanical engineering; MS preferred\n* Graduate coursework in heat transfer a plus")
        self.assertEqual(r["degree"], "BS")
        # "B.S." followed by a space never matched the old bachelor regex (no word boundary after the period)
        r = scan.requirements("Requirements\n* B.S. in mechanical engineering\n* M.S. in aerospace engineering with 2 years of research")
        self.assertEqual(r["degree"], "BS")
        # no requirements heading at all -> the graduate-degree rule stays out of it
        r = scan.requirements("We are looking for someone with a Master's degree in aerospace engineering who loves rockets.")
        self.assertIsNone(r["degree"])

    def test_jhu_apl_headings(self):
        # JHU APL 2027 Graduate postings (2026-11-18): no recognized headings, so the "above and beyond" M.S. counted as required
        t = ("You meet our minimum qualifications for the job if you...\n* Are pursuing a B.S. in Aerospace or Mechanical Engineering, graduating by May 2027\n"
             "* Have a GPA of 3.0 or higher\nYou'll go above and beyond our minimum requirements if you...\n* Have an M.S. in Aerospace Engineering\n* Have 2 years of research experience")
        r = scan.requirements(t)
        self.assertEqual((r["degree"], r["minYears"]), ("BS", None))
        self.assertEqual(scan.fit(scan.PROFILE, r, "2027 Graduate - Aerospace & Thermal Engineering")[0], "Yes")

class TestLLNLHeadings(unittest.TestCase):
    def test_qualifications_we_desire_is_preferred(self):
        # LLNL (2026-11-18): "Qualifications We Desire" was read as part of the requirements, so a desired Master's counted
        t = ("Qualifications We Require\n* Bachelor's degree in mechanical engineering or related field\n* Experience with test equipment\n"
             "Qualifications We Desire\n* Master's degree in Engineering or related field.\n* Active DOE Q clearance\n* 5 years of experience")
        r = scan.requirements(t)
        self.assertEqual((r["degree"], r["minYears"]), ("BS", None)); self.assertNotIn("Desire", r["reqSnippet"] or "")

class TestUSStates(unittest.TestCase):
    def test_new_mexico_is_in_the_us(self):
        # LANL (2026-11-18): every posting is "Los Alamos, New Mexico"; "mexico" matched NON_US and the spelled-out state
        # had no US hint, so all 134 in-field LANL roles were dropped as non-US
        for loc in ("Los Alamos, New Mexico", "Albuquerque, New Mexico", "Huntsville, Alabama", "Washington, District of Columbia"):
            self.assertFalse(scan.NON_US.search(loc) and not scan.US_HINT.search(loc), loc)
        for loc in ("Mexico City, Mexico", "Guadalajara, Mexico", "Brossard", "Québec City, QC"):  # GE Vernova Brossard slipped in 2026-11-25
            self.assertTrue(scan.NON_US.search(loc) and not scan.US_HINT.search(loc), loc)

class TestSystems(unittest.TestCase):
    def test_systems_engineering_is_a_field(self):
        # Lockheed "Systems Engineer Asc - Early Career" (Orlando, 2026-11-25) was dropped: no field word in the title on a
        # non-generic board. Systems engineering is now a field (Kevin applies to these).
        for t in ("Systems Engineer Asc - Early Career", "Systems Integration/Test Engineer Asc - Early Career", "System Test Engineer I"):
            self.assertTrue(scan.in_scope(t), t)
        self.assertEqual(scan.discipline("Systems Engineer Asc - Early Career"), "Systems"); self.assertIn("Systems", scan.PROFILE["fields"])
        self.assertFalse(scan.in_scope("Systems Administrator"))

class TestGNC(unittest.TestCase):
    def test_gnc_is_a_field(self):
        # Kevin 2026-11-17: entry-level GNC roles are wanted too
        for t in ("GNC Engineer", "2027 GNC Spacecraft/Payload Control Systems Analyst", "Guidance and Control Engineer", "2027 Trajectory Optimization Engineer"):
            self.assertTrue(scan.in_scope(t), t); self.assertEqual(scan.discipline(t), "GNC", t)
        self.assertFalse(scan.in_scope("Systems Analyst", True))
        self.assertIn("GNC", scan.PROFILE["fields"])

class TestWordNumbers(unittest.TestCase):
    def test_fifteen_to_twenty_years(self):
        # X-energy "Mechanical Design Engineer (Steam Generator)" R100796-1, 2026-11-16: word numbers above ten and a
        # spaced word range were not read, so a 15-20 year role showed as "1 yr required" (Maybe)
        r = scan.requirements("Minimum Qualifications\nBachelor's degree in mechanical engineering required.\n"
                              "Typically, fifteen- twenty years of experience in an engineering role required.\n"
                              "One plus years of demonstrated hands-on experience developing hardware.")
        self.assertEqual(r["minYears"], 15)
        self.assertEqual(scan.fit(scan.PROFILE, r, "Mechanical Design Engineer")[0], "No")
        self.assertEqual(scan.requirements("Requirements\nTwelve years of engineering experience.")["minYears"], 12)

class TestLateRequiredSections(unittest.TestCase):
    def test_xenergy_level_qualifications_after_preferred(self):
        # X-energy "Mechanical Design Engineer" (2026-11-16): Minimum Qualifications say 1+ years, but the Job Level
        # Qualifications section AFTER Preferred Qualifications says Level IV = ten years, Level V = fifteen. Was judged Maybe.
        txt = ("Minimum Qualifications\n"
               "Bachelor's degree in mechanical engineering, or related engineering discipline from an accredited institution required.\n"
               "One plus years of demonstrated hands-on experience developing and delivering hardware is required. May include industry internship experience.\n"
               "Preferred Qualifications\n"
               "Experience with commercial nuclear power plant operations.\n"
               "Experience with NRC regulations.\n"
               "Job Level Qualifications:\n"
               "Level IV\n"
               "Level Tasks/Responsibilities\n"
               "Lead the execution of the core tasks without close supervision.\n"
               "Level Minimum Qualifications\n"
               "Typically, ten years of experience in an engineering role required.\n"
               "A master's degree in engineering may be in lieu of two years of experience.\n"
               "Level V\n"
               "Level Minimum Qualifications\n"
               "Typically, fifteen years of experience in an engineering role required.\n")
        scan.TODAY = TODAY
        r = scan.requirements(txt)
        self.assertGreaterEqual(r["minYears"], 10)
        self.assertEqual(scan.fit(scan.PROFILE, r, "Mechanical Design Engineer")[0], "No")
        # the ordinary case is unchanged: preferred section at the end is still cut
        r = scan.requirements("Minimum Qualifications\nBS in Aerospace Engineering\n0-2 years of experience\nPreferred Qualifications\n5+ years of experience with CFD\n")
        self.assertEqual(r["minYears"], 0)

class TestTiming(unittest.TestCase):
    def setUp(self): scan.TODAY = TODAY

    def test_grad_phrasings(self):
        for txt, want in [("Open to Class of 2027 graduates in Mechanical Engineering.", "2027"),
                          ("This role is for Spring 2027 graduates.", "2027"),
                          ("Candidates graduating between December 2026 and June 2027 are encouraged to apply.", "2027"),
                          ("Must have graduated by May 2026.", None)]:
            r = scan.requirements("BS in Aerospace Engineering. " + txt)
            if want: self.assertIn(want, r["gradReq"] or "", txt)
            else: self.assertIn("2026", r["gradReq"] or "")

    def test_timing_kinds(self):
        P = scan.PROFILE
        r = scan.requirements("BS in Aerospace Engineering. Open to Class of 2027 graduates.")
        self.assertEqual(scan.timing(P, r, "Associate Engineer"), ("2027", "Class of 2027"))
        r = scan.requirements("BS in Aerospace Engineering.")
        self.assertEqual(scan.timing(P, r, "2027 New Grad Thermal Engineer")[0], "2027")
        self.assertEqual(scan.timing(P, r, "Associate Thermal Engineer"), ("unstated", None))
        r = scan.requirements("BS in Aerospace Engineering. Candidates must be available to begin within 30-60 days of applying.")
        self.assertEqual(scan.timing(P, r, "Propulsion Engineer")[0], "immediate")
        scan.TODAY = dt.date(2027, 4, 5)  # past June 1 minus 60 days: now it is a usable window
        self.assertEqual(scan.timing(P, r, "Propulsion Engineer"), ("window", "start window open now"))
        scan.TODAY = TODAY
        r = scan.requirements("BS in Aerospace Engineering. Graduating between December 2026 and August 2028.")
        self.assertEqual(scan.timing(P, r, "Engineer I")[0], "window")

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


class LocationAndTitleSweepTests(unittest.TestCase):
    def test_india_and_gulf_locations_are_not_us(self):
        # Kevin 2026-11-25 pasted the radar: RTX "Associate Engineer-Mechanical Design (Hybrid)" in "IN-TS-HYDERABAD-012 ~ Plot No 12"
        # and Parsons "Associate Highway Design Engineer (UAE National)" were listed as Yes
        for loc in ("IN-TS-HYDERABAD-012 ~ Plot No 12 ~ SARVOTHAM BLDG", "Dubai, UAE", "Abu Dhabi, United Arab Emirates", "Riyadh, Saudi Arabia"):
            self.assertTrue(scan.NON_US.search(loc) and not scan.US_HINT.search(loc), loc)
        self.assertFalse(scan.NON_US.search("Indianapolis, IN") and not scan.US_HINT.search("Indianapolis, IN"))

    def test_highway_welding_auditor_titles_are_out(self):
        for t in ("Associate Highway Design Engineer (UAE National)", "ENGINEER WELDING 1- ET&D HIRING EVENT", "Nuclear Engineering Auditor"):
            self.assertFalse(scan.in_scope(t, True), t)
        for t in ("ENGINEER MECHANICAL 1- ET&D HIRING EVENT", "ENGINEER STRUCTURAL 1- ET&D HIRING EVENT", "Mechanical Engineer Associate - E1"):
            self.assertTrue(scan.in_scope(t, True), t)

