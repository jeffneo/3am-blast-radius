// ===========================================================================
//  3 a.m. Blast Radius: demo queries
//
//  Run in order, or any one on its own: every query stands alone, with its
//  inputs written in. "Tonight" is 2026-09-30T03:07:00Z.
//
//  Reading the edges. A DEPENDS_ON relationship carries:
//      confirmed  active, and known to be a hard dependency (critical = true)
//      hard       active, and NOT known to be soft: unclassified edges count
//                 as hard until someone proves otherwise (assume the worst)
//  `hard` is the worst case at 3 a.m.; `confirmed` is the best case you can prove.
//
//  Units. A JOURNEY is a thing customers do ("Log in", "Pay a bill", "Send a
//  wire"). Each is backed by several services. Customer figures are
//  journey ATTEMPTS: a customer who logs in and then checks a balance is two
//  attempts, so sums across journeys are not unique people.
//
//  Rules: no $params, variable-length paths bounded, no APOC. Each statement is
//  preceded by an id comment (B0, B1 ...) that the verifier uses to find its
//  recorded result.
// ===========================================================================


// B0 - Is the graph loaded? Nodes by their first label.
MATCH (n)
WITH labels(n)[0] AS label, count(*) AS nodes
RETURN label, nodes
ORDER BY nodes DESC;


// B1 - The page. What just fired, what is it, and who owns it?
MATCH (al:Alert {id: 'ALR-77120'})-[:FIRED_ON]->(d:Datastore)<-[:OWNS]-(t:Team)
RETURN al.fired_at AS fired, al.summary AS summary,
       d.name AS component, d.kind AS kind, d.tier AS declared_tier,
       t.name AS owner, t.pager AS pager;


// B1b - It is not one alert. Ten fired in six minutes. Which is the cause, which
//       are symptoms, and which have nothing to do with it? For each alerting
//       component: how many OTHER alerting components depend on it, and how many
//       does it depend on?
MATCH (all:Alert)-[:FIRED_ON]->(ac:Component)
WITH collect(DISTINCT ac) AS alerted
MATCH (al:Alert)-[:FIRED_ON]->(c:Component)<-[:OWNS]-(t:Team)
WITH al, c, t,
     size([o IN alerted WHERE o <> c AND EXISTS {
            MATCH p = (o)-[:DEPENDS_ON*1..8]->(c)
            WHERE all(r IN relationships(p) WHERE r.hard)
          }]) AS alerting_dependents,
     size([o IN alerted WHERE o <> c AND EXISTS {
            MATCH p = (c)-[:DEPENDS_ON*1..8]->(o)
            WHERE all(r IN relationships(p) WHERE r.hard)
          }]) AS alerting_dependencies
RETURN al.id AS alert, substring(toString(al.fired_at), 11, 5) AS at,
       c.name AS component, t.name AS team, alerting_dependents, alerting_dependencies,
       CASE WHEN alerting_dependencies = 0 AND alerting_dependents > 0 THEN 'likely cause'
            WHEN alerting_dependencies > 0 THEN 'symptom'
            ELSE 'unrelated' END AS role
ORDER BY alerting_dependents DESC, at, alert;


// B2 - Blast radius, in rings. Which services fail if profile-cache goes,
//      and how many hops from the cache are they? (Worst case: hard edges.)
//      Examples are the most critical (lowest tier number) in each ring.
MATCH p = (s:Service)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
WHERE all(r IN relationships(p) WHERE r.hard)
WITH s, min(length(p)) AS hops
ORDER BY coalesce(s.tier, 9), s.name
RETURN hops, count(*) AS services, collect(s.name)[0..5] AS most_critical_examples
ORDER BY hops;


// B2b - How sure are we? Split that radius by what we can PROVE.
//       "confirmed": every link on some path is a known hard dependency.
//       "assumed":   only an unclassified link keeps it on the list.
//       "degrades":  reachable, but only over soft links (fallbacks).
MATCH p = (s:Service)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
WHERE all(r IN relationships(p) WHERE r.active)
WITH s, collect(p) AS paths
WITH s,
     any(p IN paths WHERE all(r IN relationships(p) WHERE r.confirmed)) AS confirmed,
     any(p IN paths WHERE all(r IN relationships(p) WHERE r.hard)) AS assumed
