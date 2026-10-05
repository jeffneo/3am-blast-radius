// ===========================================================================
//  Bloom search phrases
//
//  Bloom draws NODES and RELATIONSHIPS, so unlike the demo queries (which
//  return tables) each phrase here returns PATHS, in a column named p. Paste the
//  Cypher into a Bloom search phrase; the line marked `phrase:` is what you type
//  to run it, and `$name` is a parameter Bloom asks for.
//
//  Every phrase is checked by build/verify.py on Neo4j 5.26 as an attendee: it
//  must run, return paths, and keep the picture a readable size (the size is
//  recorded in build/expected/). Like the demo queries: bounded paths, no APOC.
//  Unlike them, these use $parameters: that is what Bloom's phrases are for.
//
//  `param:` lines give the default the verifier (and the guide) use.
// ===========================================================================


// P1 - The blast radius: everything that fails if a component goes, in the
//      worst case (every hard dependency, unclassified included).
//      phrase:  blast radius of $component
//      param:   component = profile-cache
MATCH p = (s:Service)-[:DEPENDS_ON*1..8]->(d:Component {name: $component})
WHERE all(r IN relationships(p) WHERE r.hard)
RETURN p;


// P2 - Why does a journey depend on the cache? One journey, link by link.
//      phrase:  chain for $journey
//      param:   journey = Log in
MATCH p = (j:Journey {name: $journey})-[:REQUIRES]->(:Service)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
WHERE all(r IN relationships(p) WHERE type(r) = 'REQUIRES' OR r.hard)
RETURN p;


// P3 - Have we been here before? The incidents a component caused, the teams
//      the tickets went to, and the team that owns it.
//      phrase:  incidents caused by $component
//      param:   component = profile-cache
MATCH p = (t:Team)<-[:ASSIGNED_TO]-(:Incident)-[:ROOT_CAUSE]->(c:Component {name: $component})<-[:OWNS]-(:Team)
RETURN p;


// P4 - Who do we page? The teams that own something in the blast radius, each
//      hanging off what it owns. Disbanded teams have nobody to page.
//      phrase:  teams to page for $component
//      param:   component = profile-cache
MATCH p = (:Team)-[:OWNS]->(s:Service)-[:DEPENDS_ON*1..8]->(d:Component {name: $component})
WHERE all(r IN relationships(p) WHERE type(r) = 'OWNS' OR r.hard)
RETURN p;


// P5 - What changed? Changes in the 24 hours before the page, on a service in
//      the blast radius, with the path to the component.
//      phrase:  changes near $component
//      param:   component = profile-cache
MATCH p = (ch:Change)-[:DEPLOYED_TO]->(:Service)-[:DEPENDS_ON*1..8]->(d:Component {name: $component})
WHERE ch.deployed_at >= datetime('2026-09-30T03:07:00Z') - duration('PT24H')
  AND ch.deployed_at <= datetime('2026-09-30T03:07:00Z')
  AND all(r IN relationships(p) WHERE type(r) = 'DEPLOYED_TO' OR r.hard)
RETURN p;


// P6 - Tonight's alert storm as a picture: how the alerting components depend on
//      one another (through anything in between). The cause is where the paths
//      end; the unrelated alerts are the ones with no path at all.
//      phrase:  alert storm
MATCH (:Alert)-[:FIRED_ON]->(c:Component)
WITH collect(DISTINCT c) AS alerting
UNWIND alerting AS a
MATCH p = (a)-[:DEPENDS_ON*1..8]->(b:Component)
WHERE b IN alerting AND all(r IN relationships(p) WHERE r.hard)
RETURN p;


// P7 - The unclassified links: dependencies nobody classified that sit on a
//      path to the component. Select one in Bloom to see what hangs above it.
//      phrase:  unclassified links to $component
//      param:   component = profile-cache
MATCH p = (:Component)-[e:DEPENDS_ON]->(b:Component)
WHERE e.active AND e.critical IS NULL
  AND EXISTS {
        MATCH q = (b)-[:DEPENDS_ON*0..8]->(:Component {name: $component})
        WHERE all(r IN relationships(q) WHERE r.hard)
      }
RETURN p;


// P8 - The second hotspot: who depends on a certificate, and who owns them.
//      phrase:  who depends on certificate $certificate
//      param:   certificate = wildcard.internal.bank
MATCH p = (:Team)-[:OWNS]->(:Certificate {name: $certificate})<-[:USES_CERT]-(:Service)<-[:OWNS]-(:Team)
RETURN p;
