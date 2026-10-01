// ===========================================================================
//  GDS scores on :Component. Run ONCE, in the build environment.
//
//  The lab's target (Neo4j 5.26 on the JPMC sandbox) has no Graph Data Science,
//  so these results are exported and embedded in graph/load.cypher as ordinary
//  properties by build/build.sh. Attendees never run this file.
//
//    pagerank    how much of the estate leans on this component. Rank flows
//                from a dependent to its dependencies, so a component many
//                things depend on, directly or through others, scores high.
//                Computed over hard edges only (active, and not known-soft).
//    cluster_id  Louvain community over the same edges, ignoring direction.
//                Renumbered by size afterwards (1 = largest), by merge_scores.py.
//
//  Both use only the hard edges, so the scores describe what breaks, not what
//  merely talks.
// ===========================================================================

CALL gds.graph.drop('deps', false) YIELD graphName RETURN graphName;
CALL gds.graph.drop('deps_u', false) YIELD graphName RETURN graphName;

// Dependents point at their dependencies, so PageRank mass pools on the things
// everyone needs. Every component is projected, so isolated ones still get a score.
MATCH (s:Component)
OPTIONAL MATCH (s)-[r:DEPENDS_ON]->(t:Component)
WHERE r.hard
WITH gds.graph.project('deps', s, t) AS g
RETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS relationships;

MATCH (s:Component)
OPTIONAL MATCH (s)-[r:DEPENDS_ON]->(t:Component)
WHERE r.hard
WITH gds.graph.project('deps_u', s, t, {}, {undirectedRelationshipTypes: ['*']}) AS g
RETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS relationships;

CALL gds.pageRank.write('deps', {writeProperty: 'pagerank', maxIterations: 50, dampingFactor: 0.85})
YIELD nodePropertiesWritten, ranIterations, didConverge
RETURN nodePropertiesWritten, ranIterations, didConverge;

// concurrency 1 and a fixed seed of work keep the result reproducible.
CALL gds.louvain.write('deps_u', {writeProperty: 'cluster_id', concurrency: 1, maxLevels: 10})
YIELD communityCount, modularity, nodePropertiesWritten
RETURN communityCount, modularity, nodePropertiesWritten;

CALL gds.graph.drop('deps') YIELD graphName RETURN graphName;
CALL gds.graph.drop('deps_u') YIELD graphName RETURN graphName;
