#!/usr/bin/env python3
"""radar_out.json + sources.json -> roles.json, orgs.json (dashboard datasets).

Importable: datasets(out, src) -> (roles, orgs). As a script, reads data/radar_out.json (RADAR_DATA) and
sources.json next to this file and writes roles.json / orgs.json into the data dir."""
import json, os, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
PLAT = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby", "workday": "Workday", "sitemap": "Career site (sitemap + job data)",
        "eightfold": "Eightfold", "smartrecruiters": "SmartRecruiters", "oracle": "Oracle HCM", "rippling": "Rippling", "apl": "APL careers API",
        "rmk": "SuccessFactors", "paylocity": "Paylocity", "htmllist": "Career site (job list pages)", "icims": "iCIMS"}
GAPS = [  # organization, sector, platform, why not covered yet
 ("Kratos", "Hypersonics & defense tech", "Workday", "robots.txt disallows"),
 ("General Atomics (GA-ASI / GA-EMS)", "Primes", "BrassRing", "no public feed"),
 ("SAIC", "Primes", "unknown", "blocks automated reads"),
 ("Textron", "Primes", "custom", "script-rendered pages"),
 ("Spirit AeroSystems", "Primes", "iCIMS", "robots.txt disallows"),
 ("Spectral Energies", "Hypersonics & defense tech", "unknown", "no careers feed found"),
 ("Kord Technologies", "Hypersonics & defense tech", "unknown", "certificate error"),
 ("X-Bow Systems", "Hypersonics & defense tech", "ApplicantPro", "adapter not built"),
 ("AEDC (National Aerospace Solutions)", "Hypersonics & defense tech", "unknown", "no careers feed found"),
 ("Intuitive Machines", "Space", "unknown", "redirect loop"), ("York Space", "Space", "Paycor", "adapter not built"),
 ("Holtec", "Nuclear & fusion", "ADP", "no public feed"), ("Framatome", "Nuclear & fusion", "unknown", "blocks automated reads"),
 ("NuScale", "Nuclear & fusion", "unknown", "no careers feed found"), ("TAE Technologies", "Nuclear & fusion", "UKG", "UKG adapter not built"), ("Type One Energy", "Nuclear & fusion", "unknown", "no careers feed found"),
 ("Nano Nuclear", "Nuclear & fusion", "unknown", "no careers feed found"),
 ("Natura Resources", "Nuclear & fusion", "Gusto", "adapter not built"),
 ("Austal USA", "Maritime", "unknown", "no careers feed found"),
 ("Fincantieri Marinette", "Maritime", "unknown", "unreachable"),
 ("INL", "Labs & FFRDCs", "Taleo", "no public feed"), ("ORNL", "Labs & FFRDCs", "SuccessFactors", "certificate error"),
 ("Argonne", "Labs & FFRDCs", "Workday", "blocks automated reads"), ("PNNL", "Labs & FFRDCs", "iCIMS", "robots.txt disallows"),
 ("SwRI", "Labs & FFRDCs", "custom", "adapter not built"),
]
KEEP = ["id", "fit", "why", "company", "sector", "title", "location", "discipline", "minYears", "degree", "majorReq", "gpaReq", "startWindow", "applyBy", "gradReq", "startReq",
        "clearance", "citizenship", "date", "dateKind", "firstSeen", "url", "schoolExpOk", "desc_ok"]

def datasets(out, src):
    """out = parsed radar_out.json, src = parsed sources.json -> (roles, orgs) lists for the dashboard."""
    st = {s["org"]: s for s in out["status"]}
    fits = collections.Counter(r["company"] for r in out["roles"] if r["fit"] == "Yes")
    orgs = []
    for s in src:
        x = st.get(s["org"])
        if not x: continue
        status = "OK" if x["ok"] else "Failing"
        orgs.append(dict(org=s["org"], sector=s["sector"], platform=PLAT.get(s["type"], s["type"]), status=status,
                         note="" if x["ok"] else (x["error"] or "")[:90], roles=x["matches"] if x["ok"] else None, fits=fits.get(s["org"], 0) if x["ok"] else None))
    for o, sec, plat, why in GAPS:
        orgs.append(dict(org=o, sector=sec, platform=plat, status="Not covered yet", note=why, roles=None, fits=None))
    roles = [{k: r.get(k) for k in KEEP} for r in out["roles"]]
    return roles, orgs

def main():
    data = os.environ.get("RADAR_DATA", os.path.join(ROOT, "data"))
    with open(os.path.join(data, "radar_out.json")) as f: out = json.load(f)
    with open(os.path.join(ROOT, "sources.json")) as f: src = json.load(f)
    roles, orgs = datasets(out, src)
    json.dump(roles, open(os.path.join(data, "roles.json"), "w"), separators=(",", ":"))
    json.dump(orgs, open(os.path.join(data, "orgs.json"), "w"), separators=(",", ":"))
    print(f"roles.json {len(roles)} rows; orgs.json {len(orgs)} orgs ({sum(o['status']=='OK' for o in orgs)} OK, "
          f"{sum(o['status']=='Not covered yet' for o in orgs)} not covered)")

if __name__ == "__main__":
    main()
