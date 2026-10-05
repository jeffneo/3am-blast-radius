# 3 a.m. Blast Radius

**Hands-on lab · about 45 minutes · Neo4j Browser**

> **03:07.** Your pager goes off: `profile-cache p99 latency 4.2s, hit rate 31% and falling`.
> It's a cache. Declared tier 3. It can probably wait until morning.
>
> *Can it?*

You're the on-call engineer at a large retail bank. Over the next 45 minutes you'll use a graph of the bank's systems to work out **what is actually broken, for whom, how sure anyone can be, and who to wake up**. You will also change the graph yourself and watch the answer move.

By the end you'll have:

- turned **{{f storm_alerts}} alerts from {{f storm_teams}} teams** into one likely cause;
- measured a **blast radius**, and separated what is *proven* from what is only *assumed*;
- found the **one link** that nobody ever checked, and seen how it got there;
- **changed the graph** and watched the answer change;
- decided what to do before the morning rush.

Everything happens in your web browser. **There is nothing to install.**

**Everything here is fictional.** The bank, its teams, services, incidents and customer numbers are invented for this exercise. Nothing describes any real institution's architecture.

---

## Before the session: prerequisites

### What you need

| | |
|---|---|
| **A laptop** | Your corporate laptop is fine. Bring it charged |
| **A current web browser** | Chrome or Edge recommended |
| **Your lab credentials** | From the pre-event email: username, password and the **Neo4j Browser URL** |
| **Two minutes, at least a day before** | For the readiness check below. Do it from the laptop and network you'll bring |
| **Neo4j or Cypher experience** | **Not required.** Every query is provided: you copy, paste and read. If you know Cypher, there are stretch challenges at the end |

You get your own database. Nobody else can see it or change it, and you can't break anyone else's. **This lab uses Neo4j Browser only.**

### The readiness check (do this before the session)

1. Open the **Neo4j Browser URL** from your pre-event email and log in.
2. Paste this into the editor at the top of the page and press **Ctrl+Enter** (Windows) or **Cmd+Enter** (Mac):

{{query R0}}

3. You should see one row like this, with **your own database name** where this example says `lab-user01`:

{{result R0}}

**If `components` shows 0, you get an error saying something "is not allowed" on database `neo4j`, or you can't log in:** don't try to fix it yourself. Email the contact in your pre-event email with a screenshot. It almost always means your login opened the wrong database, and that is a one-minute fix on our side. The check also leaves a small marker in your database, which is how we know who is ready.

---

## How the lab works

- **The presenter runs every step on the big screen** at the same time as you. If something doesn't work on your laptop, keep watching; you won't miss the point.
- **Run one query at a time.** Paste it, run it, read the result, then clear the editor for the next one.
- **Copy the whole block**, from the first line to the semicolon at the end.
- **Queries stand alone**, so if you fall behind, skip ahead to where the room is. **The one exception is Part 4**, which changes the graph: do its steps in order.
- **Predict first.** Where you see **Predict**, say your guess out loud or to your neighbour before you run the query. It's more fun and you'll remember more.
- **Stuck? Raise your hand.** Helpers are walking the room.

### Neo4j Browser in 60 seconds
- The **editor** is the box at the top. Paste a query there and press **Ctrl+Enter** / **Cmd+Enter**, or click the ▶ button.
- Each result appears in a **frame** below, newest on top. These queries return rows, which Browser shows as a **table**.
- To clear old frames, type `:clear` and run it.

### Reading Cypher in 60 seconds
Cypher describes patterns the way you would draw them on a whiteboard:

```cypher
MATCH (s:Service)-[:DEPENDS_ON]->(d:Datastore)
```

This reads: *a Service `s` that DEPENDS_ON a Datastore `d`*. Round brackets are **things**, square brackets are **connections**, and `:Word` is a label or a connection type. `WHERE` filters, and `RETURN` says what to show. `-[:DEPENDS_ON*1..8]->` means "follow DEPENDS_ON connections, between 1 and 8 in a row".

