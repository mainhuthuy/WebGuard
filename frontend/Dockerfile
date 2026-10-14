# ============================================================================
# Frontend Dockerfile — multi-stage build
#
# Stage "build": compiles the app with Vite. `npm run build` runs `tsc -b`
#   first — a build with type errors never produces dist/, so this stage
#   fails loudly instead of shipping broken output.
# Stage "production": nginx:alpine serving ONLY the static dist/ output —
#   no Node, no node_modules, no source — running fully unprivileged
#   (mirrors the backend's non-root setup, see backend/Dockerfile).
# Stage "dev": independent of the two above; used only by
#   docker-compose.dev.yml, which bind-mounts src/ over it for hot reload.
# ============================================================================

FROM node:22-alpine AS build

WORKDIR /app

# Dependencies are locked with npm (package-lock.json) — `npm ci` installs
# exactly what's locked and fails instead of silently drifting from it.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:alpine AS production

# Pull in Alpine security patches published after the nginx base image was built
# (the Trivy gate fails on HIGH/CRITICAL CVEs that already have a fix).
RUN apk upgrade --no-cache

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Lives outside conf.d/ on purpose: nginx's own base config does
# `include /etc/nginx/conf.d/*.conf;`, which expects each file there to be a
# full server block — a bare directives-only snippet doesn't belong in that
# directory. default.conf pulls this in explicitly via `include` instead
# (see nginx.conf for why it can't just sit at the server{} level).
COPY security-headers.conf /etc/nginx/security-headers.conf

# Run fully unprivileged. nginx:alpine already creates an `nginx` user for
# its worker processes; the master process only needs root by default to
# bind port 80 and own the pidfile — nginx.conf listens on 8080 instead, so
# neither reason applies here.
RUN touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/cache/nginx /var/run/nginx.pid /usr/share/nginx/html
USER nginx

EXPOSE 8080

# busybox wget ships in nginx:alpine already — no extra package needed.
# Uses 127.0.0.1, not localhost: this container's /etc/hosts resolves "localhost" to
# ::1 first, and nginx (see nginx.conf) only listens on 0.0.0.0:8080 (IPv4) — wget would
# try the IPv6 address and get connection-refused before ever trying IPv4.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]


# Development stage
FROM node:22-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
