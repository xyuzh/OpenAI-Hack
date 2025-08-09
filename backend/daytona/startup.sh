#!/bin/bash
set -e

source ~/.bashrc

export POSTGRES_PORT=5433

export PG_VERSION=$(ls /usr/lib/postgresql/ | head -1)

# Start PostgreSQL
pg_ctlcluster "$PG_VERSION" main start

# Wait for PostgreSQL to be ready
until pg_isready -h localhost -p ${POSTGRES_PORT} -U postgres; do
    sleep 1
done

nohup code-server \
    --bind-addr 0.0.0.0:8080 \
    --auth none \
    --disable-telemetry \
    --disable-update-check \
    /workspace  > code-server.log 2>&1 & disown
    
# Start pgweb
exec pgweb --bind=0.0.0.0 --listen=8081 --url="postgresql://postgres:test@localhost:${POSTGRES_PORT}/postgres"