WITH s, CASE WHEN confirmed THEN 'fails (confirmed)'
             WHEN assumed THEN 'fails (assumed)'
             ELSE 'degrades only' END AS impact
ORDER BY coalesce(s.tier, 9), s.name
RETURN impact, count(*) AS services, collect(s.name)[0..6] AS most_critical_examples
ORDER BY CASE impact WHEN 'fails (confirmed)' THEN 1 WHEN 'fails (assumed)' THEN 2 ELSE 3 END;


// B2c - What is the one thing worth finding out right now? The dependencies
//       on the path that nobody ever classified, ranked by how much sits
//       above each. Classify the top one and the radius changes shape.
MATCH (a:Component)-[e:DEPENDS_ON]->(b:Component)
WHERE e.active AND e.critical IS NULL
  AND EXISTS {
        MATCH p = (b)-[:DEPENDS_ON*0..8]->(:Datastore {name: 'profile-cache'})
        WHERE all(r IN relationships(p) WHERE r.hard)
      }
CALL {
  WITH a
  OPTIONAL MATCH p = (u:Service)-[:DEPENDS_ON*1..8]->(a)
  WHERE all(r IN relationships(p) WHERE r.hard)
  RETURN count(DISTINCT u) AS above
}
CALL {
  WITH a
  MATCH (j:Journey)-[:REQUIRES]->(s:Service)
  WHERE s = a OR EXISTS {
          MATCH p = (s)-[:DEPENDS_ON*1..8]->(a)
          WHERE all(r IN relationships(p) WHERE r.hard)
        }
  RETURN count(DISTINCT j) AS journeys
}
RETURN a.name + ' -> ' + b.name AS unclassified_dependency, e.source AS seen_via,
       toString(e.first_seen) AS first_seen, above + 1 AS services_at_stake, journeys AS journeys_at_stake
ORDER BY journeys_at_stake DESC, services_at_stake DESC, unclassified_dependency
LIMIT 6;


// B2d - What if we are wrong? Journeys down under three assumptions: the worst
//       case, the worst case if the one link from B2c turns out to be SOFT,
//       and only what is proven. The gap between the first two is what one
//       phone call to Identity & Access is worth.
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
       WHERE all(r IN relationships(p) WHERE r.hard
                 AND NOT (startNode(r).name = 'entitlements-svc' AND endNode(r).name = 'customer-profile-svc'))
     } AS if_soft,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.confirmed)
     } AS proven
UNWIND [{scenario: 'worst case (assume the unknowns)', down: worst},
        {scenario: 'if entitlements -> customer-profile is soft', down: if_soft},
        {scenario: 'proven only', down: proven}] AS sc
WITH sc.scenario AS scenario, j, sc.down AS down
WHERE down
ORDER BY j.name
RETURN scenario, count(j) AS journeys_down, collect(j.name) AS which
ORDER BY journeys_down DESC;


// B3 - What do customers see? Every journey: proven down, assumed down, or up,
//      and how many attempts per hour that is at 03:00 and at 07:00.
MATCH (j:Journey)
WITH j,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.confirmed)
     } AS confirmed,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.hard)
     } AS assumed
RETURN j.name AS journey,
       CASE WHEN confirmed THEN 'DOWN (confirmed)' WHEN assumed THEN 'DOWN (assumed)' ELSE 'up' END AS status,
       j.per_hour_0300 AS per_hour_at_0300, j.per_hour_0700 AS per_hour_at_0700
ORDER BY CASE WHEN confirmed THEN 0 WHEN assumed THEN 1 ELSE 2 END, j.customers_per_day DESC;


// B3b - The headline for the incident channel: a range, and a clock.
//       Journey attempts per hour affected now, and as the morning ramps up.
MATCH (j:Journey)
WITH j,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.confirmed)
     } AS confirmed,
     EXISTS {
       MATCH (j)-[:REQUIRES]->(s:Service)
       MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
       WHERE all(r IN relationships(p) WHERE r.hard)
     } AS assumed
UNWIND [{scenario: 'best case (proven only)', down: confirmed},
        {scenario: 'worst case (assume the unknowns)', down: assumed}] AS sc
WITH sc.scenario AS scenario, j, sc.down AS down
WHERE down
RETURN scenario, count(j) AS journeys_down,
       sum(j.per_hour_0300) AS attempts_per_hour_at_0300,
       sum(j.per_hour_0700) AS attempts_per_hour_at_0700,
       sum(j.per_hour_1200) AS attempts_per_hour_at_1200
