// ===========================================================================
//  Key figures. NOT part of the lab: build/verify.py runs these so that every
//  number quoted in the documents comes from a tested result, never from memory.
//  Read-only. Ids are K1, K2 ...
// ===========================================================================


// K1 - Nodes by label (a node with two labels counts under each)
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS n
ORDER BY label;


// K2 - Relationships by type
MATCH ()-[r]->()
RETURN type(r) AS rel, count(*) AS n
ORDER BY rel;


// K3 - The mess in the dependencies
MATCH ()-[e:DEPENDS_ON]->(b)
RETURN count(*) AS total,
       sum(CASE WHEN e.critical IS NULL THEN 1 ELSE 0 END) AS unclassified,
       sum(CASE WHEN e.source = 'observed' THEN 1 ELSE 0 END) AS undeclared,
       sum(CASE WHEN e.source = 'observed' AND b.name = 'tracing-collector' THEN 1 ELSE 0 END) AS tracing,
       sum(CASE WHEN NOT e.active THEN 1 ELSE 0 END) AS inactive,
       sum(CASE WHEN e.critical IS NULL AND e.active AND e.source = 'observed' THEN 1 ELSE 0 END) AS unclassified_and_undeclared;


// K4 - Components that depend on each other
MATCH (a:Component)-[:DEPENDS_ON]->(b:Component)-[:DEPENDS_ON]->(a)
WHERE a.name < b.name
RETURN count(*) AS mutual_pairs;


// K5 - Ownership and rating gaps
MATCH (c:Component)
OPTIONAL MATCH (t:Team)-[:OWNS]->(c)
RETURN sum(CASE WHEN t IS NULL THEN 1 ELSE 0 END) AS unowned,
       sum(CASE WHEN t.status = 'disbanded' THEN 1 ELSE 0 END) AS owned_by_disbanded,
       sum(CASE WHEN c.tier IS NULL THEN 1 ELSE 0 END) AS unrated,
       sum(CASE WHEN c.lifecycle = 'deprecated' THEN 1 ELSE 0 END) AS deprecated;


// K6 - Teams
MATCH (t:Team)
RETURN count(t) AS teams,
       sum(CASE WHEN t.status = 'disbanded' THEN 1 ELSE 0 END) AS disbanded,
       sum(CASE WHEN t.status = 'active' AND t.pager IS NULL THEN 1 ELSE 0 END) AS active_without_pager;


// K7 - Runbooks
MATCH (r:Runbook)
RETURN count(r) AS runbooks, sum(CASE WHEN r.stale THEN 1 ELSE 0 END) AS stale;


// K8 - Incidents
MATCH (i:Incident)
RETURN count(i) AS incidents,
       sum(CASE WHEN EXISTS { (i)-[:ROOT_CAUSE]->(:Component) } THEN 1 ELSE 0 END) AS with_component_root_cause,
       sum(CASE WHEN NOT EXISTS { (i)-[:ROOT_CAUSE]->() } THEN 1 ELSE 0 END) AS without_any_root_cause,
       sum(CASE WHEN i.customers_impacted IS NULL THEN 1 ELSE 0 END) AS without_customer_count,
       toString(date(min(i.started_at))) AS first_incident, toString(date(max(i.started_at))) AS last_incident;


// K9 - Certificates and changes
MATCH (c:Certificate)
WITH count(c) AS certificates,
     sum(CASE WHEN c.auto_renew IS NULL THEN 1 ELSE 0 END) AS renewal_unknown,
     sum(CASE WHEN c.auto_renew = false THEN 1 ELSE 0 END) AS manual
MATCH (ch:Change)
RETURN certificates, renewal_unknown, manual, count(ch) AS changes,
       sum(CASE WHEN ch.deployed_at >= datetime('2026-09-29T03:07:00Z') THEN 1 ELSE 0 END) AS changes_last_24h;
