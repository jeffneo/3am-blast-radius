# 3 a.m. Blast Radius

A fictional lab storyline for engineers: **a cache pages you at 3 a.m. {{f storm_alerts}} alerts, {{f storm_teams}} teams, and a dependency nobody ever classified. What actually breaks, for whom, and who do you wake up?**

Nothing in this folder describes a real institution. Every service, team, incident and customer number is invented.

```
3am_blast_radius/
├── README.md                    this file (generated)
├── STORYLINE.md                 the story in six scenes, the easter egg, what's planted (generated; SPOILERS)
├── LAB-GUIDE.pdf / .md          the attendee guide (generated). The PDF is for print and the zip
├── FACILITATOR-GUIDE.pdf / .md  for the people delivering it: run of show, the floor, the numbers (generated; SPOILERS)
├── docker-compose.yml           Neo4j (APOC + GDS Enterprise) + Enterprise Studio + a loader
├── Makefile                     shortcuts: make help
├── .env                         your configuration and credentials (secret, gitignored)
├── .env.example                 the same, with placeholders
├── gds.license  nes.license     signed licenses (secret, gitignored)
├── neo4j/
│   └── nes-setup.cypher         provisions Studio's asset database and service account
├── graph/
│   ├── MODEL.md                 schema, counts, the mess and what it's for (generated)
│   └── load.cypher              the whole graph. GENERATED, batched, pure Cypher
├── queries/
│   ├── readiness.cypher         the two-minute readiness check attendees run beforehand
│   ├── demo-queries.cypher      the read-only queries, B0 to B11, in story order
│   ├── hands-on.cypher          statements that CHANGE the graph: classify the link, watch the answer move
│   └── facts.cypher             key figures for the documents (not part of the lab)
└── build/
    ├── estate.py                the hand-written facts: teams, services, dependencies, the planted story, the easter egg
    ├── generate.py              turns the estate plus seeded background into graph/load.cypher
    ├── algorithms.cypher        GDS: PageRank and Louvain, run once
    ├── merge_scores.py          turns the GDS export into properties
    ├── build.sh                 generate, clear, load, score with GDS, regenerate, reload
    ├── rehearsal.sh             attendee-shaped databases on the dev stack, for rehearsing Part 4 together
    ├── verify.py                loads twice as a sandbox-shaped attendee, runs every query, checks the documents
    ├── facts.py                 every figure in the documents, computed from the tested results
    ├── make_guide.py            renders the generated documents from their templates
    ├── make_pdf.py              renders LAB-GUIDE.pdf and FACILITATOR-GUIDE.pdf (headless Chrome)
    ├── lab-guide.template.md    the guide's text
    ├── docs/                    the templates for STORYLINE, FACILITATOR, README and MODEL
    └── expected/                recorded results, one file per query
```

## Run it

You need Docker. The licenses (`gds.license`, `nes.license`) sit in this folder.

```bash
make up        # Neo4j + GDS + Enterprise Studio
make build     # generate the graph, score it with GDS, load it
make urls      # where everything is
```

| | |
|---|---|
| **Neo4j Browser** | http://localhost:7481 |
| **Enterprise Studio** | http://localhost:8083, deployment **Blast Radius** (Query, Explore, Dashboards) |
| **Bolt** | `bolt://localhost:7694` |
| **Database** | `blastradius`: the server's *default*, so every client opens on it |
| **Credentials** | in `.env` |

**Ports** are deliberately unusual so this runs next to the other demos; change them in `.env`.

Paste queries from `queries/demo-queries.cypher` into Query or Browser, in order or one at a time. Each stands alone.

`make down` stops everything and keeps the data. `make reset` deletes it.

### What the stack is for

This is the **development and demo** environment: Neo4j 2026.08, with GDS Enterprise for scoring and Studio for exploring. **The lab itself targets Neo4j 5.26 with no GDS**, which is what the JPMC sandbox runs. So GDS runs once here, and its results ship as ordinary properties in `load.cypher`. `make verify` tests everything on a clean 5.26.

To load into any other Neo4j 5.26 or later:

```bash
cypher-shell -a neo4j://localhost:7687 -u neo4j -d <database> -f graph/load.cypher
```

It's pure Cypher, needs no plugins or files, takes a few seconds, and is safe to repeat. It is {{f load_kb}} kB, in {{f load_statements}} small statements of at most {{f load_chunk}} rows each.

