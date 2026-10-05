# 3 a.m. Blast Radius

> **03:07.** Your pager goes off. `profile-cache p99 latency 4.2s, hit rate 31% and falling.`
> It's a cache. Declared tier 3. It can probably wait until morning.
>
> **It can't. The graph is how you find out why, and what to do about it.**

*Everything here is fictional: the bank, the teams, the services, the incidents, the customer counts. Nothing describes any real institution's architecture. Say so in the first minute.*

**This document contains spoilers, including the easter egg. It is for the people delivering the session.**

---

## The premise

You're the on-call engineer at a large retail bank. A Redis cache is degrading, and the page says tier 3. Over the next hour you discover that:

- the "cache" sits under **up to {{f journeys_worst}} of {{f journeys}} customer journeys**, through a dependency **nobody ever declared** and **nobody ever classified** as hard or soft;
- you **cannot tell** whether it breaks logins or merely slows them, and **the history says both**;
- the same cache has already caused **{{f cache_incidents}} incidents**, filed to **{{f cache_teams}} different teams**, and **never once to the team that owns it**;
- and the most useful thing you can do tonight is not a fix. It's **one phone call**.

**The line to leave them with:** *"The architecture diagram shows what we intended. The graph shows what we built, and how much of it nobody has checked."*

---

## The cast

| | |
|---|---|
| **You** | The on-call engineer. It's 3 a.m. You have until the morning ramp |
| **`profile-cache`** | A Redis cache. Owner: {{f cause_owner}}. Declared **tier {{f cache_tier}}**, "can wait until morning" |
| **`{{f link}}`** | The link. First seen {{f link_first_seen}}. In traces, **never in the catalog**. Hard or soft: **unknown** |
| **The bank** | {{f services}} services, {{f datastores}} datastores, {{f teams}} teams, {{f journeys}} customer journeys |
| **The clock** | Traffic is roughly **{{f ramp_factor}} times higher** by 07:00 |
| **A journey** | A thing customers do: *Log in*, *Pay a bill*, *Send a wire*. Each is backed by several services. "{{f journeys_worst}} journeys down" means {{f journeys_worst}} of those {{f journeys}} activities stop working. Customer figures count **attempts**: someone who logs in and then checks a balance is two |

---

## The story, in six scenes

Each scene is one question the on-call engineer asks, and the one thing the graph shows that nothing else could. Query ids (B…) are in [queries/demo-queries.cypher](queries/demo-queries.cypher). The clock is the story's, not the lab's: the lab runs in about 45 minutes.

### Scene 1. 03:07: "What is this, and is it alone?" `B0 B1 B1b`
The page is a tier-3 cache owned by {{f cause_owner}}. Then the others arrive: **{{f storm_alerts}} alerts in {{f storm_minutes}} minutes, from {{f storm_teams}} teams**. Everyone assumes their own service is the problem.

**The graph:** for each alerting component, count the other alerting components that depend on it, and the ones it depends on. `{{f cause_name}}` has **{{f cause_dependents}} alerting dependents and depends on nothing that's alerting**: the likely cause. **{{f storm_symptoms}}** alerts each depend on something that's alerting: symptoms, including two nobody would link to a cache ({{f storm_surprises}}). **{{f storm_unrelated}}** have **no link in either direction**: unrelated, and the graph says so.

> **The beat.** {{f storm_alerts}} alerts, one cause, and it's the quietest, lowest-tier component in the room. *Pause and ask: who is looking at the wrong alert right now?*

### Scene 2. 03:14: "How bad is it?" `B2 B2b B3 B3b`
Follow the dependencies upstream and count. **{{f services_worst}} services fail in the worst case, in {{f rings}} rings out to {{f max_hops}} hops**: {{f ring_sizes}}.

Then the honest question: how many can you *prove*?

| | services |
|---|---|
| **Fail, proven**: every link on some path is a known hard dependency | {{f services_proven}} |
| **Fail, assumed**: only an unclassified link keeps them on the list | {{f services_assumed}} |
| **Degrade only**: reachable over soft links, with fallbacks | {{f services_degrade}} |

So customers get a **range**, not a number:

| | journeys down | attempts/hour at 03:00 | at 07:00 |
|---|---|---|---|
| Best case, proven only | {{f journeys_proven}} of {{f journeys}} | {{n att03_best}} | {{n att07_best}} |
| Worst case, assume the unknowns | **{{f journeys_worst}} of {{f journeys}}** | **{{n att03_worst}}** | **{{n att07_worst}}** |

*Tap to pay* survives either way. Its link to the cache is soft, with a fallback. It's the one place someone designed for this.

> **The beat.** Your answer to "how many customers?" is **between {{n att03_best}} and {{n att03_worst}} attempts an hour**: a factor of about **{{f range_factor}}**, because of what nobody has checked. *And by seven the numbers are {{f ramp_factor}} times worse.*

