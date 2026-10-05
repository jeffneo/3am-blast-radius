// ===========================================================================
//  Graph Data Science, run LIVE.
//
//  These need the GDS plugin. The core lab does not: PageRank and the Louvain
//  communities are also stored on every component (B10), so the lab works
//  without GDS. Run these only if GDS is enabled in your sandbox.
//
//  Each statement is self-contained and cleans up after itself: it drops its
//  own in-memory graph first (in case an earlier run was interrupted), builds
//  a fresh projection of the CURRENT hard dependencies, runs the algorithm,
//  and drops the projection again. The projection is a snapshot: change the
//  graph, and you must run the statement again to see it.
//
//  Read-only on your data: the algorithms run in memory (stream mode) and write
//  nothing to the database.
// ===========================================================================


// G0 - Is GDS here? (for the organisers' smoke test; attendees do not need it)
RETURN gds.version() AS gds_version;


// G1 - PageRank, live. Over the hard dependencies, flowing from a dependent to
//      what it needs: high means "a lot of the estate leans on this". Shows the
//      top five, plus the three components the story is about, with their rank.
//      `precomputed` is the stored property B10 reads; after you change the graph
//      the two disagree, because the stored one is a snapshot.
CALL gds.graph.drop('lab_pagerank', false) YIELD graphName
WITH count(*) AS cleared
MATCH (s:Component)
OPTIONAL MATCH (s)-[r:DEPENDS_ON]->(t:Component)
WHERE r.hard
WITH gds.graph.project('lab_pagerank', s, t) AS g
CALL gds.pageRank.stream(g.graphName, {maxIterations: 50, dampingFactor: 0.85}) YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS c, score
ORDER BY score DESC, c.name
WITH collect({c: c, score: score}) AS ranked
CALL gds.graph.drop('lab_pagerank') YIELD graphName
UNWIND range(0, size(ranked) - 1) AS i
WITH ranked[i].c AS c, ranked[i].score AS score, i + 1 AS rank
WHERE rank <= 5 OR c.name IN ['profile-cache', 'entitlements-svc', 'customer-profile-svc']
RETURN rank, c.name AS component, c.tier AS declared_tier,
       round(score * 1000) / 1000.0 AS live_pagerank,
       round(c.pagerank * 1000) / 1000.0 AS precomputed
ORDER BY rank;


// G2 - Louvain communities, live. Which components hang together through hard
//      dependencies, ignoring direction, and how many TEAMS each group spans.
//      Compare the group around profile-cache with the team that owns it.
//      concurrency 1 makes the result repeatable. Groups of fewer than five
//      components are left out, except the one holding the cache.
CALL gds.graph.drop('lab_communities', false) YIELD graphName
WITH count(*) AS cleared
MATCH (s:Component)
OPTIONAL MATCH (s)-[r:DEPENDS_ON]->(t:Component)
WHERE r.hard
WITH gds.graph.project('lab_communities', s, t, {}, {undirectedRelationshipTypes: ['*']}) AS g
CALL gds.louvain.stream(g.graphName, {concurrency: 1}) YIELD nodeId, communityId
WITH communityId, collect(gds.util.asNode(nodeId)) AS members
WITH collect(members) AS communities
CALL gds.graph.drop('lab_communities') YIELD graphName
WITH communities, head([(t:Team)-[:OWNS]->(:Datastore {name: 'profile-cache'}) | t.name]) AS cache_owner
UNWIND communities AS members
WITH members, cache_owner,
     any(m IN members WHERE m.name = 'profile-cache') AS has_cache,
     [m IN members | head([(t:Team)-[:OWNS]->(m) | t.name])] AS owners
CALL {
  WITH owners
  UNWIND [o IN owners WHERE o IS NOT NULL] AS o
  WITH o, count(*) AS n
  ORDER BY n DESC, o
  RETURN count(*) AS teams, head(collect(o)) AS biggest_owner, head(collect(n)) AS biggest_owner_owns
}
WITH members, has_cache, teams, biggest_owner, biggest_owner_owns,
     size([o IN owners WHERE o = cache_owner]) AS owned_by_cache_owner
WHERE size(members) >= 5 OR has_cache
RETURN size(members) AS components, teams, biggest_owner, biggest_owner_owns,
       owned_by_cache_owner, has_cache AS has_profile_cache
ORDER BY components DESC, biggest_owner;
