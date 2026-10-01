"""Every number the documents quote, read from the tested results.

The documents never carry a hand-typed figure. A figure is either

    {{f key}}   the value, as recorded       {{n key}}   the same, with thousands separators

and `key` is defined here, computed from build/expected/*.txt, the output of the
queries as the attendee runs them (written by `build/verify.py --record`). If a
query changes, the figure changes with it; if a key is missing, rendering fails
instead of printing a stale number.

    python3 build/facts.py          # print every fact
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

EXPECTED = Path(__file__).resolve().parents[1] / "build/expected"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estate as E  # noqa: E402  (the hand-written facts the prose also relies on)


def _cell(c: str):
    c = c.strip()
    if c == "NULL":
        return None
    if c in ("TRUE", "FALSE"):
        return c == "TRUE"
    if len(c) >= 2 and c[0] == c[-1] == '"':
        return c[1:-1]
    try:
        return int(c)
    except ValueError:
        pass
    try:
        return float(c)
    except ValueError:
        return c


def rows(sid: str) -> list[dict]:
    """A recorded result as a list of {column: value}."""
    lines = [l for l in (EXPECTED / f"{sid}.txt").read_text().splitlines() if l.startswith("|")]
    cells = [[_cell(c) for c in l.strip().strip("|").split(" | ")] for l in lines]
    head = [str(h) for h in cells[0]]
    return [dict(zip(head, r)) for r in cells[1:]]


def one(sid: str) -> dict:
    r = rows(sid)
    assert len(r) == 1, f"{sid}: expected one row, got {len(r)}"
    return r[0]


def build() -> dict:
    f: dict = {}
    load = dict(l.split("=") for l in (EXPECTED / "LOAD.txt").read_text().split())
    f["nodes"], f["relationships"] = int(load["nodes"]), int(load["relationships"])

    lab = {r["label"]: r["n"] for r in rows("K1")}
    for key, label in [("components", "Component"), ("services", "Service"), ("datastores", "Datastore"),
                       ("teams", "Team"), ("journeys", "Journey"), ("incidents", "Incident"), ("changes", "Change"),
                       ("runbooks", "Runbook"), ("certificates", "Certificate"), ("alerts", "Alert")]:
        f[key] = lab[label]
    rel = {r["rel"]: r["n"] for r in rows("K2")}
    for t in ["DEPENDS_ON", "OWNS", "REQUIRES", "OWNED_BY", "ROOT_CAUSE", "ASSIGNED_TO", "AFFECTED", "DEPLOYED_TO",
              "COVERS", "FIRED_ON", "USES_CERT"]:
        f[f"rel_{t.lower()}"] = rel[t]

    k3 = one("K3")
    f["dep_total"], f["dep_unclassified"], f["dep_undeclared"] = k3["total"], k3["unclassified"], k3["undeclared"]
    f["dep_tracing"], f["dep_undeclared_other"] = k3["tracing"], k3["undeclared"] - k3["tracing"]
    f["dep_inactive"] = k3["inactive"]
    f["mutual_pairs"] = one("K4")["mutual_pairs"]
    k5 = one("K5")
    f.update(unowned=k5["unowned"], owned_by_disbanded=k5["owned_by_disbanded"], unrated=k5["unrated"], deprecated=k5["deprecated"])
    k6 = one("K6")
    f.update(teams_disbanded=k6["disbanded"], teams_no_pager=k6["active_without_pager"], teams_active=k6["teams"] - k6["disbanded"])
    k7 = one("K7")
    f["runbooks_stale"] = k7["stale"]
    k8 = one("K8")
    f.update(incidents_without_root=k8["without_any_root_cause"], incidents_no_customers=k8["without_customer_count"],
             first_incident=k8["first_incident"], last_incident=k8["last_incident"])
    k9 = one("K9")
    f.update(certs_renewal_unknown=k9["renewal_unknown"], certs_manual=k9["manual"], changes_last_24h=k9["changes_last_24h"])

    r0 = one("R0")
    f["ready_components"], f["ready_incidents"] = r0["components"], r0["incidents"]
    f["flags_refreshed"] = one("H2")["flags_refreshed"]

    # Part 1: the alert storm
    b1b = rows("B1b")
    f["storm_alerts"] = len(b1b)
    f["storm_teams"] = len({r["team"] for r in b1b})
    for role, key in [("likely cause", "storm_cause"), ("symptom", "storm_symptoms"), ("unrelated", "storm_unrelated")]:
        f[key] = sum(1 for r in b1b if r["role"] == role)
    f["cause_name"], f["cause_dependents"] = b1b[0]["component"], b1b[0]["alerting_dependents"]
    f["cause_owner"] = b1b[0]["team"]
    mins = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:])
    f["storm_minutes"] = max(mins(r["at"]) for r in b1b) - min(mins(r["at"]) for r in b1b)
    f["storm_surprises"] = " and ".join(f"`{r['component']}`" for r in b1b
                                        if r["component"] in ("campaign-svc", "agent-desktop-svc"))

    # Part 2: the radius
    rings = rows("B2")
    f["ring_sizes"] = ", ".join(str(r["services"]) for r in rings)
    f["rings"] = len(rings)
    f["services_worst"] = sum(r["services"] for r in rings)
    f["max_hops"] = max(r["hops"] for r in rings)
    b2b = {r["impact"]: r["services"] for r in rows("B2b")}
    f["services_proven"], f["services_assumed"], f["services_degrade"] = (
        b2b["fails (confirmed)"], b2b["fails (assumed)"], b2b["degrades only"])
    f["assumed_pct"] = round(100 * f["services_assumed"] / f["services_worst"])
    h1, h3, h5 = one("H1"), one("H3"), one("H5")
    f["journeys_worst"], f["journeys_proven"] = h1["journeys_down_worst_case"], h1["journeys_down_proven"]
    f["journeys_if_soft"] = h3["journeys_down_worst_case"]
    f["journeys_if_hard_proven"] = h5["journeys_down_proven"]
    f["journeys_if_hard_worst"] = h5["journeys_down_worst_case"]
    f["journeys_up"] = f["journeys"] - f["journeys_worst"]
    f["journeys_assumed"] = f["journeys_worst"] - f["journeys_proven"]
    b3b = {r["scenario"]: r for r in rows("B3b")}
    best, worst = b3b["best case (proven only)"], b3b["worst case (assume the unknowns)"]
    f["att03_best"], f["att03_worst"] = best["attempts_per_hour_at_0300"], worst["attempts_per_hour_at_0300"]
    f["att07_best"], f["att07_worst"] = best["attempts_per_hour_at_0700"], worst["attempts_per_hour_at_0700"]
    f["att12_worst"] = worst["attempts_per_hour_at_1200"]
    f["range_factor"] = round(f["att03_worst"] / f["att03_best"])
    f["ramp_factor"] = round(f["att07_worst"] / f["att03_worst"])
    tap = [r for r in rows("B3") if r["journey"] == "Tap to pay"][0]
    f["tap_status"] = tap["status"]

    # Part 3: the link
    c = rows("B2c")
    f["link"], f["link_seen_via"], f["link_first_seen"] = c[0]["unclassified_dependency"], c[0]["seen_via"], c[0]["first_seen"]
    f["link_services"], f["link_journeys"] = c[0]["services_at_stake"], c[0]["journeys_at_stake"]
    f["link2"], f["link2_services"], f["link2_journeys"] = c[1]["unclassified_dependency"], c[1]["services_at_stake"], c[1]["journeys_at_stake"]
    f["links_ranked"] = len(c)
    b6b = one("B6b")
    f.update(link_change=b6b["introduced_by"], link_team=b6b["team"], link_months=b6b["months_in_production"],
             link_reviewed=b6b["had_risk_review"], link_change_what=b6b["change"])
    b6c = rows("B6c")
    pre, post = b6c[0], b6c[1]
    f["replay_date"] = pre["as_of"]
    f["replay_services_before"], f["replay_services_after"] = pre["services_failing"], post["services_failing"]
    f["replay_journeys_before"], f["replay_journeys_after"] = pre["journeys_down"], post["journeys_down"]
    f["replay_att_before"], f["replay_att_after"] = pre["attempts_per_day"], post["attempts_per_day"]
    f["replay_att_factor"] = round(post["attempts_per_day"] / pre["attempts_per_day"])

    # Part 4: history and datastores
    b5 = rows("B5")
    f["b5_mismatch"] = sum(1 for r in b5 if r["flag"] == "MISMATCH")
    f["b5_review"] = sum(1 for r in b5 if r["flag"] == "REVIEW")
    f["b5_unrated"] = sum(1 for r in b5 if r["flag"] == "UNRATED")
    pc = [r for r in b5 if r["datastore"] == "profile-cache"][0]
    f["cache_tier"], f["cache_proven"], f["cache_worst"] = pc["declared_tier"], pc["journeys_proven"], pc["journeys_worst_case"]
    f["b5_top"] = b5[0]["datastore"]
    f["b5_second"], f["b5_second_tier"], f["b5_second_journeys"] = b5[1]["datastore"], b5[1]["declared_tier"], b5[1]["journeys_proven"]
    b7 = rows("B7")[0]
    f.update(cache_incidents=b7["incidents"], cache_minutes=b7["total_minutes"], cache_customers=b7["customers_impacted"],
             cache_teams=b7["teams_assigned"], cache_to_owner=b7["assigned_to_owner"])
    f["cache_hours"] = round(b7["total_minutes"] / 60)
    b7b = {r["routing"]: r for r in rows("B7b")}
    own, els = b7b["assigned to the owner"], b7b["assigned elsewhere"]
    f.update(route_own_n=own["incidents"], route_own_avg=int(own["avg_minutes"]), route_own_re=own["avg_reassignments"],
             route_els_n=els["incidents"], route_els_avg=int(els["avg_minutes"]), route_els_re=els["avg_reassignments"])
    f["route_factor"] = round(els["avg_minutes"] / own["avg_minutes"], 1)
    f["route_total"] = own["incidents"] + els["incidents"]
    b7c = rows("B7c")
    f["hist_degraded"] = sum(1 for r in b7c if r["impact"] == "degraded")
    f["hist_outages"] = sum(1 for r in b7c if r["impact"] == "outage")
    f["outage_hit_rates"] = " and ".join(sorted(
        (re.search(r"hit rate fell to (\d+)%", r["detail"]).group(1) + "%" for r in b7c if r["impact"] == "outage"),
        key=lambda x: -int(x[:-1])))

    # Part 5: act
    b8 = rows("B8")
    f["changes_window"], f["changes_in_radius"] = len(b8), sum(1 for r in b8 if r["in_radius"] == "yes")
    f["change_closest"], f["change_closest_what"], f["change_closest_at"] = b8[0]["change"], b8[0]["what"], b8[0]["deployed_at"][-5:]
    f["change_closest_review"] = b8[0]["had_risk_review"]
    b4 = rows("B4")
    f["radius_teams_active"] = sum(1 for r in b4 if r["status"] == "active")
    f["radius_teams_disbanded"] = sum(1 for r in b4 if r["status"] == "disbanded")
    f["radius_top_team"], f["radius_top_team_n"] = b4[0]["team"], b4[0]["owns_in_radius"]
    b4b = rows("B4b")
    f["unpageable"] = len(b4b)
    f["unpageable_names"] = " and ".join(f"`{r['component']}`" for r in b4b)
    b9 = {r["coverage"]: r["components"] for r in rows("B9")}
    f.update(rb_none=b9["no runbook"], rb_stale=b9["runbook (stale)"], rb_current=b9["runbook (current)"])
    f["radius_components"] = sum(b9.values())

    # PageRank
    b10 = rows("B10")
    f["pr_top"], f["pr_top_score"] = b10[0]["component"], b10[0]["pagerank"]
    f["pr_second"] = b10[1]["component"]
    f["pr_cache_rank"] = [r["component"] for r in b10].index("profile-cache") + 1

    # The loader and the guide
    load_text = (EXPECTED.parents[1] / "graph/load.cypher").read_text()
    f["load_statements"] = len(re.findall(r";\s*$", load_text, re.M))
    f["load_kb"] = round(len(load_text.encode()) / 1000)
    import generate as G
    f["load_chunk"] = G.CHUNK
    guide = (EXPECTED.parents[1] / "build/lab-guide.template.md").read_text()
    f["stretch_count"] = len(re.findall(r"^### S\d+:", guide, re.M))
    core = guide.split("## Stretch challenges")[0]
    f["ladder_queries"] = len(set(re.findall(r"\{\{query (\w+)\}\}", core)) - {"R0"})

    # The easter egg
    b11 = rows("B11b")[0]
    f.update(egg_cert=b11["certificate"], egg_days=b11["expires_in_days"], egg_owner=b11["owner"], egg_renews=b11["renews_itself"],
             egg_services=b11["services"], egg_teams=b11["teams"], egg_journeys=b11["journeys"],
             egg_rotated=b11["last_rotated"], egg_last_outage=b11["last_expiry_outage"],
             egg_outage_hours=round(b11["last_outage_minutes"] / 60))
    egg_rows = rows("B11b")
    f["egg_rows"] = len(egg_rows)
    f["egg_decoys"] = len(egg_rows) - 1
    decoys = [r for r in egg_rows if r["certificate"] != f["egg_cert"]]
    f["egg_decoys_renewing"] = sum(1 for r in decoys if r["renews_itself"] == "yes")
    sso = [r for r in decoys if r["certificate"] == "sso.idp.signing"][0]
    f["egg_decoy_name"], f["egg_decoy_journeys"] = sso["certificate"], sso["journeys"]
    f["labels_shown"] = len(rows("B11a"))
    return f


def check(f: dict, b1b: list[dict]) -> None:
    """The prose makes structural claims, not just numeric ones. Refuse to render
    documents if the data stops supporting any of them."""
    role = {r["component"]: r["role"] for r in b1b}
    claims = {
        "Tap to pay survives the worst case": f["tap_status"] == "up",
        "profile-cache is the likely cause": f["cause_name"] == "profile-cache" and f["storm_cause"] == 1,
        "campaign-svc and agent-desktop-svc are surprise symptoms":
            role.get("campaign-svc") == "symptom" and role.get("agent-desktop-svc") == "symptom",
        "marking the link soft equals the day before CHG-1873": f["journeys_if_soft"] == f["replay_journeys_before"],
        "marking the link hard proves every worst-case journey": f["journeys_if_hard_proven"] == f["journeys_worst"],
        "the entitlements link is the top unclassified link": f["link"] == "entitlements-svc -> customer-profile-svc",
        "the link came from CHG-1873 with no risk review": f["link_change"] == "CHG-1873" and f["link_reviewed"] is False,
        "no cache incident went to the owner": f["cache_to_owner"] == 0,
        "profile-cache leads the mismatches": f["b5_top"] == "profile-cache",
        "CHG-2301 is the closest change, unreviewed": f["change_closest"] == "CHG-2301" and f["change_closest_review"] is False,
        "customer-profile-svc has the top PageRank": f["pr_top"] == "customer-profile-svc",
        "the wildcard certificate is the easter egg": f["egg_cert"] == "wildcard.internal.bank" and f["egg_renews"] == "NO",
        "routing elsewhere is slower": f["route_els_avg"] > f["route_own_avg"],
        "the wildcard was rotated by hand the day it last expired": f["egg_rotated"] == f["egg_last_outage"],
        "the wildcard's owner was disbanded": "disbanded" in f["egg_owner"],
        "Tap to pay's service is under the wildcard (its card-auth-svc)": "card-auth-svc" in E.WILDCARD["used_by"],
        "exactly one decoy is manual, the rest renew": f["egg_decoys"] - f["egg_decoys_renewing"] == 1,
        "the loudest decoy renews itself": any(r["certificate"] == "sso.idp.signing" and r["renews_itself"] == "yes"
                                              for r in rows("B11b")),
    }
    bad = [k for k, ok in claims.items() if not ok]
    if bad:
        raise SystemExit("documents refuse to render; the data no longer supports: " + "; ".join(bad))


FACTS = build()
check(FACTS, rows("B1b"))

if __name__ == "__main__":
    w = max(len(k) for k in FACTS)
    for k, v in FACTS.items():
        print(f"{k:<{w}}  {v}")
