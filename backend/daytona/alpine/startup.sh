#!/bin/bash
set -e

# Start PostgreSQL
su - postgres -c 'pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/logfile start'

nohup code-server \
    --bind-addr 0.0.0.0:8080 \
    --auth none \
    --disable-telemetry \
    --disable-update-check \
    /workspace  > code-server.log 2>&1 & disown

# Start pgweb
exec pgweb --bind=0.0.0.0 --listen=8081 --url="postgresql://postgres:test@localhost:5433/postgres"