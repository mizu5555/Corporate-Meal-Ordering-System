FROM postgres:16-alpine
# Only top-level .sql files run as init scripts; the draft/ subdir is intentionally skipped.
COPY backend/db/migrations/*.sql /docker-entrypoint-initdb.d/
