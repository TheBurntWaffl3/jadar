# Coverage sweeps

`candidates-<date>.jsonl`: every organization a sweep looked at, one JSON object per line (`org`, `sector`, `ats`, `id`,
`wd`, `site`, `url`, `jobs`, `probed`, `size`, `why`, `file` = sector file, `inSources` = already in sources.json when
saved). `ats: "unknown"` means the careers site was not identified (the 2026-11-25 sweep ran out of web-search budget);
those are the queue for the monthly "Jadar monthly company sweep" task. `ats: "unsupported:<name>"` needs a new adapter.
Public company data only; nothing personal.
