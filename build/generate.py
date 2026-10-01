"""Generate graph/load.cypher: the 3 a.m. Blast Radius graph.

    python3 build/generate.py                 # writes graph/load.cypher
    python3 build/generate.py --scores FILE   # also embeds GDS scores (see build.sh)

Everything is fictional and reproducible: the same seed gives the same file.
build/estate.py holds the hand-written facts (the cast, the planted story, the
easter egg). This file adds the seeded background a real estate has: hundreds of
unrelated incidents and changes, runbooks, certificates, observability edges.

The mess is deliberate, and each kind has a reason to exist in a query:

  critical = null        a dependency nobody ever classified as hard or soft
  source = observed      seen in traces, never declared in the service catalog
  active = false         declared, but no traffic seen for months
  disbanded teams        still own components; incidents are still assigned to them
  no owner / no tier     datastores nobody claimed, or ever rated
  mutual dependencies    A -> B -> A, which every graph of real services has
  lookalike services     two notification services, two auth gateways
  incomplete incidents   some with no recorded root cause, some with no customer count
  stale runbooks         reviewed more than a year ago
  alerts that are noise  or duplicated, in the middle of a real storm

Derived edge flags (written as properties so queries stay readable):
  confirmed = active AND critical = true            (known to be a hard dependency)
  hard      = active AND critical is not false      (assume the worst until proven soft)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
from pathlib import Path

import estate as E

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "graph/load.cypher"
UTC = dt.timezone.utc
CHUNK = 150  # rows per UNWIND statement: keeps every statement small and the file loadable anywhere
rng = random.Random(20260930)


# ==========================================================================
# Parsing the estate
# ==========================================================================
def parse_services():
    out = []
    for line in E.SERVICES_TEXT.strip().splitlines():
        team, items = [x.strip() for x in line.split("|", 1)]
        for item in items.split(","):
            name, tier = item.split()
            deprecated = tier.endswith("!")
            tier = tier.rstrip("!")
            out.append(dict(name=name, team=team, tier=None if tier == "?" else int(tier),
                            lifecycle="deprecated" if deprecated else "active"))
    return out


def parse_datastores():
    out = []
    for line in E.DATASTORES_TEXT.strip().splitlines():
        team, items = [x.strip() for x in line.split("|", 1)]
        for item in items.split(","):
            name, kind, tier = item.split()
            out.append(dict(name=name, team=None if team == "(nobody)" else team, kind=kind,
                            tier=None if tier == "?" else int(tier)))
    return out


def edge(src, dst, flag, opts):
    r = random.Random(f"{src}>{dst}")
    first = dt.date(2023, 1, 1) + dt.timedelta(days=r.randint(0, 850))
    d = dict(src=src, dst=dst, critical={"T": True, "F": False, "?": None}[flag],
             source="observed" if "observed" in opts else "both", active="inactive" not in opts,
             first_seen=first.isoformat(), introduced_by=None)
    for o in opts:
        if o.startswith("first="):
            d["first_seen"] = o[6:]
        if o.startswith("chg="):
            d["introduced_by"] = o[4:]
    d["last_seen"] = "2026-09-28" if d["active"] else "2025-04-12"
    d["confirmed"] = d["active"] and d["critical"] is True
    d["hard"] = d["active"] and d["critical"] is not False
    return d


def parse_edges(service_names):
    out, seen = [], set()

    def add(src, dst, flag, opts):
        assert (src, dst) not in seen, f"duplicate dependency {src} -> {dst}"
        seen.add((src, dst))
        out.append(edge(src, dst, flag, opts))

    for line in E.EDGES_CORE.strip().splitlines():
        p = line.split()
        add(p[0], p[2], p[3], p[4:])
    for line in E.EDGES_ESTATE.strip().splitlines():
        if not line.strip():
            continue
        src, rest = line.split(":", 1)
        for part in rest.split(";"):
            p = part.split()
            add(src.strip(), p[0], p[1], p[2:])
    for name in service_names:
        if name not in E.NO_TRACING and (name, "tracing-collector") not in seen:
            add(name, "tracing-collector", "F", ["observed"])
    return out


# ==========================================================================
# Seeded background
# ==========================================================================
def lognorm(median: float, sigma: float) -> float:
    return math.exp(math.log(median) + sigma * rng.gauss(0, 1))


def when(lo: dt.datetime, hi: dt.datetime) -> dt.datetime:
    return lo + dt.timedelta(minutes=rng.randint(0, int((hi - lo).total_seconds() // 60)))


def background_incidents(edges, owner_of, tier_of, services, disbanded):
    """Mostly routed to the owner and fixed fast; about one in five is routed
    elsewhere, bounces, and takes ~3x as long: an effect we PLANT. A few are
    incomplete, as real ones are: no recorded root cause, no customer count."""
    dependents: dict[str, list[str]] = {}
    for e in edges:
        if e["active"] and e["dst"] != "tracing-collector":
            dependents.setdefault(e["dst"], []).append(e["src"])
    active_teams = [t[0] for t in E.TEAMS if t[2] == "active"]
    roots = [n for n in tier_of if n not in ("profile-cache", "tracing-collector")]
    weights = [{1: 3, 2: 2, 3: 1, None: 1}[tier_of[n]] for n in roots]
    details = ["", "", "", "", "Rolled back", "Failed over", "Restarted", "Capacity increased", "Config reverted", "Hotfix deployed"]
    out = []
    for _ in range(220):
        root = rng.choices(roots, weights)[0]
        owner = owner_of.get(root)
        routed_right = owner is not None and owner not in disbanded and rng.random() < 0.80
        team = owner if routed_right else rng.choice([t for t in active_teams if t != owner])
        mins = lognorm(48 if routed_right else 165, 0.45)
        impact = "outage" if rng.random() < 0.15 else "degraded"
        tier = tier_of[root] or 2
        cust = int(lognorm({1: 60_000, 2: 12_000, 3: 1_500}[tier], 0.8) * (2 if impact == "outage" else 1))
        deps = [d for d in dependents.get(root, []) if d in services]
        affected = ([root] if root in services else []) + (rng.sample(deps, min(len(deps), rng.randint(1, 2))) if deps else [])
        kind = "service" if root in services else "datastore"
        title = rng.choice({
            ("service", "degraded"): ["elevated error rate", "latency above SLO", "intermittent timeouts", "queue backlog"],
            ("service", "outage"): ["partial outage", "failing health checks"],
            ("datastore", "degraded"): ["replication lag", "slow queries", "disk pressure"],
            ("datastore", "outage"): ["failover event", "node unavailable"],
        }[(kind, impact)])
        out.append(dict(
            id="", at=when(dt.datetime(2025, 1, 15, tzinfo=UTC), dt.datetime(2026, 9, 20, tzinfo=UTC)).strftime("%Y-%m-%dT%H:%M:00Z"),
            sev=1 if (impact == "outage" and tier == 1) else (2 if impact == "outage" or tier == 1 else 3),
            title=f"{root}: {title}", root=root, affected=affected, team=team, minutes=max(8, int(mins)),
            impact=impact, customers=cust, reassignments=0 if routed_right and rng.random() < 0.9 else rng.randint(1, 3),
            detail=rng.choice(details)))
    # Incomplete records, picked at random after the fact.
    for inc in rng.sample(out, 16):
        inc["root"] = None
    for inc in rng.sample(out, 24):
        inc["customers"] = None
    return out


def background_changes(services_active, extra_planted_ids):
    templates = [
        lambda: (f"Deploy v{rng.randint(1, 9)}.{rng.randint(0, 20)}.{rng.randint(0, 9)}", True),
        lambda: (f"Config: {rng.choice(['timeout', 'pool size', 'retry budget', 'log level', 'rate limit', 'batch size'])} change", rng.random() < 0.6),
        lambda: (f"Dependency upgrade: {rng.choice(['http client', 'json parser', 'tls library', 'metrics agent', 'orm'])}", True),
        lambda: (f"Schema migration {rng.randint(100, 999)}", True),
        lambda: (f"Feature flag rollout {rng.choice([5, 10, 25, 50, 100])}%", rng.random() < 0.8),
    ]
    raw = []
    for _ in range(440):
        w = when(dt.datetime(2025, 1, 6, tzinfo=UTC), dt.datetime(2026, 9, 28, 3, 0, tzinfo=UTC))
        what, review = rng.choice(templates)()
        raw.append((w, rng.choice(services_active), what, review))
    # A handful of ordinary overnight changes, none near the cache.
    clear = [s for s in services_active if s not in E.KEEP_CLEAR_OF]
    tonight = []
    for _ in range(6):
        w = when(dt.datetime(2026, 9, 29, 3, 30, tzinfo=UTC), dt.datetime(2026, 9, 30, 2, 50, tzinfo=UTC))
        what, review = rng.choice(templates)()
        tonight.append((w, rng.choice(clear), what, review))
    out, n = [], 1000
    for w, svc, what, review in sorted(raw):
        n += 1
        while f"CHG-{n}" in extra_planted_ids:
            n += 1
        out.append(dict(id=f"CHG-{n}", at=w.strftime("%Y-%m-%dT%H:%M:00Z"), svc=svc, what=what, review=review))
    for i, (w, svc, what, review) in enumerate(sorted(tonight), start=7):
        out.append(dict(id=f"CHG-23{i:02d}", at=w.strftime("%Y-%m-%dT%H:%M:00Z"), svc=svc, what=what, review=review))
    return out


def generated_runbooks(components, tier_of, covered):
    out = []
    for name in sorted(components):
        if name in E.NEVER_COVERED or name in covered:
            continue
        p = {1: 0.50, 2: 0.30, 3: 0.12, None: 0.05}[tier_of[name]]
        if rng.random() < p:
            reviewed = dt.date(2023, 10, 1) + dt.timedelta(days=rng.randint(0, 1050))
            out.append((f"RB-{name}", [name], reviewed.isoformat()))
    return out


def certificates(service_names, owner_of, tier_of):
    """The easter egg, its decoys, and ordinary background certificates."""
    certs = []
    w = E.WILDCARD
    certs.append(dict(name=w["name"], expires_on=w["expires_on"], last_rotated=w["last_rotated"],
                      auto_renew=w["auto_renew"], issuer=w["issuer"], team=w["team"], used_by=w["used_by"]))
    for name, exp, auto, team, used in E.DECOY_CERTS:
        rot = (dt.date.fromisoformat(exp) - dt.timedelta(days=365)).isoformat()
        certs.append(dict(name=name, expires_on=exp, last_rotated=rot, auto_renew=auto, issuer="Public CA",
                          team=team, used_by=used))
    pool = [s for s in service_names if tier_of[s] in (1, 2) and s not in set(w["used_by"][:0])]
    for svc in rng.sample(pool, 29):
        exp = dt.date(2026, 11, 20) + dt.timedelta(days=rng.randint(0, 520))
        r = rng.random()
        auto = None if r < 0.12 else (False if r < 0.20 else True)
        if auto is False:
            exp = max(exp, dt.date(2027, 3, 1))   # a manual cert that is NOT about to expire: not a decoy
        others = rng.sample([s for s in service_names if s != svc], rng.randint(0, 2))
        certs.append(dict(name=f"mtls.{svc}", expires_on=exp.isoformat(),
                          last_rotated=(exp - dt.timedelta(days=rng.randint(300, 400))).isoformat(),
                          auto_renew=auto, issuer=rng.choice(["Internal CA", "Internal CA", "Public CA"]),
                          team=owner_of[svc], used_by=[svc] + others))
    return certs


# ==========================================================================
# Cypher output
# ==========================================================================
def cy(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(cy(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {cy(x)}" for k, x in v.items()) + "}"
    raise TypeError(type(v))


def unwind(comment: str, rows: list[dict], body: str) -> list[str]:
    """One statement per CHUNK rows, so every statement stays small."""
    out = []
    n = max(1, math.ceil(len(rows) / CHUNK))
    for i in range(n):
        part = rows[i * CHUNK:(i + 1) * CHUNK]
        label = f"// ---- {comment}" + (f" (batch {i + 1} of {n})" if n > 1 else "") + " ----\n"
        out.append(label + "UNWIND [\n  " + ",\n  ".join(cy(r) for r in part) + "\n] AS row\n" + body)
    return out


HEADER = """// ===========================================================================
//  3 a.m. Blast Radius: the graph                       GENERATED, do not edit
//
//  Regenerate with:  python3 build/generate.py        (seeded: same output every time)
//
//  A fully fictional service-dependency graph for a large retail bank. Nothing
//  here describes any real institution's architecture. Every name, team,
//  incident, change and customer count is invented.
//
//    {summary}
//
//  Pure Cypher: no APOC, no GDS, no files. Idempotent: every write is a MERGE on
//  a unique key, so re-running changes nothing. Statements are batched
//  ({chunk} rows each), so none is large.
//
//    cypher-shell -d <database> -f graph/load.cypher
//
//  "Tonight" is 2026-09-30T03:07:00Z. The queries use that fixed time, never now().
//
//  The data is deliberately messy: see build/generate.py for the list, and
//  graph/MODEL.md for what each kind of mess is for.
// ===========================================================================

