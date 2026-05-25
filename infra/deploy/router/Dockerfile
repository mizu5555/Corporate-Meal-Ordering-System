# Shared internal deploy router. The Caddyfile is baked into the image rather
# than bind-mounted, so the container has NO host-path dependency: it survives
# host reboots, docker daemon restarts, and /tmp or Jenkins-workspace cleanup.
# (A bind mount from an ephemeral path is what previously killed this container
# with exit 127 — Docker auto-created the missing source as a directory and the
# mount onto /etc/caddy/Caddyfile failed.)
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
