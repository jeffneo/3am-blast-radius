// ===========================================================================
//  Readiness check
//
//  Run in Neo4j Browser before the session (and again in the first minute).
//
//  Expected:  your_database is YOUR lab database (not `neo4j`), and components and
//             incidents are both well above zero (the guide shows the exact figures).
//  If components is 0, or you get an error saying something "is not allowed"
//  on database `neo4j`, your login opened the wrong database. Tell the
//  organisers; do not try to fix it yourself.
//
//  It also leaves a small :Checkin node behind, which is how the organisers
//  can tell who is ready without asking.
// ===========================================================================

// R0 - Am I ready?
CALL db.info() YIELD name
CREATE (:Checkin {at: datetime()})
RETURN name AS your_database,
       COUNT { (:Component) } AS components,
       COUNT { (:Incident) } AS incidents,
       'You are ready' AS status;
