# Job Radar

Daily read-only scan of ~115 organizations' own job boards for entry-level aerospace,
mechanical, nuclear and naval engineering roles. Run by a scheduled Claude task:

    timeout 2400 python3 -I scan.py && python3 -I build_dash.py

- `scan.py`: fetches job boards (fixed host allowlist built from `sources.json`, honors robots.txt), reads each full description, and judges fit.
- `sources.json`: the organizations and how each board is read.
- `build_dash.py`: turns `radar_out.json` into the dashboard datasets.

The scheduled task checks each file's SHA-256 against hashes in its own instructions before running anything.
