# ---- Base image ------------------------------------------------------------
FROM ubuntu:22.04

# ---- Versions / env vars ---------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

ENV PGDATA=/var/lib/postgresql/data
ENV POSTGRES_USER=test
ENV POSTGRES_DB=postgres
ENV POSTGRES_PORT=5433

# ---- System packages, PostgreSQL, uv, pgweb --------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash git build-essential quilt \
    jq rsync lsof \
    curl openssh-client \
    python3 python3-pip python3-venv \
    postgresql postgresql-client postgresql-contrib \ 
    unzip make g++ \
    procps coreutils \
    ca-certificates \
    vim tree \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*


# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Initialize PostgreSQL - Alternative approach using pg_createcluster
RUN service postgresql stop || true && \
    rm -rf /var/lib/postgresql/*/main && \
    rm -rf ${PGDATA} && \
    mkdir -p ${PGDATA} && \
    chown -R postgres:postgres ${PGDATA}

# Use pg_createcluster (Debian/Ubuntu standard way)
RUN PG_VERSION=$(ls /usr/lib/postgresql/ | head -1) && \
    pg_dropcluster --stop ${PG_VERSION} main || true 

RUN PG_VERSION=$(ls /usr/lib/postgresql/ | head -1) && \
    pg_createcluster ${PG_VERSION} main --start --datadir=${PGDATA} --port=${POSTGRES_PORT} && \
    su - postgres -c "psql -c \"ALTER USER postgres PASSWORD 'test';\"" && \
    until pg_isready -h localhost -p ${POSTGRES_PORT} -U postgres; do \
        sleep 1; \
    done


# Install pgweb
RUN curl -L --output /tmp/pgweb.zip \
    https://github.com/sosedoff/pgweb/releases/latest/download/pgweb_linux_amd64.zip \
    && unzip /tmp/pgweb.zip -d /tmp \
    && mv /tmp/pgweb_linux_amd64 /usr/local/bin/pgweb \
    && chmod +x /usr/local/bin/pgweb \
    && rm /tmp/pgweb.zip 

# Install bun
RUN npm install -g bun@1.2.14

COPY template/ /template/
RUN cd /template/vite-template && bun install
RUN cd /template/nextjs_template && bun install

# Copy scripts as executable commands to /usr/local/bin
COPY script/glob.sh /usr/local/bin/glob
COPY script/multi_edit.sh /usr/local/bin/multi_edit
RUN chmod +x /usr/local/bin/glob /usr/local/bin/multi_edit

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Create a user for code-server
RUN useradd -m coder

# Create startup script
COPY startup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/startup.sh

# ---- Workspace mount -------------------------------------------------------
WORKDIR /workspace             

# ---- Ports -----------------------------------------------------------------           
EXPOSE 1-65535/tcp 1-65535/udp  

ENTRYPOINT ["/usr/local/bin/startup.sh"]