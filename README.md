# Corporate Meal Ordering System

NYCU 2026 Spring Cloud Native Development and Best Practice.

This is a cloud-native base repo for a team building a corporate meal ordering
system. It intentionally contains only the shared development environment,
layering, CI, RBAC skeleton, vendor admin skeleton, committee review skeleton,
and initial database schema. 

## Project Structure

```text
project-root/
├── frontend/
├── backend/
│   ├── core/
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── db/migrations/
│   ├── tests/
│   └── main.py
├── infra/caddy/
├── docker-compose.yml
├── .env.example
├── .github/workflows/test.yml
├── requirements.txt
├── .gitignore
└── README.md
```

## Team Work Split

- Frontend: `frontend/`
- Backend DB: schema, migrations, persistence setup
- Backend ordering: meal ordering routes, services, repositories
- Backend vendor admin: vendor management and vendor review flow
- Backend committee review: approval workflow and audit trail

## Getting Started

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Update `.env` local secrets such as `POSTGRES_PASSWORD`.

3. Start the full local stack (with hot reload):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

**Deployment (TBD via Jenkins):** see `infra/deploy/SETUP-NOL.md` for the NOL host one-time setup and Jenkins pipeline configuration.

Main HTTPS entrypoint:

- App: https://localhost
- Backend health check: https://localhost/health
- API docs: https://localhost/docs

Caddy uses a local internal TLS certificate for development. Your browser may
ask you to trust the local certificate the first time.

4. Optional backend-only local setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. Run the backend locally:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Services

- HTTPS gateway: https://localhost
- Frontend direct dev port: http://localhost:3000
- Backend direct dev port: http://localhost:8000
- PostgreSQL: localhost:5432

## Backend Skeleton

- `GET /health`
- RBAC dependency skeleton: `backend/core/rbac.py`
- Vendor review route skeleton: `backend/routes/admin_vendors.py`
- Vendor review service skeleton: `backend/services/vendor_review_service.py`
- Vendor repository skeleton: `backend/repositories/vendor_repository.py`
- Committee review route skeleton: `backend/routes/committee_reviews.py`
- Committee review service skeleton: `backend/services/committee_review_service.py`
- Committee review repository skeleton: `backend/repositories/committee_review_repository.py`
- Audit log repository skeleton: `backend/repositories/audit_log_repository.py`
- Initial SQL schema: `backend/db/migrations/001_initial_schema.sql`

## Testing

```bash
pytest backend/tests
```

## Git Branch Flow

1. Keep `main` stable and protected.
2. Each teammate creates their own feature branch:

```bash
git checkout -b feature/<name>/<short-task>
```

3. Commit small, focused changes.
4. Open a pull request into `main`.
5. GitHub Actions runs backend tests first.
6. Docker image builds only run after backend tests pass.
7. Merge only after review and passing checks.

## 12-Factor Notes

- Config comes from environment variables.
- Secrets belong in `.env` locally and GitHub secrets in CI, not source code.
- Logs are written to stdout.
- The FastAPI app is stateless.
- PostgreSQL is treated as an external backing service.