That is enough to read every query in this lab.

---

## The world you're investigating

A bank's technology estate, as a graph:

```
(:Team) ─[:OWNS]─▶ (:Component)  ◀─[:ROOT_CAUSE]── (:Incident) ─[:ASSIGNED_TO]─▶ (:Team)
                      │  ▲                         
        [:DEPENDS_ON] │  └─[:DEPLOYED_TO]── (:Change)
                      ▼
                (:Component)         (:Journey) ─[:REQUIRES]─▶ (:Service)
                                     (:Alert)   ─[:FIRED_ON]─▶ (:Component)
```

- A **Component** is either a **Service** (code that runs) or a **Datastore** (a database, cache or queue).
- A **Journey** is *a thing customers do*: Log in, Pay a bill, Send a wire. There are {{f journeys}}. Each needs several services to work.
- Every Component has a **tier**: 1 means customer-facing and critical, 3 means it can wait until morning. For a Datastore this is the tier it was **declared** to have.
- **Customer numbers count attempts.** Someone who logs in and then checks a balance is two attempts, so these are not unique people.

### Three kinds of dependency
Every `DEPENDS_ON` connection says how much one component needs another:

| | meaning |
|---|---|
| **Hard** (`critical = true`) | The caller fails without it |
| **Soft** (`critical = false`) | The caller slows down or falls back |
| **Unclassified** (`critical` is empty) | **Nobody ever decided.** Common in real systems |

Two flags, worked out from that, appear in the queries:

| flag | means |
|---|---|
| **`confirmed`** | Known to be hard. This is **what you can prove** |
| **`hard`** | Not known to be soft, so **assume the worst** until someone proves otherwise |

So *confirmed* is the best case you can defend, and *hard* is the worst case you must plan for. The distance between them is what this lab is about.

---

## Part 1: The page (about 8 minutes)

**03:07.** It's a tier-3 cache. Surely it can wait.

### Step 1: What fired?

{{query B1}}

**You should see** one row: a Redis cache called `profile-cache`, **declared tier 3**, owned by Data Platform.

{{result B1}}

### Step 2: It's not one alert

By 03:14, **{{f storm_alerts}} alerts** have fired from **{{f storm_teams}} teams** in {{f storm_minutes}} minutes. Everyone assumes their own service is the problem. The query counts, for each alerting component, how many *other* alerting components depend on it, and how many it depends on.

**Predict:** how many of the {{f storm_alerts}} are actually the cause?

{{query B1b}}

