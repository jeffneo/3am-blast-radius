#!/usr/bin/env bash
# Build the graph end to end, in the running compose stack (docker compose up -d).
#
#   1. generate graph/load.cypher                      (generate.py, no scores yet)
#   2. load it into the lab database
#   3. run GDS: PageRank + Louvain                     (algorithms.cypher)
#   4. export the scores                               (merge_scores.py)
#   5. regenerate graph/load.cypher WITH the scores    (the sandbox has no GDS)
#   6. reload, so the live database matches the file
#
# Safe to repeat: generation is seeded and every load is a MERGE.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; . ./.env; set +a
DB="${NEO4J_DATABASE:-blastradius}"
WORK="$ROOT/build/.work"; mkdir -p "$WORK"

# cypher-shell inside the server container; credentials come from its own NEO4J_AUTH.
cs() { docker exec -i br-neo4j sh -c 'cypher-shell -u "${NEO4J_AUTH%%/*}" -p "${NEO4J_AUTH#*/}" -d '"$DB"' "$@"' _ "$@"; }
load() { docker compose run --rm -T loader 2>&1 | tail -1; }

docker compose ps --status running --services | grep -qx neo4j || { echo "stack is not running: docker compose up -d" >&2; exit 1; }

echo "== 1. generate";  python3 build/generate.py
echo "== 1b. clear the lab database (names change between generations)"
cs --format plain "MATCH (n) DETACH DELETE n" >/dev/null
echo "== 2. load";      load
echo "== 3. GDS";       docker cp -q build/algorithms.cypher br-neo4j:/tmp/algorithms.cypher
cs --format plain -f /tmp/algorithms.cypher | grep -v '^graphName\|^"deps' || true
echo "== 4. export scores"
cs --format plain "MATCH (c:Component) RETURN c.name AS name, c.pagerank AS pagerank, c.cluster_id AS cluster_id ORDER BY name" > "$WORK/scores.csv"
python3 build/merge_scores.py "$WORK/scores.csv" "$WORK/scores.json"
echo "== 5. regenerate with scores"; python3 build/generate.py --scores "$WORK/scores.json"
echo "== 6. reload";    load
echo "== done: database '$DB' is up to date with graph/load.cypher"
