// Provisioning for Neo4j Enterprise Studio, run once against the `system`
// database by the `nes-init` service before Studio starts.
//
// Studio persists its assets (saved queries, dashboards, Perspectives, sharing
// metadata) in a dedicated database, reached with a dedicated service account.
// The database must exist when Studio boots, and Studio reconciles its own
// constraints and indexes on every startup, so the account needs schema
// privileges as well as read/write. The `architect` built-in role covers it.
//
// Idempotent: safe to re-run, which matters because compose runs it on every
// `up`. Parameter: $toolsPassword (passed by compose from NES_SERVICE_PASSWORD).

CREATE DATABASE `tools-storage` IF NOT EXISTS WAIT;

CREATE USER `tools_service` IF NOT EXISTS
  SET PASSWORD $toolsPassword
  SET PASSWORD CHANGE NOT REQUIRED;

GRANT ROLE architect TO `tools_service`;

// Studio inspects schema and DBMS metadata to build Perspectives and offer
// completions, so plain readers need these beyond ordinary MATCH access. Without
// them Explore silently shows no schema.
GRANT SHOW CONSTRAINTS ON DATABASES * TO reader;
GRANT SHOW INDEXES ON DATABASES * TO reader;
GRANT SHOW ROLE ON DBMS TO reader;
GRANT SHOW USER ON DBMS TO reader;
