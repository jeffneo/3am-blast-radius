"""Check the blast-radius graph and queries on a clean Neo4j 5.26.

    python3 build/verify.py            # compare every query to build/expected/
    python3 build/verify.py --record   # (re)write build/expected/ after a deliberate change
    python3 build/verify.py --image neo4j:2026.08.1-enterprise   # same checks on the dev server version
    python3 build/verify.py --no-gds   # a plain server: skips the GDS statements (the core lab must not need them)

Starts a throwaway container (removed afterwards, with its volume; never touches
the compose stack) laid out like the JPMC sandbox: an attendee database
(lab-user01) and a NON-ADMIN user whose home database it is, who runs every
query without naming a database. Loads graph/load.cypher TWICE (the second load must change nothing: idempotency),
runs each statement in queries/demo-queries.cypher, the live GDS statements (queries/gds.cypher:
the plugin ships in the enterprise image and is switched on, unlicensed), the Bloom search
phrases (queries/bloom.cypher: each must return paths; the size of its picture is recorded)
and then queries/hands-on.cypher (which writes, and must restore the graph; live PageRank and
the blast-radius picture are re-run after the edit), and checks:

  * it succeeds and matches the recorded result
  * lab rules: no $params, every variable-length path bounded, no APOC
  * time per statement (flagged above 1 s)

Exits non-zero on any failure.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "neo4j:5.26-enterprise"
NAME = "br-verify"
PW = "verifyadmin"
DB, USER, USER_PW = "lab-user01", "user01", "user01-password"  # shaped like a JPMC attendee
EXPECTED = ROOT / "build/expected"
BANNER = re.compile(r"Thank you for installing Neo4j.*?if you require more time\.\s*", re.S)
# Write summaries ("Added 1 nodes, Set 1 properties" on 5.26, "Created 1 node, set 1
# property" on 2026.x). Their wording differs by server version and carries no result.
SUMMARY = re.compile(r"^(added|set|removed|deleted|created)\b.*\d.*$", re.I | re.M)
TIMING = re.compile(r"ready to start consuming query after (\d+) ms, results consumed after another (\d+) ms")
ID_RE = re.compile(r"^//\s*((?:B\d+[a-z]?)|(?:H\d+)|(?:R\d+)|(?:K\d+)|(?:G\d+)|(?:P\d+))\b")
PARAM_RE = re.compile(r"^//\s+param:\s+(\w+) = (.+?)\s*$")


def sh(*a: str, input: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(a, capture_output=True, text=True, input=input)


def cypher(query: str, fmt: str = "verbose", user: str = "neo4j", pw: str = PW,
           db: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["docker", "exec", "-i", NAME, "cypher-shell", "-u", user, "-p", pw, "--format", fmt]
    if db:
        cmd += ["-d", db]
    return sh(*cmd, input=query)


def as_attendee(query: str, fmt: str = "verbose") -> subprocess.CompletedProcess:
    """Run as the attendee: non-admin, no database named, so the HOME database is
    exercised. This is how the JPMC sandbox will connect them."""
    return cypher(query, fmt=fmt, user=USER, pw=USER_PW)


def statements(path: Path):
    cur, buf = None, []
    for line in path.read_text().splitlines():
        m = ID_RE.match(line.strip())
        if m:
            cur = m.group(1)
            continue
        if line.strip().startswith("//") or (not line.strip() and not buf):
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            if not cur:
                sys.exit("statement without an id comment:\n" + "\n".join(buf))
            yield cur, "\n".join(buf).strip()
            buf = []


def phrase_params(path: Path) -> dict[str, list[tuple[str, str]]]:
    """The `param: name = value` defaults written above each Bloom phrase."""
    out: dict[str, list[tuple[str, str]]] = {}
    cur = None
    for line in path.read_text().splitlines():
        m = ID_RE.match(line.strip())
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur and (pm := PARAM_RE.match(line.strip())):
            out[cur].append((pm.group(1), pm.group(2)))
    return out


def phrase_wrapper(stmt: str, params: list[tuple[str, str]]) -> str:
    """Run a Bloom phrase (which returns paths in a column `p`) and report the size of
    the picture it would draw: paths, distinct nodes, distinct relationships."""
    pre = "".join(f":param {k} => '{v}'\n" for k, v in params)
    return pre + f"""CALL {{
{stmt.rstrip().rstrip(';')}
}}
WITH collect(p) AS ps
RETURN size(ps) AS paths,
       size(reduce(a = [], x IN ps | a + [n IN nodes(x) WHERE NOT n IN a])) AS nodes,
       size(reduce(a = [], x IN ps | a + [r IN relationships(x) WHERE NOT r IN a])) AS relationships;"""


def lint(stmt: str, kind: str = "lab") -> list[str]:
    """kind: 'lab' (the core: no $params, no GDS), 'gds' (live GDS, no $params) or
    'bloom' (search phrases: $params are the point, and each must return paths as p)."""
    body = re.sub(r"'[^']*'", "''", stmt)
    out = []
    if "$" in body and kind != "bloom":
        out.append("uses a $param")
    if kind == "lab" and "gds." in body:
        out.append("uses GDS (the core lab must work without it)")
    if kind == "bloom" and not re.search(r"\bRETURN p;$", body.strip()):
        out.append("a Bloom phrase must end with RETURN p;")
    for rel in re.findall(r"\[[^\]]*\*[^\]]*\]", body):
        if not re.search(r"\*\d*\.\.\d+", rel):
            out.append(f"unbounded path {rel}")
    if "apoc." in body:
        out.append("uses APOC")
    if "//" in body:
        out.append("has a // comment (copying from a PDF can lose line breaks, and a comment would swallow the rest)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--image", default=IMAGE, help="Neo4j image to test on (default: the 5.26 lab target)")
    ap.add_argument("--no-gds", action="store_true", help="plain server without the GDS plugin: skips the GDS statements")
    args = ap.parse_args()
    gds = not args.no_gds
    if args.record and not gds:
        sys.exit("--record needs GDS (the recorded results include the GDS statements)")

    sh("docker", "rm", "-fv", NAME)
    # GDS ships inside the enterprise image; the plugin is switched on, unlicensed (the
    # conservative case: we do not know which edition the sandbox has).
    plugin = (["-e", 'NEO4J_PLUGINS=["graph-data-science"]', "-e", "NEO4J_dbms_security_procedures_unrestricted=gds.*",
               "-e", "NEO4J_dbms_security_procedures_allowlist=gds.*"] if gds else [])
    sh("docker", "run", "-d", "--name", NAME, "-e", f"NEO4J_AUTH=neo4j/{PW}",
       "-e", "NEO4J_ACCEPT_LICENSE_AGREEMENT=eval", "-e", "NEO4J_server_memory_heap_max__size=512m",
       "-e", "NEO4J_server_memory_pagecache_size=128m", *plugin, args.image)
    failures, rows = 0, []
    try:
        for _ in range(60):
            if cypher("RETURN 1", "plain").returncode == 0:
                break
            time.sleep(3)
        else:
            sys.exit("Neo4j did not start")

        setup = f"""
