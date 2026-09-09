#!/bin/bash
# Runs once, automatically, when the postgres container's data volume is first
# initialized (standard postgres image behavior for anything mounted at
# /docker-entrypoint-initdb.d/). POSTGRES_DB only creates one database, but
# per PLANNING.md §5/§13 this one Postgres server hosts 5 independent logical
# databases (one per standalone service, plus the MCP server's own) — this
# script creates the other four alongside the one POSTGRES_DB already made.
set -e

for db in smartspot360 captivator360 maestro360 mcp_server; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE $db;
EOSQL
done