### Scene 3. 03:25: "Why can't we tell?" `B2c B2d B6 B6b B6c`, and hands-on `H1 to H7`
Exactly one unclassified link carries most of the doubt: **`{{f link}}`**, with **{{f link_services}} services** and **{{f link_journeys}} journeys** sitting above it. The next-largest has {{f link2_services}} and {{f link2_journeys}}. *Log in* reaches the cache through that link, and nothing else on its chain is uncertain.

Where did it come from? **`{{f link_change}}`, on {{f link_first_seen}}**: a change that made entitlements resolve group membership through the profile service. It was **seen in traces, never declared, and had no risk review**. It has been in production for **{{f link_months}} months**.

**The replay (B6c).** Ask the same question as of the day *before* `{{f link_change}}`, using only the dependencies that existed then:

| | services failing | journeys down | attempts/day |
|---|---|---|---|
| {{f replay_date}}, the day before | {{f replay_services_before}} | {{f replay_journeys_before}} | {{n replay_att_before}} |
| Tonight | {{f replay_services_after}} | **{{f replay_journeys_after}}** | **{{n replay_att_after}}** |

One change, no review, and the blast radius went from **{{f replay_journeys_before}} journeys to {{f replay_journeys_after}}**: about **{{f replay_att_factor}} times** the daily attempts at risk.

> **The beat.** One undeclared call, {{f link_months}} months ago, turned a tier-3 cache into part of the foundation of login. *Nobody did anything wrong. Everybody did something normal.*

**Your turn: classify the link (H1 to H7).** So far you have only read the graph. Now change it, in your own database, and watch the answer move:

| You decide the link is… | journeys down: worst case | journeys down: proven |
|---|---|---|
| **unclassified** (today) | {{f journeys_worst}} | {{f journeys_proven}} |
| **soft**: entitlements survives a slow profile service | **{{f journeys_if_soft}}** | {{f journeys_proven}} |
| **hard**: entitlements fails when it is slow | {{f journeys_worst}} | **{{f journeys_if_hard_proven}}** |

If it's soft, tonight looks exactly like the day before `{{f link_change}}`. If it's hard, the doubt becomes fact. *One link, two answers, and nobody on the call knows which is true.* A final statement puts everything back.

### Scene 4. 03:40: "Have we been here before?" `B5 B7 B7b B7c B10`
The graph checks every datastore: how many journeys depend on it, against the tier it was declared at. **{{f b5_mismatch}} are flagged `MISMATCH`**, and **`profile-cache`** heads the list: declared tier {{f cache_tier}}, **{{f cache_proven}} journeys proven, {{f cache_worst}} in the worst case**. (`{{f b5_second}}` is a smaller version of the same problem: declared tier {{f b5_second_tier}}, {{f b5_second_journeys}} journeys proven.) And PageRank over the hard dependencies, computed independently, ranks `{{f pr_top}}` **first**, above `{{f pr_second}}`; `profile-cache` is number {{f pr_cache_rank}}. *(With GDS, run live as stretch `G1`, it also answers back: mark the unclassified link soft and `profile-cache` falls from {{f pr_live_cache_rank}} to {{f pr_soft_cache_rank}}, while the stored score stays put.)*

Then the history. The cache has caused **{{f cache_incidents}} incidents** since that change: **{{n cache_minutes}} minutes** (about {{f cache_hours}} hours), filed to **{{f cache_teams}} different teams**, **none to {{f cause_owner}}**. Across the {{f route_total}} incidents with a recorded root cause, tickets routed to the owner of the root cause took **{{f route_own_avg}} minutes on average**; tickets routed elsewhere took **{{f route_els_avg}}**, bouncing between teams **{{f route_els_re}}** times.

And the evidence on the unknown link? In {{f hist_degraded}} of the {{f cache_incidents}} incidents the services above it *degraded* (logins slow, but succeeded). {{f hist_outages}} were **outages**, when the hit rate fell to **{{f outage_hit_rates}}**. Tonight it's **31% and falling**.

> **The beat.** The link has answered both ways before. *The question isn't whether the cache breaks login. It's how far it falls.*

### Scene 5. 03:52: "What changed, and who do I wake up?" `B4 B4b B8 B9`
{{f changes_window}} changes in the last 24 hours; **{{f changes_in_radius}} are in the blast radius**, ranked by distance. The closest: **`{{f change_closest}}`, cache TTL cut from 24 hours to one, at {{f change_closest_at}}, with no risk review**. The rest are correctly ruled out.

Who to page? **{{f radius_teams_active}} active teams** own something in the radius, and so do {{f radius_teams_disbanded}} that have been disbanded: {{f unpageable_names}} belong to teams that no longer exist. Nobody can be paged for them.

Are you covered? Of {{f radius_components}} components in the radius, **{{f rb_none}} have no runbook**, {{f rb_stale}} have a stale one, and {{f rb_current}} have a current one. The cache has none.

> **The beat.** {{f radius_teams_active}} teams in the radius, and only two of them have a decision to make.

