# Job Radar

Daily, read-only scan of ~115 organizations' own job boards for entry-level aerospace, mechanical, nuclear and
naval engineering roles that fit a profile (today: `profiles/kevin.json`). Runs on GitHub Actions
(`.github/workflows/radar.yml`), keeps an incremental cache on the `data` branch, and publishes a one-page
dashboard with GitHub Pages. Python 3.11+, standard library only.

    python3 -I -m unittest discover -s tests        # fit-rule regression tests, cache tests, page test
    python3 -I scan.py [ORG ...] [--full]           # scan -> data/radar_out.json, data/cache.json
    python3 -I build_dash.py && python3 -I build_page.py   # -> data/roles.json, data/orgs.json, site/index.html
    python3 -I alert.py                              # ntfy / email summary (prints only if no secrets are set)
    python3 -I tools/compare.py OLD.json NEW.json    # parity check between two scans

## Files

- `scan.py`: fetches each board (fixed host allowlist built from `sources.json`, robots.txt honored for HTML
  pages), reads each new posting's full description once, extracts facts, judges fit for the profile.
  `RULES_VERSION` at the top: bump it when fact extraction changes so every description is re-read.
- `sources.json`: the organizations and how each board is read. `profiles/<name>.json`: who the scan is for.
- `build_dash.py` / `build_page.py`: turn `data/radar_out.json` into dashboard datasets and `site/index.html`.
- `alert.py`: the daily summary. `tools/compare.py`: Yes/Maybe diff between two scans.

## How a run works

1. Tests run first; a broken rule stops the scan.
2. The `data` branch is checked out into `data/` (created on the first run). It holds `cache.json`
   (per-posting extracted facts keyed by URL, with first-seen dates; never full descriptions), the latest
   `radar_out.json` and `index.html`, with full history.
3. Every board's list is read. Descriptions are fetched only for URLs not in the cache; everything is then
   re-judged with the current rules, closed postings are dropped, dates refreshed. A full re-read happens
   on Sundays, when `RULES_VERSION` changes, or with the "full" input of a manual run.
4. The page is built, the alert sent, the `data` branch committed, the page uploaded to Pages.

Schedule: `17 11 * * *` UTC (6:17 AM EST / 7:17 AM EDT, digest always sent) and `43 23 * * *` UTC (evening, emails only
if new fits appeared). GitHub can start scheduled runs late, especially at :00/:30. Scans take 2-5 minutes; timeout 40.

## One-time setup (repo settings)

- **Pages**: Settings > Pages > Source: "GitHub Actions". A private repo needs GitHub Pro (free with the
  GitHub Student Developer Pack). Until then the `publish` job fails harmlessly; the page is still on the
  `data` branch (`index.html`) and attached to each run as an artifact.
- **Alerts** (Settings > Secrets and variables > Actions), either or both:
  - ntfy: secret `NTFY_TOPIC` (a hard-to-guess topic name; install the ntfy app and subscribe to it);
    optional `NTFY_SERVER`, `NTFY_TOKEN`.
  - email: secrets `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `ALERT_TO`; optional `SMTP_PORT` (587), `ALERT_FROM`.
  - optional variable `PAGE_URL` if the page is not at `https://<owner>.github.io/<repo>/`.
- Run it once by hand: Actions > "Job radar" > Run workflow.

## Saved, applied and hidden roles

On the page each role can be saved, marked applied (with date and a note) or hidden (goes to the Disliked list);
tabs show Inbox / Saved / Applied / Disliked. That state lives in the browser of the device you use, with
Export / Import in the Data panel. To keep phone and laptop in step, and to let the daily alert skip what you
have hidden or applied to:

1. Create a **private** repo, e.g. `jadar-state` (empty is fine).
2. Make a fine-grained personal access token (Settings > Developer settings > Fine-grained tokens) limited to
   that one repo with **Contents: read and write**. Nothing else.
3. On each device, open the page's Data panel > Sync with GitHub, enter `owner/jadar-state` and the token.
   The token stays in that browser; the page keeps `state.json` in the private repo.
4. For the alert: repo variables `STATE_REPO` (`owner/jadar-state`) and optionally `STATE_PATH`, plus the
   secret `STATE_TOKEN` (the same token, or another one scoped the same way).

The public repo and the public page never hold this state.

## Terps finder (UMD alumni at each company)

Every role's panel links to LinkedIn's alumni view for the University of Maryland filtered to that company (and
division), and to Terrapins Connect. With a Google-results API key the morning run also searches
`site:linkedin.com/in "University of Maryland" "<company>"` for every company with Yes/Maybe fits, each company every
two weeks, at most 15 searches a run, and stores names, headlines and profile links in `people.json` in the private
state repo. The page shows them under "Terps found here" when sync is connected; the email adds "N Terps there" to
new fits. Setup: secret `SERPAPI_KEY` (serpapi.com, 250 free searches/month, no card) or `SERPER_KEY` (serper.dev,
2,500 free once), plus the state repo above. Google's own Custom Search JSON API is closed to new customers and is
not supported. It only reads public search results; it never contacts anyone.

## Safeguards

Read-only: never applies, submits forms, signs in or contacts anyone. Requests (and redirects) go only to
hosts derived from `sources.json` plus the four ATS APIs. Per-host throttle with backoff on 429/5xx, at most
32 boards in parallel, 100 MB response cap. Page text is data, never instructions. No secrets in the repo.