ORDER BY journeys_down;


// B4 - Who do we page? Teams that own something in the worst-case radius.
MATCH (c:Component)
WHERE c.name = 'profile-cache'
   OR EXISTS {
        MATCH p = (c)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
        WHERE all(r IN relationships(p) WHERE r.hard)
      }
OPTIONAL MATCH (t:Team)-[:OWNS]->(c)
WITH coalesce(t.name, '(nobody)') AS team, t.status AS status, t.pager AS pager, c
ORDER BY c.name
RETURN team, status, pager, count(c) AS owns_in_radius, collect(c.name)[0..4] AS examples
ORDER BY owns_in_radius DESC, team;


// B4b - ...and who CANNOT be paged? Components in the radius whose owner has
//       been disbanded, or that nobody ever owned.
MATCH (c:Component)
WHERE EXISTS {
        MATCH p = (c)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
        WHERE all(r IN relationships(p) WHERE r.hard)
      }
OPTIONAL MATCH (t:Team)-[:OWNS]->(c)
WITH c, t
WHERE t IS NULL OR t.status <> 'active'
RETURN c.name AS component, c.lifecycle AS lifecycle,
       coalesce(t.name, '(nobody)') AS last_owner, toString(t.disbanded_on) AS disbanded_on
ORDER BY component;


// B5 - THE HIDDEN SHARED DEPENDENCY. For every datastore: how many customer
//      journeys depend on it (proven, and in the worst case), against the tier
//      it was declared at. MISMATCH: declared tier 2 or 3, yet 3+ journeys are
//      PROVEN to need it. UNRATED: never given a tier, yet 2+ journeys need it.
//      REVIEW: only the unclassified links put it there. Flagged rows come first,
//      the furthest below its true weight (highest declared tier number) at the top.
MATCH (d:Datastore)
CALL {
  WITH d
  MATCH (j:Journey)-[:REQUIRES]->(s:Service)
  WHERE EXISTS {
    MATCH p = (s)-[:DEPENDS_ON*1..8]->(d)
    WHERE all(r IN relationships(p) WHERE r.confirmed)
  }
  RETURN count(DISTINCT j) AS proven
}
CALL {
  WITH d
  MATCH (j:Journey)-[:REQUIRES]->(s:Service)
  WHERE EXISTS {
    MATCH p = (s)-[:DEPENDS_ON*1..8]->(d)
    WHERE all(r IN relationships(p) WHERE r.hard)
  }
  RETURN count(DISTINCT j) AS worst_case
}
WITH d, proven, worst_case,
     CASE WHEN d.tier >= 2 AND proven >= 3 THEN 'MISMATCH'
          WHEN d.tier IS NULL AND proven >= 2 THEN 'UNRATED'
          WHEN d.tier >= 2 AND worst_case >= 3 THEN 'REVIEW'
          ELSE '' END AS flag
WHERE worst_case >= 3 OR flag <> ''
RETURN d.name AS datastore, d.kind AS kind, d.tier AS declared_tier,
       proven AS journeys_proven, worst_case AS journeys_worst_case, flag
ORDER BY CASE flag WHEN 'MISMATCH' THEN 0 WHEN 'UNRATED' THEN 1 WHEN 'REVIEW' THEN 2 ELSE 3 END,
         coalesce(d.tier, 0) DESC, proven DESC, worst_case DESC, datastore
LIMIT 12;


// B6 - Why? The chain from a journey down to profile-cache, with the status of
//      every link. Send a wire is proven end to end. Log in has exactly one
//      link nobody has classified.
UNWIND [{journey: 'Send a wire', mode: 'confirmed'}, {journey: 'Log in', mode: 'hard'}] AS q
MATCH (j:Journey {name: q.journey}), (d:Datastore {name: 'profile-cache'})
MATCH p = shortestPath((j)-[:REQUIRES|DEPENDS_ON*1..9]->(d))
WHERE all(r IN relationships(p) WHERE type(r) = 'REQUIRES'
          OR (q.mode = 'confirmed' AND r.confirmed) OR (q.mode = 'hard' AND r.hard))
