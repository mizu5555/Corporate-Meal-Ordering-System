FROM postgres:16-alpine
# Migrations are applied exclusively by the app at startup via run_migrations()
# (tracked in schema_migrations). The initdb path was removed so migrations are
# never applied twice on a fresh volume (see #49).