CREATE DATABASE `{DB}` IF NOT EXISTS WAIT;
CREATE USER {USER} IF NOT EXISTS SET PASSWORD '{USER_PW}' CHANGE NOT REQUIRED SET HOME DATABASE `{DB}`;
CREATE ROLE {USER}_owner IF NOT EXISTS;
GRANT ALL ON DATABASE `{DB}` TO {USER}_owner;
GRANT ALL GRAPH PRIVILEGES ON GRAPH `{DB}` TO {USER}_owner;
GRANT ROLE {USER}_owner TO {USER};
"""
        r = cypher(setup, "plain", db="system")
        if r.returncode:
            sys.exit("attendee setup failed:\n" + r.stderr)

        load = (ROOT / "graph/load.cypher").read_text()
        counts = []
        for _ in range(2):
            r = cypher(load, "plain", db=DB)
            if r.returncode:
                sys.exit("load failed:\n" + r.stderr)
            counts.append(r.stdout.strip().splitlines()[-1])
        idem = counts[0] == counts[1]
        if args.record:   # the load summary feeds the documents' totals
            (EXPECTED / "LOAD.txt").parent.mkdir(parents=True, exist_ok=True)
            nodes, rels = [x.strip() for x in counts[0].split(",")]
            load_txt = f"nodes={nodes}\nrelationships={rels}\n"
        else:
            load_txt = None
        print(f"loaded: {counts[0]}; second load: {counts[1]} -> idempotent: {idem}")
        failures += not idem

        EXPECTED.mkdir(parents=True, exist_ok=True)
        if args.record:  # drop results for queries that no longer exist
            for old in EXPECTED.glob("*.txt"):
                old.unlink()
            (EXPECTED / "LOAD.txt").write_text(load_txt)
        results: dict[str, str] = {}

        def check(sid: str, stmt: str, compare_as: str | None = None, kind: str = "lab",
                  compare: bool = True, send: str | None = None) -> None:
            """Run one statement and compare it to its recorded result. `send` is what is
            actually run when that differs from the statement linted (Bloom phrases are
            wrapped to measure them). compare=False checks only that it runs."""
            nonlocal failures
            problems = lint(stmt, kind)
            r = as_attendee(send or stmt)
            m = TIMING.search(r.stdout)
            ms = int(m[1]) + int(m[2]) if m else None
            result = re.sub(r"\n{3,}", "\n\n", SUMMARY.sub("", BANNER.sub("", TIMING.sub("", r.stdout)))).strip() + "\n"
            results[sid] = result
            exp = EXPECTED / f"{compare_as or sid}.txt"
            status = "ok"
            if r.returncode:
                status = "ERROR"
                problems.append(r.stderr.strip().splitlines()[0])
            elif not compare:
                pass
            elif args.record and compare_as is None:
                exp.write_text(result)
            elif not exp.exists():
                status = "NO EXPECTED"
            elif exp.read_text() != result:
                status = "CHANGED"
            if problems and status == "ok":
                status = "LINT"
            if ms and ms > 1000:
                problems.append(f"slow: {ms} ms")
            failures += status != "ok"
            rows.append((sid, status, ms, problems))

        # Read-only demo queries first, then the hands-on file, which WRITES and
        # must run in order. Afterwards B2d is run again: it must match its
        # original result, proving the hands-on reset really restores the graph.
        for sid, stmt in statements(ROOT / "queries/readiness.cypher"):
            check(sid, stmt)
        for sid, stmt in statements(ROOT / "queries/facts.cypher"):
            check(sid, stmt)
        for sid, stmt in statements(ROOT / "queries/demo-queries.cypher"):
            check(sid, stmt)
        # Live GDS (read-only: stream mode). Run as the attendee on the unlicensed plugin.
        gds_stmts = dict(statements(ROOT / "queries/gds.cypher")) if gds else {}
        for sid, stmt in gds_stmts.items():
            check(sid, stmt, kind="gds", compare=sid != "G0")     # G0 prints the plugin version: it differs by server
        if gds and args.record:
            ver = re.search(r'"([\d.]+)"', results["G0"])
            (EXPECTED / "GDS.txt").write_text(f"gds_version={ver.group(1) if ver else 'unknown'}\n")
        # Bloom search phrases: each must run, return paths, and keep the picture a readable size.
        bloom = ROOT / "queries/bloom.cypher"
        defaults = phrase_params(bloom)
        for sid, stmt in statements(bloom):
            check(sid, stmt, kind="bloom", send=phrase_wrapper(stmt, defaults[sid]))
        for sid, stmt in statements(ROOT / "queries/hands-on.cypher"):
            check(sid, stmt)
            if gds and sid in ("H2", "H4"):     # the algorithm must move with the decision
                check("G1s" if sid == "H2" else "G1h", gds_stmts["G1"], kind="gds")
            if sid == "H2":                     # ... and so must the Bloom picture
                p1 = dict(statements(bloom))["P1"]
                check("P1s", p1, kind="bloom", send=phrase_wrapper(p1, defaults["P1"]))
        if gds:                                  # restored: live PageRank must be back where it started
            check("G1^", gds_stmts["G1"], compare_as="G1", kind="gds")
        b2d = dict(statements(ROOT / "queries/demo-queries.cypher"))["B2d"]
        check("B2d*", b2d, compare_as="B2d")
        # The facilitator's last resort is to re-run the loader against one
        # attendee's database. Prove it, run as the attendee, for the two ways
        # a database goes wrong: an edit left half-done, and everything deleted.
        hands = dict(statements(ROOT / "queries/hands-on.cypher"))
        demo = dict(statements(ROOT / "queries/demo-queries.cypher"))
        as_attendee(hands["H2"])                                  # link left SOFT
        r = as_attendee(load, "plain")
        rows.append(("reload", "ok" if r.returncode == 0 else "ERROR", None, [r.stderr.strip()[:120]] if r.returncode else []))
        failures += r.returncode != 0
        check("H1~", hands["H1"], compare_as="H1")                # edited graph, reloaded
        as_attendee("MATCH (n) DETACH DELETE n;")                 # everything deleted
        r = as_attendee(load, "plain")
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        ok = r.returncode == 0 and last.replace(" ", "") == counts[0].replace(" ", "")
        rows.append(("reload+", "ok" if ok else "CHANGED", None, [] if ok else [f"after deleting everything, the loader gave {last!r}, not {counts[0]!r}"]))
        failures += not ok
        for sid in ("H1", "B2c", "B6c", "B11b"):
            check(f"{sid}+", hands.get(sid) or demo[sid], compare_as=sid)
        # H7 (restored) must equal H1 (before), compared on THIS run's output,
        # not on the recorded files.
        same = "H1" in results and results.get("H1") == results.get("H7")
        rows.append(("H1=H7", "ok" if same else "CHANGED", None, [] if same else ["restored scoreboard differs from the original"]))
        failures += not same
        # The attendee guide embeds these queries and results; it must match them.
        if not args.record:
            g = sh(sys.executable, str(ROOT / "build/make_guide.py"), "--check")
            ok = g.returncode == 0
            rows.append(("guide", "ok" if ok else "STALE", None, [] if ok else [(g.stderr or g.stdout).strip()]))
            failures += not ok
    finally:
        sh("docker", "rm", "-fv", NAME)

    print(f"\n{'id':5} {'status':12} {'ms':>5}  notes")
    for sid, status, ms, problems in rows:
        print(f"{sid:5} {status:12} {ms if ms is not None else '-':>5}  {'; '.join(problems)}")
    print(f"\n{len(rows)} statements, {failures} failed" + (" (recorded)" if args.record else ""))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