RETURN j.name AS journey, [n IN nodes(p) | n.name] AS chain,
       [r IN relationships(p) | CASE WHEN type(r) = 'REQUIRES' THEN 'requires'
                                     WHEN r.critical IS NULL THEN 'UNCLASSIFIED'
                                     WHEN r.critical THEN 'critical' ELSE 'soft' END] AS links;


// B6b - How did Log in come to depend on a cache? The unclassified link in that
//       chain: when it appeared, what change introduced it, and whether anyone
//       ever declared it.
MATCH (a:Component {name: 'entitlements-svc'})-[e:DEPENDS_ON]->(b:Component {name: 'customer-profile-svc'})
MATCH (ch:Change {id: e.introduced_by})-[:DEPLOYED_TO]->(:Service)<-[:OWNS]-(t:Team)
RETURN a.name + ' -> ' + b.name AS dependency, e.source AS seen_via,
       toString(e.first_seen) AS first_seen, ch.id AS introduced_by, ch.what AS change,
       t.name AS team, ch.risk_review AS had_risk_review,
       duration.inMonths(e.first_seen, date('2026-09-30')).months AS months_in_production;


// B6c - REPLAY. How big was the blast radius the day before that change, and how
//       big is it tonight? The same question asked "as of" two dates, using only
//       the dependencies that existed on each (first_seen), with today's
//       classifications. One undeclared change, no risk review.
MATCH (ch:Change {id: 'CHG-1873'})
WITH date(ch.deployed_at) AS changed
UNWIND [changed - duration('P1D'), date('2026-09-30')] AS asof
CALL {
  WITH asof
  MATCH (s:Service)
  WHERE EXISTS {
    MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
    WHERE all(r IN relationships(p) WHERE r.hard AND r.first_seen <= asof)
  }
  RETURN count(s) AS services_failing
}
CALL {
  WITH asof
  MATCH (j:Journey)
  WHERE EXISTS {
    MATCH (j)-[:REQUIRES]->(s:Service)
    MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
    WHERE all(r IN relationships(p) WHERE r.hard AND r.first_seen <= asof)
  }
  RETURN count(j) AS journeys_down, sum(j.customers_per_day) AS attempts_per_day
}
RETURN toString(asof) AS as_of, services_failing, journeys_down, attempts_per_day
ORDER BY as_of;


// B7 - Have we been here before? Root causes ranked by total minutes of customer
//      impact, with who got the ticket versus who owns the cause. Customer counts
//      sum only the incidents that recorded one.
MATCH (i:Incident)-[:ROOT_CAUSE]->(c:Component)
OPTIONAL MATCH (o:Team)-[:OWNS]->(c)
MATCH (i)-[:ASSIGNED_TO]->(a:Team)
WITH c, o, count(i) AS incidents, sum(i.duration_minutes) AS minutes,
     sum(i.customers_impacted) AS customers, collect(DISTINCT a.name) AS assigned_to,
     sum(CASE WHEN a = o THEN 1 ELSE 0 END) AS assigned_to_owner
RETURN c.name AS root_cause, coalesce(o.name, '(nobody)') AS owner, incidents,
       minutes AS total_minutes, customers AS customers_impacted,
       size(assigned_to) AS teams_assigned, assigned_to_owner
ORDER BY total_minutes DESC
LIMIT 5;


// B7b - What does routing to the wrong team cost? Every incident with a recorded
//       root cause, by whether the ticket went to the owner of that root cause.
MATCH (i:Incident)-[:ROOT_CAUSE]->(c:Component)
OPTIONAL MATCH (o:Team)-[:OWNS]->(c)
MATCH (i)-[:ASSIGNED_TO]->(a:Team)
WITH i, CASE WHEN a = o THEN 'assigned to the owner' ELSE 'assigned elsewhere' END AS routing
RETURN routing, count(i) AS incidents,
       round(avg(i.duration_minutes)) AS avg_minutes, percentileCont(i.duration_minutes, 0.5) AS median_minutes,
       round(avg(i.reassignments) * 10) / 10 AS avg_reassignments
ORDER BY routing;


// B7c - What does history say about the unclassified link? Every past
//       profile-cache incident, and whether the services above it slowed
//       down or failed.
MATCH (i:Incident)-[:ROOT_CAUSE]->(:Datastore {name: 'profile-cache'})
MATCH (i)-[:ASSIGNED_TO]->(a:Team)
RETURN toString(date(i.started_at)) AS date, i.id AS incident, i.impact AS impact,
       i.duration_minutes AS minutes, a.name AS assigned_to, i.detail AS detail