## The documents are generated

`README.md`, `STORYLINE.md`, `FACILITATOR-GUIDE.md`, `graph/MODEL.md` and `LAB-GUIDE.md` carry **no hand-typed figure, query or result**. Their text lives in templates (`build/docs/*.tmpl.md`, `build/lab-guide.template.md`); every number comes from `build/facts.py`, which reads the recorded results. **Edit the templates, never the outputs.** After changing the data or a query:

```bash
python3 build/verify.py --record           # re-run everything on 5.26 and record the results
python3 build/make_guide.py                # regenerate the five documents
uv run --with markdown build/make_pdf.py   # regenerate the two PDFs
```

If the data stops supporting a claim the prose makes (for example, that *Tap to pay* survives), rendering fails rather than printing something false.

## Check it

```bash
make verify        # clean Neo4j 5.26: the lab target
make verify-dev    # the dev server version
```

Each starts a throwaway container (removed afterwards, with its volume) laid out like the JPMC sandbox: an attendee database and a **non-admin user** whose home database it is, who runs every query without naming a database. It loads the graph twice (the second load must change nothing), runs the readiness check, the key-figure queries, all the demo queries and the hands-on statements, compares each to `build/expected/`, and fails if any generated document is out of date. It then re-runs the loader as that attendee, after a half-finished edit and after deleting everything, and checks the graph comes back identical: that is the facilitator's reset. It also enforces the lab rules: no `$params`, every path bounded, no APOC, no `//` comments inside a statement.

## Delivering it

[FACILITATOR-GUIDE.pdf](FACILITATOR-GUIDE.pdf) ([.md](FACILITATOR-GUIDE.md)) is for the people running the session: the clock, a script for each of the 16 steps with the number each one should land, Part 4 and how to reset a database, a first-aid table for helpers, the questions you'll get, what has and has not been tested, and what is still to confirm with JPMC. **To rehearse, each person needs their own database, because Part 4 writes:**

```bash
make rehearsal N=4        # lab-user01 to lab-user04 on the dev stack, each with its own non-admin login
make rehearsal-down N=4
```

## The 45-minute lab

The demo queries are the **reference**. The lab attendees run is a cut of them: **17 statements in five parts**, plus {{f stretch_count}} optional stretch challenges. Everything runs in Neo4j Browser. **No Bloom is needed.**

| Minutes | Part | Steps | Queries |
|---|---|---|---|
| before | Readiness check | | `R0` |
| 0 to 8 | **1. The page**: {{f storm_alerts}} alerts, one cause | 1 to 2 | `B1` `B1b` |
| 8 to 20 | **2. How bad is it?**: the radius, proven vs assumed, the range | 3 to 5 | `B2` `B2b` `B3b` |
| 20 to 30 | **3. Why can't we tell?**: the link, its birth, the replay | 6 to 8 | `B2c` `B6b` `B6c` |
| 30 to 38 | **4. Your turn**: classify the link (soft, then hard, then restore) | 9 to 14 | `H1` to `H6` (`H7` optional check) |
| 38 to 43 | **5. What do we do?**: what changed, what routing costs | 15 to 16 | `B8` `B7b` |
| 43 to 45 | The decision (presenter) | | |

**Stretch, not in the 45:** `B3` `B2d` `B4` `B4b` `B5` `B6` `B7` `B7c` `B9` `B10`, and the easter egg (`B11a` `B11b`; see STORYLINE.md, **spoilers**).

The guide is [LAB-GUIDE.pdf](LAB-GUIDE.pdf) (print, zip) and [LAB-GUIDE.md](LAB-GUIDE.md) (copy-paste).

## What the graph is

**{{n nodes}} nodes, {{n relationships}} relationships:** {{f services}} services and {{f datastores}} datastores, {{f teams}} teams, {{f journeys}} customer journeys, {{f incidents}} incidents over 18 months, {{f changes}} changes, {{f runbooks}} runbooks, {{f certificates}} certificates and tonight's {{f alerts}} alerts. See [graph/MODEL.md](graph/MODEL.md).

It is **deliberately messy**: {{f dep_unclassified}} dependencies nobody classified as hard or soft, {{f dep_undeclared}} seen in traces but never declared, {{f teams_disbanded}} disbanded teams that still own {{f owned_by_disbanded}} components, datastores nobody owns or ever rated, lookalike services, {{f runbooks_stale}} stale runbooks of {{f runbooks}}, incidents with missing fields, and alerts that are noise. That mess is what lets the story be honest.

