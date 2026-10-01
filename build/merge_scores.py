"""Turn the raw GDS export into build/.work/scores.json.

Input: cypher-shell --format plain output with columns
    name, pagerank, cluster_id
Louvain ids are arbitrary, so they are renumbered by community size (1 = largest;
ties broken by smallest raw id) to make them stable and readable in Explore.
PageRank is rounded to 4 decimals so tiny floating-point noise cannot change the
generated file between runs.
"""

from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path


def main(src: Path, dst: Path) -> None:
    with open(src, newline="") as fh:
        rows = list(csv.DictReader(fh, skipinitialspace=True))
    sizes = collections.Counter(r["cluster_id"] for r in rows)
    rank = {c: i + 1 for i, c in enumerate(sorted(sizes, key=lambda c: (-sizes[c], int(c))))}
    scores = {r["name"].strip('"'): {"pagerank": round(float(r["pagerank"]), 4), "cluster_id": rank[r["cluster_id"]]}
              for r in rows}
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(scores, indent=1, sort_keys=True) + "\n")
    top = sorted(scores.items(), key=lambda kv: -kv[1]["pagerank"])[:5]
    print(f"{len(scores)} components, {len(sizes)} clusters; top pagerank: "
          + ", ".join(f"{n} {s['pagerank']}" for n, s in top))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
