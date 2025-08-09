# ---- Base image ------------------------------------------------------------
FROM node:20-alpine3.21 AS base

# ---- Versions / env vars ---------------------------------------------------
ENV CODE_SERVER_VERSION=4.100.2 \
    SHELL=/bin/bash \
    PYTHONUNBUFFERED=1 \
    PRISMA_CLI_BINARY_TARGETS=linux-musl-openssl-3.0.x  \
    PRISMA_CLIENT_ENGINE_TYPE=binary \
    OPENSSL_ROOT_DIR=/usr
ENV DEBIAN_FRONTEND=noninteractive


# ---- System packages, PostgreSQL, uv, pgweb --------------------------------
RUN apk update && apk upgrade
RUN apk add bash git alpine-sdk quilt krb5-dev libx11-dev \
      libxkbfile-dev libstdc++ libc6-compat libsecret-dev jq rsync
RUN apk add --no-cache \
    bash curl git openssh build-base \
    python3=~3.12 py3-pip uv py3-uv \
    postgresql postgresql-client \
    libc6-compat libstdc++ gcompat \
    krb5-dev unzip make g++ \
    linux-headers util-linux procps coreutils \
    ca-certificates \
    openssl3 openssl3-dev \
    vim \
    && ln -sf /usr/lib/libssl.so.3 /usr/lib/libssl.so \
    && ln -sf /usr/lib/libcrypto.so.3 /usr/lib/libcrypto.so



# Initialize PostgreSQL
RUN mkdir -p /run/postgresql /var/lib/postgresql/data \
    && chown  -R  postgres:postgres /run/postgresql /var/lib/postgresql \
    && su - postgres -c "initdb --auth=md5 --username=postgres --pwfile=<(echo test) /var/lib/postgresql/data"

# Install pgweb
RUN curl -L --output /tmp/pgweb.zip \
    https://github.com/sosedoff/pgweb/releases/latest/download/pgweb_linux_amd64.zip \
    && unzip /tmp/pgweb.zip -d /tmp \
    && mv /tmp/pgweb_linux_amd64 /usr/local/bin/pgweb \
    && chmod +x /usr/local/bin/pgweb \
    && rm /tmp/pgweb.zip 

# Install bun
RUN npm install -g bun@1.2.14

# Config next js template
RUN mkdir -p /template \
    && bun create next-app /template/nextjs_template --typescript --tailwind --eslint --app --src-dir --turbopack --import-alias "@/*" --use-bun --yes --force \
    && cd /template/nextjs_template \
    && bunx shadcn@latest init --base-color neutral --yes \
    && bunx shadcn@latest add accordion alert alert-dialog aspect-ratio avatar badge breadcrumb button calendar card carousel chart checkbox collapsible command context-menu dialog drawer dropdown-menu form hover-card input input-otp label menubar navigation-menu pagination popover progress radio-group resizable scroll-area select separator sheet sidebar skeleton slider sonner switch table tabs textarea toggle toggle-group tooltip --yes 


COPY template/vite-template /template/vite-template
RUN cd /template/vite-template \
    && bun install

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh
RUN mkdir -p ~/.config/code-server

# ---- Workspace mount -------------------------------------------------------
WORKDIR /workspace             

# ---- Ports -----------------------------------------------------------------           
EXPOSE 1-65535/tcp 1-65535/udp  

# ---- Entrypoint ------------------------------------------------------------
ENTRYPOINT ["/usr/local/bin/startup.sh"]