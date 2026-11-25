# Bulk resume build: worker brief (used by the "Jadar cloud resume build" task and by ad-hoc bulk builds)

The caller replaces <BULK_DIR> with a scratch directory holding batch_NN.json files and tells each worker its NN.

You are building tailored one-page resumes for Kevin Kyle, one per job posting, from his master Word resume. Kevin asked
for a resume for every open "Yes" role, as fast as possible. Work through every item in your batch file, in order.
Read-only toward the outside world: never apply, sign in, submit anything, or fetch job sites. Do not run git.

## Inputs
- Batch: `<BULK_DIR>/batch_NN.json` (your number is in the
  prompt). Each item: url, company, title, slug, location, why, salary, discipline, reqSnippet (the posting's minimum
  qualification lines, may be empty), timing.
- Master: `/home/user/jadar-state/master/Kevin_Kyle_Lockheed_Martin_Resume.docx`. Rules: `/home/user/jadar-state/master/CLAUDE.md`
  (tailoring rules, per-company notes) and `/home/user/jadar-state/master/FACTS.md` (fixed facts). Read both once, first.
- Tool: `python3 -I /home/user/jadar/tools/build_resume.py`
  - `dump <docx>` prints every paragraph: index, kind (heading/bold/text/bullet), text; "⟶" separates left text from the
    right-aligned part (dates, locations). Run it once on the master and keep the listing in mind; indexes in a plan always
    refer to the MASTER's indexes.
  - `apply <master> <plan.json> <out.docx>`: plan keys: `set` {index: "new text"} (keeps formatting; keep "⟶" where the
    original has it), `delete` [indexes], `insert_after` {index: ["new paragraph", ...]} (copies that paragraph's formatting),
    `move` [{"range": [first, last], "after": index}] (moves a block of master paragraphs after another master paragraph).
  - `pdf <docx> <outdir>` prints `... pages=N`. N must be 1.
- Work dir: `<BULK_DIR>/work_NN/` (make it). Set
  `LO_PROFILE=<BULK_DIR>/lo_NN` in the environment of every
  `pdf` call so your LibreOffice does not fight the other workers.

## How to tailor (from master/CLAUDE.md; these win)
- Nothing invented. Only reorder, select, trim and re-word bullets Kevin already has. No new tools, sensors, numbers, dates.
- Fixed facts: exactly as listed in master/FACTS.md (titles, sensors, wording, degree line, graduation). Do not vary them.
- Lead with what the posting screens for (use reqSnippet; if empty, go by the title, the discipline and the company notes):
  - Test / instrumentation / systems test: DAQ, test procedure, load system, sensors first.
  - Analysis / stress / thermal / aerothermal: hypersonics section above SEDS; ANSYS and FEA bullets lead; Skills opens with
    the Analysis line; coursework leads with structures courses.
  - Design / manufacturing / mechanical: SEDS machining and GD&T, Terrapin layups, CAD skills line first.
  - Propulsion / fluids test: no P&ID or high-pressure line exists; lead with test + hardware bullets, do not stretch.
  - Systems engineering: Rocket Lab procedure/training and SEDS integration/test bullets first, Control of Aerospace Systems
    in coursework stays; do not claim MBSE/SysML.
  - GNC / controls: MATLAB solver, Python modeling, Control of Aerospace Systems; say in notes it is a stretch.
  - Nuclear / naval: thermal + structures analysis first (hypersonics), then Rocket Lab test; GPA prominent.
  - New-space (SpaceX, Blue Origin, Relativity, Stoke, Firefly, Rocket Lab...): hardware-first; "machined", "built",
    "fabricated", "launched" high on the page.
  - Defense primes (Lockheed, Northrop, RTX, BAE, L3Harris, HII, GD): LEADERSHIP section name; GPA prominent.
- Match the posting's vocabulary where true ("finite element analysis (FEA)", "ANSYS Mechanical", "test procedures",
  "data acquisition"). Never thermocouples.
- One page, every bullet fills its line (a bullet ending more than ~1 inch short of the margin is a defect; fix with
  Kevin's fuller original wording, never filler). Keep one-line bullets one line; a reworded bullet must be about the same
  length as the original. Machine learning lab keeps 2-3 bullets. If `pdf` says 2 pages: shorten the Analysis/Software
  skills line or restore shorter original bullets, rebuild.
- Near-identical roles (same company, same discipline) may share one plan: build the first, then reuse the plan file with
  only the wording that differs. Do not spend more than ~2 minutes of thought per resume; the tailoring is ordering + vocabulary.

## Per item
1. Write `work_NN/<slug>.plan.json`. 2. `apply` -> `work_NN/<slug>.docx`. 3. `pdf` -> `work_NN/<slug>.pdf`; check pages=1;
   fix and rebuild if not. 4. Copy the three files to `/home/user/jadar-state/resumes/` (same names). Do not touch any other
   file there. Skip an item only if the posting is clearly not a US engineering role for a 2027 aerospace BS (say why).

## Report (your final message; keep it short)
One line per item: `slug | built|skipped | one clause on what leads | gap note if any (e.g. "no P&ID experience; stretch")`.
Then the total built and skipped. Nothing else.