**You should see** {{f storm_cause}} `likely cause` (it has {{f cause_dependents}} alerting dependents and depends on nothing that's alerting), {{f storm_symptoms}} `symptom`s, and {{f storm_unrelated}} `unrelated` alerts that have **no link to any other alerting component in either direction**.

{{result B1b}}

**What to notice:** the cause is the quietest, lowest-tier component in the room. Among the symptoms are two nobody would connect to a cache: {{f storm_surprises}}. And {{f storm_unrelated}} of the {{f storm_alerts}} alerts are noise: `image-store` and `email-gateway` have nothing to do with this.

---

## Part 2: How bad is it? (about 12 minutes)

**03:14.** Now follow the dependencies upstream.

### Step 3: The blast radius, in rings

Which services fail if `profile-cache` goes, and how many hops from the cache are they? This is the **worst case**: it follows every `hard` dependency.

{{query B2}}

**You should see** {{f rings}} rings of {{f ring_sizes}} services, **{{f services_worst}} in all**. (The examples are the most critical in each ring.)

{{result B2}}

### Step 4: How much can we prove?

The same radius, split by what you can prove.

**Predict:** of those {{f services_worst}}, how many can you *prove* will fail?

{{query B2b}}

**You should see** three groups: **{{f services_proven}}** proven, **{{f services_assumed}}** assumed (only an unclassified link keeps them on the list), and **{{f services_degrade}}** that merely degrade.

{{result B2b}}

**What to notice:** {{f assumed_pct}}% of the "failing" list is assumption.

### Step 5: What does that mean for customers?

How many journey attempts per hour are affected, now (03:00) and as the morning builds (07:00)?

{{query B3b}}

**You should see** a **range**, not a number.

{{result B3b}}

**What to notice:** at 03:00 the answer is between **{{n att03_best}}** and **{{n att03_worst}}** attempts an hour. **A factor of about {{f range_factor}}, because of what nobody has checked.** And by 07:00 it's {{f ramp_factor}} times higher.

---

## Part 3: Why can't we tell? (about 10 minutes)

**03:25.** Something is making the answer a range. Find out what.

### Step 6: The one link worth checking

These are the dependencies on the path to the cache that **nobody ever classified**, ranked by how much sits above each.

{{query B2c}}

**You should see** {{f links_ranked}} rows. The top one is `{{f link}}`, with **{{f link_services}} services** and **{{f link_journeys}} journeys** above it. The next has {{f link2_services}} services and {{f link2_journeys}} journeys.

{{result B2c}}

**What to notice:** `seen_via` is `observed`. This link was seen in traces. **It was never declared in the catalog.**

### Step 7: Where did it come from?

{{query B6b}}

**You should see** the change that introduced it: `{{f link_change}}`, on {{f link_first_seen}}, **{{f link_months}} months ago**, with **no risk review**.

{{result B6b}}

**What to notice:** nobody did anything wrong. A team resolved group membership through the profile service, which is a perfectly normal change. It just never made it into the catalog.

### Step 8: The replay

How big was the blast radius the day *before* that change, compared with tonight? The same question, asked "as of" two dates.

**Predict:** how many journeys depended on the cache the day before?

{{query B6c}}

**You should see** the worst case grow from **{{f replay_journeys_before}} journeys to {{f replay_journeys_after}}**, and from {{f replay_services_before}} services to {{f replay_services_after}}.

{{result B6c}}

**What to notice:** one change, {{f link_months}} months ago, took the worst case from **{{f replay_journeys_before}} journeys to {{f replay_journeys_after}}**: about **{{f replay_att_factor}} times** the daily attempts at risk.

---

## Part 4: Your turn: classify the link (about 8 minutes)

**03:40.** So far you've only *read* the graph. Now change it, in your own database, and watch the answer move.

The link is `entitlements-svc -> customer-profile-svc`. Nobody knows whether it's hard or soft. You'll try both answers.

**Do these steps in order.** They write to *your* database only. At any point, Step 14 puts everything back.

### Step 9: The scoreboard, before

{{query H1}}

{{result H1}}

Write these down: **{{f journeys_worst}}** journeys down in the worst case, and **{{f journeys_proven}}** proven.

### Step 10: Decide the link is SOFT

Suppose `entitlements-svc` survives a slow profile service. This marks the link soft and recomputes the `hard` and `confirmed` flags.

{{query H2}}

### Step 11: The scoreboard again

**Predict:** how many journeys are down in the worst case now?

{{query H3}}

{{result H3}}

**What to notice:** the worst case falls to **{{f journeys_if_soft}} journeys**. Tonight looks exactly like the day before `{{f link_change}}`. *(Curious what a graph algorithm makes of that change? That's stretch challenge S12, if your database has Graph Data Science.)*

### Step 12: Now decide it's HARD

The opposite: `entitlements-svc` fails when the profile service is slow.

{{query H4}}

### Step 13: The scoreboard once more

**Predict:** how many journeys are now *proven* down?

{{query H5}}

{{result H5}}

**What to notice:** **all {{f journeys_if_hard_proven}}** are now proven. What was doubt is now fact. *One link, two answers, and nobody on the call knows which is true.*

### Step 14: Put it back

{{query H6}}

**Optional check:** run the scoreboard one more time. It should match Step 9 exactly.

{{query H7}}

**If anything looks off:** run Step 14 again. If it still looks wrong, ask a helper; they can restore your database in seconds.

---

## Part 5: What do we do? (about 5 minutes)

**03:52.** You have an answer with a range and a cause. Now act on it.

### Step 15: What changed?

Every change in the 24 hours before the page, ranked by how close it is to the cache.

{{query B8}}

**You should see** {{f changes_window}} changes, **{{f changes_in_radius}} of them in the blast radius**.

{{result B8}}

**What to notice:** the closest is `{{f change_closest}}`, a cache **TTL cut from 24 hours to 1 hour**, deployed at {{f change_closest_at}} with no risk review. The changes outside the radius are correctly ruled out.

### Step 16: What does routing cost?

Across all {{f route_total}} incidents with a recorded root cause, what happens when the ticket goes to the team that owns the root cause, compared with anywhere else?

{{query B7b}}

{{result B7b}}

**What to notice:** tickets that went to the owner took **{{f route_own_avg}} minutes** on average. Tickets routed elsewhere took **{{f route_els_avg}} minutes**, bouncing between teams **{{f route_els_re}}** times. *These incident figures are invented for the exercise, and the size of the gap is built into the data. The direction is the point.*

---

## The decision

You have, at 03:55:

1. **Data Platform:** roll back `CHG-2301`. It's the closest change, and the one you can undo.
2. **Identity & Access:** answer one question: *does `entitlements-svc` survive a slow profile service?* It moves the worst case from {{f journeys_worst}} journeys to {{f journeys_if_soft}}.
3. **Tell the other teams in the blast radius.**
4. **Monday:** classify the link, declare it, give the cache a runbook and an honest tier, and route incidents to the team that owns the cause.

**Three things to take away:**
1. **The dependency that matters isn't in the catalog.** It's in the traces, and in the graph.
2. **"We don't know" is measurable.** The graph tells you how much of the answer is assumption, and which single fact would change it most.
3. **Much of an incident's cost is routing, not fixing.**

---

## Stretch challenges (if you finish early)

Try each one first; the query and result are under each. **Keep variable-length paths short** (`*1..8` or less): everyone's database lives on the same server. **S12 and S13 need the Graph Data Science (GDS) plugin**, which not every database has; each tells you what to do if yours doesn't.

### S1: Which journeys are down?
Every journey, with its status: proven down, assumed down, or up.

<details><summary>Query and result</summary>

{{query B3}}

{{result B3}}

**{{f journeys_assumed}}** are down only if the unclassified links turn out hard. *Tap to pay* survives either way: its link to the cache is soft, with a fallback.
</details>

### S2: Three scenarios side by side
Without editing anything: journeys down in the worst case, if the link from Step 6 is soft, and proven only.

<details><summary>Query and result</summary>

{{query B2d}}

{{result B2d}}
</details>

### S3: Who do we page?

<details><summary>Query and result</summary>

{{query B4}}

{{result B4}}

**{{f radius_teams_active}} active teams** own something in the radius, and so do {{f radius_teams_disbanded}} disbanded ones. Only two have a decision to make.
</details>

### S4: Who can we not page?

<details><summary>Query and result</summary>

{{query B4b}}

{{result B4b}}

{{f unpageable_names}} are in the blast radius and their owning teams were **disbanded**.
</details>

### S5: Which other datastores are declared lower than they should be?

<details><summary>Query and result</summary>

{{query B5}}

{{result B5}}

`MISMATCH` means declared tier 2 or 3 but **proven** to be needed by 3 or more journeys. `UNRATED` means never given a tier. `REVIEW` means only unclassified links put it there. There are **{{f b5_mismatch}} mismatches**; `profile-cache` heads the list because it was declared tier {{f cache_tier}}, the lowest, and sits under {{f cache_worst}} journeys in the worst case.
</details>

### S6: The chain, link by link
Why does a journey depend on the cache? Show the path and the status of every link.

<details><summary>Query and result</summary>

{{query B6}}

{{result B6}}

*Send a wire* is proven end to end. *Log in* reaches the cache through exactly one `UNCLASSIFIED` link.
</details>

### S7: Have we been here before?

<details><summary>Query and result</summary>

{{query B7}}

{{result B7}}

`profile-cache` caused **{{f cache_incidents}}** incidents and **{{n cache_minutes}}** minutes of impact (about {{f cache_hours}} hours). They went to **{{f cache_teams}}** different teams, and **none to the team that owns it**.
</details>

### S8: What does history say about the unclassified link?

<details><summary>Query and result</summary>

{{query B7c}}

{{result B7c}}

In {{f hist_degraded}} of the {{f cache_incidents}} incidents the services above it *degraded*; in {{f hist_outages}} it was an **outage**, when the hit rate fell to **{{f outage_hit_rates}}**. Tonight it's **31% and falling**.
</details>

### S9: Are we covered at 3 a.m.?

<details><summary>Query and result</summary>

{{query B9}}

{{result B9}}
</details>

### S10: What do the numbers say?
PageRank over the hard dependencies, computed ahead of time, independent of anything declared.

<details><summary>Query and result</summary>

{{query B10}}

{{result B10}}

`{{f pr_top}}` ranks **first**, above `{{f pr_second}}`; `profile-cache`, declared tier {{f cache_tier}}, is number {{f pr_cache_rank}}.
</details>

### S11: Is there anything else in here?
This story was about one cache. But a graph this size can hold more than one problem. **Is there another hotspot hiding in it that this guide has never mentioned?** One person in the room will find it first.

<details><summary>Hint 1: what is in the graph?</summary>

Look at the labels. Does every kind of thing in this database appear in your guide?

{{query B11a}}

{{result B11a}}

One of those labels has not come up once today.
</details>

<details><summary>Hint 2 and solution</summary>

Take a closer look at the label no one mentioned. Which of them is about to expire, and what depends on it?

{{query B11b}}

{{result B11b}}

`{{f egg_cert}}` expires in **{{f egg_days}} days**. It does **not** renew itself. Its owner, **Shared Services**, was disbanded. It sits under **{{f egg_services}} services** owned by **{{f egg_teams}} teams**, and **{{f egg_journeys}} of the {{f journeys}} customer journeys** touch one of them. It was last rotated on {{f egg_rotated}}, by hand, the morning it expired and took the estate down for {{f egg_outage_hours}} hours. The other certificates on the list are decoys: they expire soon but renew themselves, or matter little.

*A different kind of hidden shared dependency, and an eight-day fuse instead of a 3 a.m. page.*
</details>

### S12: Run the algorithm yourself, then change the answer
**Needs the Graph Data Science (GDS) plugin.** If your database doesn't have it, this stops with an error such as *There is no procedure with the name `gds.graph.drop` registered*. Nothing was changed; skip S12 and S13. (If the error says you are *not allowed* to run it, tell a helper.)

S10 read a score that was worked out in advance. This runs **PageRank now**, over the hard dependencies as they are at this moment: it builds a temporary in-memory copy of them, runs the algorithm, and removes the copy. It writes nothing to your database. It shows the top five, plus the three components the story is about.

<details><summary>Query and result</summary>

{{query G1}}

{{result G1}}

`live_pagerank` and `precomputed` agree: the stored property is the same calculation, done earlier. `profile-cache`, declared tier {{f cache_tier}}, ranks **{{f pr_live_cache_rank}}**.

**Now change the graph and run it again.** Run **Step 10** (mark the link soft), then run this query once more:

{{result G1s}}

`customer-profile-svc` falls from rank 1 to **{{f pr_soft_profile_rank}}** (score {{f pr_live_profile_score}} to {{f pr_soft_profile_score}}) and `profile-cache` from rank {{f pr_live_cache_rank}} to **{{f pr_soft_cache_rank}}** ({{f pr_live_cache_score}} to {{f pr_soft_cache_score}}). The **`precomputed` column has not moved**: a stored score is a snapshot of the graph as it was when it was calculated. If you mark the link **hard** (Step 12) instead, nothing changes, because the worst case already assumed it was hard.

**Put it back with Step 14** when you are done.
</details>

### S13: Does the org chart match the dependency map?
**Needs GDS**, like S12. *Louvain* finds groups of components that depend on each other more than on the rest of the estate, ignoring direction. For each group this shows how many **teams** own its members, which team owns the most, and how many belong to the team that owns the cache.

<details><summary>Query and result</summary>

{{query G2}}

{{result G2}}

The group that holds `profile-cache` has **{{f comm_cache_components}} components owned by {{f comm_cache_teams}} teams**. {{f comm_cache_biggest}} owns the most of them ({{f comm_cache_biggest_owns}}); {{f cause_owner}}, which owns the cache, owns **{{f comm_cache_owner_owns}}**. It is the finding from S7 seen from another side: the things that fail together are not inside one team, so a ticket for one of them lands in the wrong place.

*The group sizes are repeatable here, but Louvain is a heuristic: a different version of GDS can split the smaller groups slightly differently. The group numbers in S10's `cluster` column were computed on another version for that reason.*
</details>

---

## If something goes wrong

| What you see | What to do |
|---|---|
| Every query returns **no rows**, or the readiness check shows **0 components** | You're on the wrong database. Raise your hand; don't try to fix it |
| An error saying something **"is not allowed"** on database `neo4j`, or **"Database not found" / access denied** | Your login opened the wrong database. Raise your hand |
| **Syntax error** | Part of the query was probably missed when copying. Copy the whole block again, from the first line to the `;` |
| A query **keeps spinning** | Click the stop button on its frame. Lab queries finish in under a second; a slow one is usually an edited query with a long `*` path |
| **Your numbers differ from the guide** after Part 4 | Run Step 14 again |
| **Your data looks deleted or changed** | Raise your hand. We can restore your database in seconds |

---

## After the session

- **Take it with you.** The repository (or zip) from your pre-event email has this guide, every query, and the graph. `graph/load.cypher` rebuilds the whole lab on your own Neo4j 5.26 or later; instructions are at the top of that file.
- **Learn more Cypher and graph data science** at [Neo4j GraphAcademy](https://graphacademy.neo4j.com), which has free, self-paced courses.

### Glossary
| Term | Meaning |
|---|---|
| **Blast radius** | Everything that stops working, or gets worse, if one component fails |
| **Journey** | A thing customers do (Log in, Pay a bill). Each needs several services |
| **Attempt** | One customer trying one journey. Two journeys by one person are two attempts |
| **Tier** | How critical a component is. 1 = customer-facing critical, 3 = can wait until morning |
| **Hard / soft / unclassified** | A dependency the caller fails without / one it can work around / one nobody ever decided |
| **Proven vs assumed** | Down because every link is a known hard dependency / down only because an unclassified link is assumed hard |
| **Hop** | One step along a dependency |
| **Hit rate** | The share of cache lookups answered from the cache. When it falls, the database behind it takes the load |
| **TTL** | How long a cache entry lives before it expires |
| **p99** | The latency that 99% of requests beat. A measure of the slow tail |
| **Runbook** | Written steps for handling a known failure |
| **Root cause** | The component that actually failed, as opposed to those that merely showed symptoms |
| **PageRank** | A score for how much of a graph leans on each node, counting indirect reliance. Here, how much of the estate depends on a component, directly or through others |
| **Community** | A group of nodes more connected to each other than to the rest, found by an algorithm (Louvain). Here, components that depend on each other |
