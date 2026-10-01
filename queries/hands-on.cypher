// ===========================================================================
//  Hands-on: classify the link
//
//  So far you have only READ the graph. This part changes it, and you watch
//  the answer change. The link is the one from B2c:
//
//      entitlements-svc -> customer-profile-svc     (never classified)
//
//  Nobody knows whether it is hard or soft. Decide, and see what each answer
//  would mean at 3 a.m.
//
//  Run in order. Every statement says what it changes. These write to YOUR
//  database only. To put everything back at any time, run H6, or re-load
//  graph/load.cypher (it restores every property).
//
//  The two flags the demo queries read, `hard` and `confirmed`, are derived from
//  `critical` and `active`. Each classify statement recomputes them for every
//  dependency, so the queries see the change.
// ===========================================================================


// H1 - The scoreboard, BEFORE. Journeys down in the worst case (assume the
//      unknowns) and proven (known hard dependencies only), out of all the journeys.
MATCH (j:Journey)
WITH j,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.hard)
     } AS worst,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.confirmed)
     } AS proven
RETURN sum(CASE WHEN worst THEN 1 ELSE 0 END) AS journeys_down_worst_case,
       sum(CASE WHEN proven THEN 1 ELSE 0 END) AS journeys_down_proven;


// H2 - Suppose entitlements-svc survives a slow profile service: the link is SOFT.
//      CHANGES: critical = false on that one dependency, then refreshes hard/confirmed.
MATCH (:Component {name: 'entitlements-svc'})-[e:DEPENDS_ON]->(:Component {name: 'customer-profile-svc'})
SET e.critical = false
WITH count(e) AS links_classified
MATCH ()-[x:DEPENDS_ON]->()
SET x.hard = x.active AND coalesce(x.critical, true),
    x.confirmed = x.active AND coalesce(x.critical, false)
RETURN links_classified, count(x) AS flags_refreshed;


// H3 - The scoreboard again. The worst case should have shrunk.
MATCH (j:Journey)
WITH j,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.hard)
     } AS worst,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.confirmed)
     } AS proven
RETURN sum(CASE WHEN worst THEN 1 ELSE 0 END) AS journeys_down_worst_case,
       sum(CASE WHEN proven THEN 1 ELSE 0 END) AS journeys_down_proven;


// H4 - Now the opposite: suppose it is HARD, and entitlements fails when the
//      profile service is slow. CHANGES: critical = true, then refreshes the flags.
MATCH (:Component {name: 'entitlements-svc'})-[e:DEPENDS_ON]->(:Component {name: 'customer-profile-svc'})
SET e.critical = true
WITH count(e) AS links_classified
MATCH ()-[x:DEPENDS_ON]->()
SET x.hard = x.active AND coalesce(x.critical, true),
    x.confirmed = x.active AND coalesce(x.critical, false)
RETURN links_classified, count(x) AS flags_refreshed;


// H5 - The scoreboard once more. Now the "proven" numbers jump: what was
//      doubt is now fact.
MATCH (j:Journey)
WITH j,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.hard)
     } AS worst,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.confirmed)
     } AS proven
RETURN sum(CASE WHEN worst THEN 1 ELSE 0 END) AS journeys_down_worst_case,
       sum(CASE WHEN proven THEN 1 ELSE 0 END) AS journeys_down_proven;


// H6 - Put it back: the link is unclassified again (critical removed).
//      CHANGES: removes critical from that dependency, then refreshes the flags.
MATCH (:Component {name: 'entitlements-svc'})-[e:DEPENDS_ON]->(:Component {name: 'customer-profile-svc'})
REMOVE e.critical
WITH count(e) AS links_reset
MATCH ()-[x:DEPENDS_ON]->()
SET x.hard = x.active AND coalesce(x.critical, true),
    x.confirmed = x.active AND coalesce(x.critical, false)
RETURN links_reset, count(x) AS flags_refreshed;


// H7 - The scoreboard, restored. It should match H1 exactly.
MATCH (j:Journey)
WITH j,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.hard)
     } AS worst,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.confirmed)
     } AS proven
RETURN sum(CASE WHEN worst THEN 1 ELSE 0 END) AS journeys_down_worst_case,
       sum(CASE WHEN proven THEN 1 ELSE 0 END) AS journeys_down_proven;