"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", type=Path, help="JSON {component: {pagerank, cluster_id}} from GDS")
    args = ap.parse_args()
    scores = json.loads(args.scores.read_text()) if args.scores and args.scores.exists() else {}

    svc_rows, ds_rows = parse_services(), parse_datastores()
    services = {s["name"] for s in svc_rows}
    tier_of = {c["name"]: c["tier"] for c in svc_rows + ds_rows}
    owner_of = {c["name"]: c["team"] for c in svc_rows + ds_rows if c["team"]}
    names = set(tier_of)
    assert len(svc_rows) + len(ds_rows) == len(names), "duplicate component name"
    team_names = {t[0] for t in E.TEAMS}
    assert set(owner_of.values()) <= team_names, set(owner_of.values()) - team_names
    disbanded = {t[0] for t in E.TEAMS if t[2] == "disbanded"}

    edges = parse_edges([s["name"] for s in svc_rows])
    for e in edges:
        assert e["src"] in names and e["dst"] in names, e
    for j in E.JOURNEYS:
        assert j[2] in team_names and all(s in services for s in j[3]), j
    for a in E.ALERTS:
        assert a[2] in names, a

    # Incidents
    incidents = [dict(i) for i in E.PLANTED_INCIDENTS]
    incidents += background_incidents(edges, owner_of, tier_of, services, disbanded)
    incidents.sort(key=lambda i: i["at"])
    n = 0
    for inc in incidents:
        if not inc["id"]:
            n += 1
            inc["id"] = f"INC-{2000 + n}"
    for inc in incidents:
        assert inc["team"] in team_names and all(a in services for a in inc["affected"]), inc
        assert inc["root"] is None or inc["root"] in names, inc

    # Changes
    planted_ids = {c[0] for c in E.PLANTED_CHANGES}
    changes = [dict(id=c[0], at=c[1], svc=c[2], what=c[3], review=c[4]) for c in E.PLANTED_CHANGES]
    changes += background_changes([s["name"] for s in svc_rows if s["lifecycle"] == "active"], planted_ids)
    changes.sort(key=lambda c: c["at"])
    assert len({c["id"] for c in changes}) == len(changes), "duplicate change id"
    for c in changes:
        assert c["svc"] in services, c

    # Runbooks
    covered = {c for _, cs, _ in E.RUNBOOKS for c in cs}
    runbooks = list(E.RUNBOOKS) + generated_runbooks(names, tier_of, covered)

    # Certificates (the easter egg lives here)
    certs = certificates([s["name"] for s in svc_rows], owner_of, tier_of)
    for c in certs:
        assert c["team"] in team_names and all(u in services for u in c["used_by"]), c
    egg = E.EGG_INCIDENT
    assert all(a in services for a in egg["affected"]) and set(egg["teams"]) <= team_names

    comp = lambda nm: {k: scores[nm][k] for k in ("pagerank", "cluster_id")} if nm in scores else {}
    cert_pairs = [dict(cert=c["name"], svc=u) for c in certs for u in dict.fromkeys(c["used_by"])]

    sections = [
        *[f"CREATE CONSTRAINT {n}_key IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE;"
          for n, label, key in [("component", "Component", "name"), ("team", "Team", "name"), ("journey", "Journey", "name"),
                                ("incident", "Incident", "id"), ("change", "Change", "id"), ("runbook", "Runbook", "id"),
                                ("alert", "Alert", "id"), ("certificate", "Certificate", "name")]],
        "CREATE INDEX change_time IF NOT EXISTS FOR (n:Change) ON (n.deployed_at);",
        "CREATE INDEX incident_time IF NOT EXISTS FOR (n:Incident) ON (n.started_at);",
        *unwind("teams", [dict(name=n_, pager=p, status=s, disbanded_on=d) for n_, p, s, d in E.TEAMS],
                "MERGE (t:Team {name: row.name})\nSET t.pager = row.pager, t.status = row.status,\n"
                "    t.disbanded_on = CASE WHEN row.disbanded_on IS NULL THEN null ELSE date(row.disbanded_on) END;"),
        *unwind("services (tier 1 = customer-facing critical ... 3 = can wait; null = never rated)",
                [dict(name=s["name"], tier=s["tier"], lifecycle=s["lifecycle"], **comp(s["name"])) for s in svc_rows],
                "MERGE (c:Component {name: row.name})\nSET c:Service, c.tier = row.tier, c.lifecycle = row.lifecycle,\n"
                "    c.pagerank = row.pagerank, c.cluster_id = row.cluster_id;"),
        *unwind("datastores (tier = the tier they were DECLARED to have)",
                [dict(name=d["name"], kind=d["kind"], tier=d["tier"], **comp(d["name"])) for d in ds_rows],
                "MERGE (c:Component {name: row.name})\nSET c:Datastore, c.kind = row.kind, c.tier = row.tier,\n"
                "    c.pagerank = row.pagerank, c.cluster_id = row.cluster_id;"),
        *unwind("ownership (some datastores have no owner: nobody claimed them)",
                [dict(name=nm, team=t) for nm, t in owner_of.items()],
                "MATCH (c:Component {name: row.name}), (t:Team {name: row.team})\nMERGE (t)-[:OWNS]->(c);"),
        *unwind("dependencies. critical: true hard, false soft, null never classified. source: both | observed (undeclared)",
                edges,
                "MATCH (a:Component {name: row.src}), (b:Component {name: row.dst})\nMERGE (a)-[r:DEPENDS_ON]->(b)\n"
                "SET r.critical = row.critical, r.source = row.source, r.active = row.active,\n"
                "    r.first_seen = date(row.first_seen), r.last_seen = date(row.last_seen),\n"
                "    r.introduced_by = row.introduced_by, r.confirmed = row.confirmed, r.hard = row.hard;"),
        *unwind("customer journeys (attempt counts are invented)",
                [dict(name=j[0], daily=j[1], team=j[2], requires=j[3], h03=round(j[1] * j[4][0]),
                      h07=round(j[1] * j[4][1]), h12=round(j[1] * j[4][2])) for j in E.JOURNEYS],
                "MERGE (j:Journey {name: row.name})\nSET j.customers_per_day = row.daily, j.per_hour_0300 = row.h03,\n"
                "    j.per_hour_0700 = row.h07, j.per_hour_1200 = row.h12\n"
                "WITH j, row\nMATCH (t:Team {name: row.team})\nMERGE (j)-[:OWNED_BY]->(t)\nWITH j, row\nUNWIND row.requires AS svc\n"
                "MATCH (s:Service {name: svc})\nMERGE (j)-[:REQUIRES]->(s);"),
        *unwind("incident history: 18 months",
                [dict(id=i["id"], at=i["at"], sev=i["sev"], title=i["title"], team=i["team"], minutes=i["minutes"],
                      impact=i["impact"], customers=i["customers"], reassignments=i["reassignments"], detail=i["detail"])
                 for i in incidents],
                "MERGE (i:Incident {id: row.id})\nSET i.severity = row.sev, i.started_at = datetime(row.at), i.title = row.title,\n"
                "    i.duration_minutes = row.minutes, i.impact = row.impact, i.customers_impacted = row.customers,\n"
                "    i.reassignments = row.reassignments, i.detail = row.detail\n"
                "WITH i, row\nMATCH (t:Team {name: row.team})\nMERGE (i)-[:ASSIGNED_TO]->(t);"),
        *unwind("incident root causes (some incidents never had one recorded)",
                [dict(id=i["id"], root=i["root"]) for i in incidents if i["root"]],
                "MATCH (i:Incident {id: row.id}), (c:Component {name: row.root})\nMERGE (i)-[:ROOT_CAUSE]->(c);"),
        *unwind("incident impact: which services each one hit",
                [dict(id=i["id"], svc=s) for i in incidents for s in i["affected"]],
                "MATCH (i:Incident {id: row.id}), (s:Service {name: row.svc})\nMERGE (i)-[:AFFECTED]->(s);"),
        *unwind("changes (deploys, config, flags)",
                [dict(id=c["id"], at=c["at"], svc=c["svc"], what=c["what"], review=c["review"]) for c in changes],
                "MERGE (c:Change {id: row.id})\nSET c.deployed_at = datetime(row.at), c.what = row.what, c.risk_review = row.review\n"
                "WITH c, row\nMATCH (s:Service {name: row.svc})\nMERGE (c)-[:DEPLOYED_TO]->(s);"),
        *unwind("runbooks (stale = not reviewed in 12 months)",
                [dict(id=i, reviewed=r) for i, _, r in runbooks],
                "MERGE (r:Runbook {id: row.id})\nSET r.last_reviewed = date(row.reviewed),\n"
                "    r.stale = date(row.reviewed) < date('2025-09-30');"),
        *unwind("what each runbook covers",
                [dict(id=i, comp=c) for i, cs, _ in runbooks for c in cs],
                "MATCH (r:Runbook {id: row.id}), (c:Component {name: row.comp})\nMERGE (r)-[:COVERS]->(c);"),
        *unwind("certificates",
                [dict(name=c["name"], exp=c["expires_on"], rot=c["last_rotated"], auto=c["auto_renew"],
                      issuer=c["issuer"], team=c["team"]) for c in certs],
                "MERGE (c:Certificate {name: row.name})\nSET c.expires_on = date(row.exp), c.last_rotated = date(row.rot),\n"
                "    c.auto_renew = row.auto, c.issuer = row.issuer\n"
                "WITH c, row\nMATCH (t:Team {name: row.team})\nMERGE (t)-[:OWNS]->(c);"),
        *unwind("which services use which certificate",
                cert_pairs,
                "MATCH (c:Certificate {name: row.cert}), (s:Service {name: row.svc})\nMERGE (s)-[:USES_CERT]->(c);"),
        *unwind("the last time a certificate took the estate down",
                [dict(id=egg["id"], at=egg["at"], sev=egg["sev"], title=egg["title"], cert=egg["cert"],
                      minutes=egg["minutes"], impact=egg["impact"], customers=egg["customers"],
                      reassignments=egg["reassignments"], detail=egg["detail"], teams=egg["teams"], affected=egg["affected"])],
                "MERGE (i:Incident {id: row.id})\nSET i.severity = row.sev, i.started_at = datetime(row.at), i.title = row.title,\n"
                "    i.duration_minutes = row.minutes, i.impact = row.impact, i.customers_impacted = row.customers,\n"
                "    i.reassignments = row.reassignments, i.detail = row.detail\n"
                "WITH i, row\nMATCH (c:Certificate {name: row.cert})\nMERGE (i)-[:ROOT_CAUSE]->(c)\n"
                "WITH i, row\nUNWIND row.teams AS tn\nMATCH (t:Team {name: tn})\nMERGE (i)-[:ASSIGNED_TO]->(t)\n"
                "WITH DISTINCT i, row\nUNWIND row.affected AS sn\nMATCH (s:Service {name: sn})\nMERGE (i)-[:AFFECTED]->(s);"),
        *unwind("tonight's alert storm",
                [dict(id=i, at=f"2026-09-30T{t}:00Z", comp=c, summary=s) for i, t, c, s in E.ALERTS],
                "MERGE (a:Alert {id: row.id})\nSET a.fired_at = datetime(row.at), a.summary = row.summary\n"
                "WITH a, row\nMATCH (c:Component {name: row.comp})\nMERGE (a)-[:FIRED_ON]->(c);"),
        "// ---- summary ----\nMATCH (n) RETURN count(n) AS nodes, COUNT { ()-[]->() } AS relationships;",
    ]
    n_nodes = (len(E.TEAMS) + len(svc_rows) + len(ds_rows) + len(E.JOURNEYS) + len(incidents) + 1
               + len(changes) + len(runbooks) + len(certs) + len(E.ALERTS))
    summary = (f"{n_nodes} nodes: {len(svc_rows) + len(ds_rows)} components, {len(E.TEAMS)} teams, {len(E.JOURNEYS)} journeys, "
               f"{len(incidents) + 1} incidents, {len(changes)} changes, {len(runbooks)} runbooks, "
               f"{len(certs)} certificates, {len(E.ALERTS)} alerts. {len(edges)} dependencies.")
    OUT.write_text(HEADER.format(summary=summary, chunk=CHUNK) + "\n\n".join(sections) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e3:.0f} kB): {summary}"
          + (f" Scores for {len(scores)} components." if scores else ""))


if __name__ == "__main__":
    main()
