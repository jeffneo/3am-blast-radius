#!/usr/bin/env bash
# Rehearsal databases on the running dev stack, laid out like the JPMC sandbox.
#
#   build/rehearsal.sh up 4       # lab-user01..04, each loaded, each with its own login
#   build/rehearsal.sh down 4     # drop them again (users, roles, databases)
#
# Part 4 of the lab WRITES to the graph, so a team rehearsing together needs a
# database each. Everyone logs in to Neo4j Browser as userNN / rehearsal-userNN;
# that user's HOME database is lab-userNN and it is not an admin, so queries
# run without naming a database, exactly as for an attendee.
# These are throwaway credentials for the local dev stack only. Nothing here
# touches the lab database (blastradius) the stack is built around.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
action="${1:-}"; count="${2:-4}"
[[ "$action" == up || "$action" == down ]] || { echo "usage: $0 up|down [N]" >&2; exit 2; }
docker ps --format '{{.Names}}' | grep -qx br-neo4j || { echo "stack is not running: make up" >&2; exit 1; }

# cypher-shell inside the server container; credentials come from its own NEO4J_AUTH.
cs() { docker exec -i br-neo4j sh -c 'exec cypher-shell -u "${NEO4J_AUTH%%/*}" -p "${NEO4J_AUTH#*/}" --format plain -d "$1"' _ "$1"; }

for i in $(seq 1 "$count"); do
  n=$(printf '%02d' "$i"); db="lab-user$n"; user="user$n"
  if [[ "$action" == up ]]; then
    cs system >/dev/null <<EOF
CREATE DATABASE \`$db\` IF NOT EXISTS WAIT;
CREATE USER $user IF NOT EXISTS SET PASSWORD 'rehearsal-$user' CHANGE NOT REQUIRED SET HOME DATABASE \`$db\`;
CREATE ROLE ${user}_owner IF NOT EXISTS;
GRANT ALL ON DATABASE \`$db\` TO ${user}_owner;
GRANT ALL GRAPH PRIVILEGES ON GRAPH \`$db\` TO ${user}_owner;
GRANT ROLE ${user}_owner TO $user;
EOF
    out=$(cs "$db" < graph/load.cypher | tail -1)
    echo "$db  loaded ($out)   login: $user / rehearsal-$user"
  else
    cs system >/dev/null <<EOF
DROP USER $user IF EXISTS;
DROP ROLE ${user}_owner IF EXISTS;
DROP DATABASE \`$db\` IF EXISTS WAIT;
EOF
    echo "$db  dropped"
  fi
done
