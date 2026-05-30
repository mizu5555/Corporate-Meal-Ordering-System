# Corporate Meal Ordering System

NYCU 2026 Spring — Cloud Native Development and Best Practice.

A cloud-native corporate meal ordering system: employees pre-order meals,
vendors manage their own shops, and a committee/admin oversees operations.
Built with a layered FastAPI backend, a React + Vite frontend served through
nginx, PostgreSQL, a Caddy HTTPS gateway, Docker Compose for local dev,
GitHub Actions CI with images published to GHCR, Jenkins-based delivery, and a
Prometheus / Grafana / Loki observability stack.

## Features

- **Employee ordering** — daily meal pre-orders with per-day quota, pickup /
  facility routing, and meal recommendations (popular-by-sales and random).
- **Vendor self-service** — menu CRUD, menu photos, category management, shop
  profile, and sales history for the logged-in vendor.
- **Admin / committee** — vendor application review, an operations dashboard
  (orders, revenue, vendor ranking, facility distribution), monthly
  billing/statements, multi-facility management, and an audit-log viewer.
- **Platform** — header/JWT-based RBAC, an audit trail for state-changing
  actions, structured JSON logging, Prometheus metrics, and alert rules.

## Architecture

Strict layered backend — routes never touch repositories directly:

```text
routes/  →  services/  →  repositories/  →  (in-memory or PostgreSQL)
               ↑
         schemas/ (Pydantic)   models/ (domain types)   core/ (config, RBAC)
```

- **RBAC** (`backend/core/rbac.py`): roles `admin`, `employee`,
  `vendor_manager`, `committee_reviewer`. Routes guard with
  `Depends(require_roles(...))`.
- **Audit trail**: state-changing services record to the `audit_logs` table
  alongside their domain repository.
- **Repositories** ship in-memory and PostgreSQL implementations, selected by
  configuration so tests can run without a database.
- **Gateway**: Caddy terminates HTTPS and routes `/health`, `/docs`,
  `/openapi.json`, and the backend API prefixes to the backend; everything else
  to the frontend.

## Project Structure

```text
project-root/
├── frontend/                 # React + Vite app (nginx-served in prod)
├── backend/
│   ├── core/                 # config, RBAC, security, observability
│   ├── routes/               # FastAPI routers
│   ├── services/             # business logic
│   ├── repositories/         # data access (in-memory + Postgres)
│   ├── schemas/              # Pydantic request/response models
│   ├── models/               # domain types
│   ├── db/migrations/        # SQL migrations (+ seeds/)
│   ├── tests/
│   └── main.py               # create_app()
├── infra/
│   ├── caddy/                # HTTPS gateway image
│   ├── deploy/               # deploy compose overlays, router, backup
│   └── monitoring/           # Grafana dashboards, Prometheus/Loki, alerts
├── .github/workflows/        # GitHub Actions (CI + image publish)
├── docker-compose.yml        # base stack
├── docker-compose.dev.yml    # local hot-reload overlay
├── .env.example
├── requirements.txt
└── README.md
```

## Getting Started

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Update local secrets in `.env` (e.g. `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`).

3. Start the full local stack (with hot reload):

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

Main HTTPS entrypoint:

- App: https://localhost
- Backend health check: https://localhost/health
- API docs: https://localhost/docs

Caddy uses a local internal TLS certificate for development; your browser may
ask you to trust it the first time.

4. Optional backend-only local setup:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Optional frontend local development with Vite:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Services

- HTTPS gateway: https://localhost
- Frontend direct dev port: http://localhost:3000
- Backend direct dev port: http://localhost:8000
- PostgreSQL: localhost:5432

## Database Migrations

SQL migrations live in `backend/db/migrations/` and are applied by the backend
startup hook when `DATABASE_URL` is configured; applied filenames are tracked in
the `schema_migrations` table. In local Docker Compose, PostgreSQL starts first
and the backend applies pending migrations automatically. Optional demo data
(`backend/db/seeds/`) can be enabled via `SEED_DEMO_DATA` for non-production
environments.

## Observability

- Backend exposes Prometheus metrics at `/metrics` and structured JSON logs to
  stdout (shipped to Loki).
- Grafana dashboards, Prometheus scrape config, Loki, and alert rules live under
  `infra/monitoring/` and are applied to the monitoring host.

## Testing

```bash
pytest backend/tests
```

CI runs the unit and integration suites on every PR; container images are built
and published only after tests pass.

## CI/CD & Deployment

- **CI** (GitHub Actions): on each PR, the unit and integration suites plus a
  static-analysis gate run; on success, backend / frontend / db / gateway images
  are built and pushed to GHCR.
- **Delivery** (Jenkins): merges to `main` deploy to a staging environment, git
  tags (`vX.Y.Z`) promote the corresponding image to production, and open PRs get
  ephemeral preview stacks that are torn down on close.

Host-specific deployment and Jenkins configuration are kept in a private ops
runbook and intentionally not published here.

## Database Backups

The staging and production stacks run a `pg_dump` backup sidecar
(`infra/deploy/backup/backup.sh`, wired into the staging/prod compose overlays).
It writes a daily compressed snapshot of the database and keeps the most recent
few, so the data survives a lost container or volume.

- **Schedule / retention** — one dump every `BACKUP_INTERVAL_SECONDS` (default
  `86400`, i.e. daily), keeping the newest `BACKUP_KEEP` (default `7`) files named
  `mealorder-YYYYMMDD-HHMMSS.sql.gz`. Dumps live in the `db_backups` named volume,
  which persists across stack restarts.
- **On-demand backup**:

  ```bash
  docker compose -p <stack> exec backup sh -c 'BACKUP_ONCE=1 sh /backup.sh'
  ```

- **List available dumps**:

  ```bash
  docker compose -p <stack> exec backup ls -1t /backups
  ```

- **Restore a dump**:

  ```bash
  DUMP=mealorder-YYYYMMDD-HHMMSS.sql.gz
  docker compose -p <stack> exec -T backup cat /backups/${DUMP} \
    | docker compose -p <stack> exec -T db \
        sh -c 'gunzip -c | psql -U $POSTGRES_USER -d $POSTGRES_DB'
  ```

`<stack>` is the compose project name of the target environment. Detailed,
host-specific restore steps live in the private ops runbook.

## Git Branch Flow

1. Keep `main` stable and protected.
2. Start every change from an issue, then a feature branch:

   ```bash
   git checkout -b feature/<name>/<short-task>
   ```

3. Commit small, focused changes; reference the issue (`#<n>`).
4. Open a pull request into `main`; CI must pass and a review is required.
5. Image builds run only after tests pass; merge after green checks + review.

## 12-Factor Notes

- Config comes from environment variables.
- Secrets live in `.env` locally and in the CI / deploy secret stores — never in
  source code.
- Logs are written to stdout.
- The FastAPI app is stateless; PostgreSQL is an external backing service.