### Scene 6. 04:05: The decision
1. **{{f cause_owner}}:** roll back `{{f change_closest}}`. It's the closest change, and the one you can undo.
2. **Identity & Access:** answer one question. *Does `entitlements-svc` survive a slow profile service?* It moves the worst case from {{f journeys_worst}} journeys to {{f journeys_if_soft}}.
3. **Tell the other teams in the blast radius**, and know that some components in it have no one to tell.
4. **Monday:** classify the link. Declare it. Give the cache a runbook and an honest tier. Route incidents to the team that owns the cause.

---

## The easter egg (spoiler)

There is a **second hotspot** that the story never mentions. It is deliberately not on any step of the lab. Attendees who finish early can find it as **stretch challenge S11**, with two hints.

**What it is.** A `:Certificate` label that appears in the database sidebar and in no part of the guide. One certificate, **`{{f egg_cert}}`**:

- expires in **{{f egg_days}} days** (2026-10-08) and **does not renew itself**;
- is owned by **Shared Services, a team disbanded in 2025**;
- is used by **{{f egg_services}} services** across **{{f egg_teams}} teams**, touching **{{f egg_journeys}} of the {{f journeys}} journeys**, including *Tap to pay*, which survives the cache failure but not this;
- was last rotated on {{f egg_rotated}}, by hand, the morning it expired and took the estate down for **{{f egg_outage_hours}} hours** (`INC-0990`).

**Decoys.** {{f egg_decoys}} other certificates also expire within weeks, so a naive "expiring soon" list is not enough. {{f egg_decoys_renewing}} renew themselves; the other is a Wi-Fi certificate used by two minor services. The loudest decoy, `{{f egg_decoy_name}}`, touches {{f egg_decoy_journeys}} of the {{f journeys}} journeys, but renews itself. Only the wildcard combines *no renewal*, *no owner*, and *everything depends on it*.

**How it is found.** `B11a` lists every label with its count; the unfamiliar one is `Certificate`. `B11b` ranks expiring certificates by reach. The lesson is the same as the cache's, in a different dimension: **the dependency that matters isn't a call between services, it's a shared secret nobody owns.**

**Why it's worth keeping quiet.** It's a reward for curiosity, and it shows that a graph holds more than the story the presenter chose. Don't bring it up first. If someone finds it, give them the room's attention for a minute.

---

## What the room should walk away with

1. **The dependency that matters isn't in the catalog.** It's in the traces, and in the graph.
2. **"We don't know" is measurable.** The graph doesn't only give an answer; it says how much of the answer is assumption, and which single fact would change it most.
3. **Much of an incident's cost is routing, not fixing.** The graph shows who owns the cause.

---

## Why it works as a lab

- **No domain knowledge needed.** Engineers already know services, caches and runbooks.
- **Every query is a question the on-call person actually asks.**
- **The aha has layers.** Anyone gets "a cache has up to {{f journeys_worst}} journeys above it". The sharper people get "and we don't know whether that's true", which is the better lesson.
- **The mess is the point.** Unclassified, undeclared, stale, orphaned, duplicated: any attendee will recognise their own estate in at least one of them.
- **It scales with the audience.** Scenes 1 to 3 for everyone; the stretch challenges, and the easter egg, for people who want more.

---

## Be honest about what's planted

The graph is generated, and five things are **deliberately planted** to make the story work:
1. The unclassified `{{f link}}` link and its history.
2. {{f cache_incidents}} `profile-cache` incidents, all misrouted, with outages at low hit rates.
3. The **misrouting penalty** in Scene 4. It's built into the generator, not discovered. Its direction is plausible; its size is invented.
4. The alert storm and tonight's changes.
5. The easter egg: the wildcard certificate and its decoys.

The other ~{{f incidents}} incidents, ~{{f changes}} changes, observability edges and decommissioned services are seeded background. **Say so before the room asks.**

## What this is not

- **Not real data**, and not Chase's architecture.
- **Not a tool comparison.** It doesn't argue Neo4j beats a service catalog. It shows what a connected question looks like.
- **Not an architecture review.** No claims about how a bank *should* build things.

## Limits

- **Real dependency data is worse:** several sources that disagree, edges missing entirely, names that don't match.
- **Classifying a link is still someone's job.** The graph shows where the judgement is missing; it can't make it.
- **{{n nodes}} nodes is a lab, not a bank.** Enough to explore, and every lab query still finishes in well under a second.

---

## Where it goes next

**Built:** the 45-minute lab and its attendee guide ([LAB-GUIDE.pdf](LAB-GUIDE.pdf)), the facilitator guide ([FACILITATOR-GUIDE.pdf](FACILITATOR-GUIDE.pdf)), the readiness check, the time replay (B6c), the hands-on classify step (H1 to H7), the easter egg, rehearsal databases (`make rehearsal`), two live GDS stretch steps (`G1`, `G2`), and eight Bloom search phrases ([BLOOM-GUIDE.md](BLOOM-GUIDE.md); the Cypher is tested, Bloom itself is not). **Not built:** a loader for all 60 attendee databases, fill-in-the-blank variants, and attendee-facing Bloom steps. Nothing has yet been run with real people or on the JPMC sandbox.
