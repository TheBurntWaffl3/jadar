#!/usr/bin/env python3
"""Parity check between two scans: python3 -I tools/compare.py OLD.json NEW.json

Each file is a radar_out.json (roles under "roles") or a roles.json list, e.g. the Claude scheduled task's dashboard data vs.
data/radar_out.json from GitHub Actions. Prints the Yes/Maybe postings only one side has, and fit changes on shared URLs."""
import json, sys, collections

def load(p):
    with open(p) as f: d = json.load(f)
    roles = d["roles"] if isinstance(d, dict) else d
    return {r["url"]: r for r in roles}

def main(a, b):
    A, B = load(a), load(b)
    fa = {u for u, r in A.items() if r["fit"] in ("Yes", "Maybe")}
    fb = {u for u, r in B.items() if r["fit"] in ("Yes", "Maybe")}
    print(f"{a}: {len(A)} roles, {len(fa)} Yes/Maybe   {b}: {len(B)} roles, {len(fb)} Yes/Maybe")
    for label, urls, src in (("Only in " + a, fa - fb, A), ("Only in " + b, fb - fa, B)):
        print(f"\n{label}: {len(urls)}")
        for u in sorted(urls, key=lambda u: (src[u]["fit"], src[u]["company"])):
            r = src[u]; other = (B if src is A else A).get(u)
            tail = f"  [other side: {other['fit']} - {other['why']}]" if other else "  [not in other scan]"
            print(f"  {r['fit']:5} {r['company']}: {r['title']}  ({r['why']}){tail}\n        {u}")
    changed = [(u, A[u], B[u]) for u in fa & fb if A[u]["fit"] != B[u]["fit"]]
    print(f"\nShared Yes/Maybe with a different fit: {len(changed)}")
    for u, x, y in changed: print(f"  {x['fit']} -> {y['fit']}  {x['company']}: {x['title']}  ({x['why']} | {y['why']})")
    c = collections.Counter((A.get(u, {}).get("fit", "-"), B.get(u, {}).get("fit", "-")) for u in set(A) | set(B))
    print("\nFit matrix (old -> new):", dict(sorted(c.items())))

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