ORDER BY date;


// B8 - What changed? Every change in the 24 hours before the page, ranked by how
//      close it is to the cache. A change far from the radius is noise.
MATCH (ch:Change)-[:DEPLOYED_TO]->(s:Service)
WHERE ch.deployed_at >= datetime('2026-09-30T03:07:00Z') - duration('PT24H')
  AND ch.deployed_at <= datetime('2026-09-30T03:07:00Z')
OPTIONAL MATCH p = (s)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
WHERE all(r IN relationships(p) WHERE r.hard)
WITH ch, s, min(length(p)) AS hops
RETURN ch.id AS change, s.name AS service, ch.what AS what,
       substring(toString(ch.deployed_at), 0, 16) AS deployed_at,
       duration.inSeconds(ch.deployed_at, datetime('2026-09-30T03:07:00Z')).hours AS hours_before_page,
       CASE WHEN hops IS NULL THEN 'no' ELSE 'yes' END AS in_radius, hops AS hops_from_cache,
       ch.risk_review AS had_risk_review
ORDER BY hops IS NULL, hops, ch.deployed_at DESC;


// B9 - Are we covered at 3 a.m.? Runbook coverage across the radius, and
//      whether the runbook we have was reviewed in the last year.
MATCH (c:Component)
WHERE c.name = 'profile-cache'
   OR EXISTS {
        MATCH p = (c)-[:DEPENDS_ON*1..8]->(:Datastore {name: 'profile-cache'})
        WHERE all(r IN relationships(p) WHERE r.hard)
      }
OPTIONAL MATCH (rb:Runbook)-[:COVERS]->(c)
WITH c, collect(rb) AS runbooks
WITH c, CASE WHEN size(runbooks) = 0 THEN 'no runbook'
             WHEN any(r IN runbooks WHERE NOT r.stale) THEN 'runbook (current)'
             ELSE 'runbook (stale)' END AS coverage
ORDER BY coalesce(c.tier, 9), c.name
RETURN coverage, count(*) AS components, collect(c.name)[0..6] AS most_critical_examples
ORDER BY coverage;


// B10 - What do the numbers say, independent of anything we declared?
//       PageRank over the hard dependencies (precomputed with GDS): how much of
//       the estate leans on each component. Compare the rank to its declared tier.
MATCH (c:Component)
RETURN c.name AS component, labels(c)[1] AS kind, c.tier AS declared_tier,
       c.pagerank AS pagerank, c.cluster_id AS cluster
ORDER BY c.pagerank DESC, c.name
LIMIT 8;


// B11a - What kinds of things are in this graph? Every label, and how many.
//        (Does every one of them appear in your guide?)
MATCH (n)
UNWIND labels(n) AS label
RETURN label, count(*) AS nodes
ORDER BY nodes DESC, label;


// B11b - EASTER EGG. Certificates expiring within 60 days: when, whether they
//        renew themselves, who owns them, and how much leans on each.
MATCH (c:Certificate)
WITH c, duration.inDays(date('2026-09-30'), c.expires_on).days AS days_left
WHERE days_left <= 60
CALL {
  WITH c
  OPTIONAL MATCH (i:Incident)-[:ROOT_CAUSE]->(c)
  RETURN toString(max(date(i.started_at))) AS last_expiry_outage, max(i.duration_minutes) AS last_outage_minutes
}
OPTIONAL MATCH (t:Team)-[:OWNS]->(c)
OPTIONAL MATCH (s:Service)-[:USES_CERT]->(c)
OPTIONAL MATCH (st:Team)-[:OWNS]->(s)
OPTIONAL MATCH (j:Journey)-[:REQUIRES]->(s)
RETURN c.name AS certificate, days_left AS expires_in_days,
       CASE c.auto_renew WHEN true THEN 'yes' WHEN false THEN 'NO' ELSE 'unknown' END AS renews_itself,
       coalesce(t.name, '(nobody)') + CASE WHEN t.status = 'disbanded' THEN ' (disbanded)' ELSE '' END AS owner,
       count(DISTINCT s) AS services, count(DISTINCT st) AS teams, count(DISTINCT j) AS journeys,
       toString(c.last_rotated) AS last_rotated, last_expiry_outage, last_outage_minutes
ORDER BY expires_in_days, certificate;