## What the queries find

| Query | Result |
|---|---|
| B1b | {{f storm_alerts}} alerts across {{f storm_teams}} teams: **{{f storm_cause}} likely cause** (`{{f cause_name}}`, {{f cause_dependents}} alerting dependents), **{{f storm_symptoms}} symptoms**, **{{f storm_unrelated}} unrelated** |
| B2 / B2b | **{{f services_worst}} services fail in the worst case**: {{f services_proven}} proven, {{f services_assumed}} assumed. {{f services_degrade}} more degrade |
| B2c | One unclassified link matters most: `{{f link}}`, with {{f link_services}} services and {{f link_journeys}} journeys above it. The next has {{f link2_journeys}} |
| B2d | If that link is soft, the worst case falls from **{{f journeys_worst}} journeys to {{f journeys_if_soft}}**. Proven only: {{f journeys_proven}} |
| B3 / B3b | **{{f journeys_worst}} of {{f journeys}} journeys** down in the worst case, {{f journeys_proven}} proven. Attempts per hour: **{{n att03_best}} to {{n att03_worst}} at 03:00**, rising to **{{n att07_best}} to {{n att07_worst}} by 07:00** |
| B4 / B4b | {{f radius_teams_active}} active teams own something in the radius; {{f unpageable_names}} belong to disbanded teams |
| **B5** | **{{f b5_mismatch}} `MISMATCH`es**, led by **`profile-cache`**: declared tier {{f cache_tier}}, {{f cache_worst}} journeys in the worst case. Plus {{f b5_review}} `REVIEW` and {{f b5_unrated}} `UNRATED` |
| B6 / B6b | *Log in* reaches the cache through one `UNCLASSIFIED` link, added {{f link_first_seen}} by `{{f link_change}}`: undeclared, no risk review, {{f link_months}} months in production |
| **B6c** | **The replay.** The day before `{{f link_change}}`: {{f replay_services_before}} services, {{f replay_journeys_before}} journeys, {{n replay_att_before}} attempts a day. Tonight: {{f replay_services_after}}, **{{f replay_journeys_after}}**, {{n replay_att_after}} |
| **H1 to H7** | **Hands-on.** Mark the link soft: worst case falls to {{f journeys_if_soft}} journeys. Mark it hard: all {{f journeys_if_hard_proven}} are proven. Then restore it |
| B7 / B7b / B7c | {{f cache_incidents}} cache incidents, {{f cache_teams}} teams, **none to the owner**: {{n cache_minutes}} minutes. Tickets routed to the owner: {{f route_own_avg}} min average; elsewhere: {{f route_els_avg}}. Outages only at hit rates of {{f outage_hit_rates}} |
| B8 | {{f changes_window}} changes in 24 hours, {{f changes_in_radius}} in the radius. Closest: `{{f change_closest}}`, cache TTL 24h to 1h, no risk review |
| B9 | Of {{f radius_components}} components in the radius, {{f rb_none}} have no runbook, {{f rb_stale}} a stale one, {{f rb_current}} a current one |
| B10 | GDS PageRank ranks `{{f pr_top}}` first, above `{{f pr_second}}` |
| B11 | *There is a second hotspot. Spoilers are in STORYLINE.md* |

## Not built yet

The scripts to load and check 60 attendee databases (the facilitator guide has a tested check-in loop and the single-database reset, but not a loader for all 60), fill-in-the-blank variants, and a Bloom/Explore exercise. Studio's Explore is running locally but nothing has been designed or tested in it. **Nothing has been run with real people yet**, nor on the JPMC sandbox itself; the facilitator guide lists what is still to confirm.

## Notes

- **Licenses.** `gds.license` and `nes.license` are signed JWTs. They are gitignored and mounted into the containers, never baked into an image. GDS expires 2027-01-29; Studio expires **2026-12-13**.
- **Studio restarts.** Studio exits if Neo4j restarts under it, so it has a restart policy. If you ever see a blank page at :8083, `docker compose up -d` brings it back.
- **First boot only.** `NEO4J_AUTH` and the default-database setting apply only on the first start of a fresh volume. If you change them in `.env` afterwards, run `make reset`; otherwise Neo4j silently keeps the old values.
- **Rebuilding the live database.** `make build` clears the lab database first, because names change between generations.
