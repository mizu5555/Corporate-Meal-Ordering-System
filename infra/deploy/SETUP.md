# NOL One-Time Setup for TBD Deployment

All steps run **on the NOL host (A 機)** as a user with docker permission and access to NPM (nginx proxy manager).
Re-running any block is safe (idempotent) unless explicitly noted.

This setup supports the Trunk-Based Development pipeline:
- `merge to main` → staging at `https://nol.cs.nycu.edu.tw/meal-staging/`
- `git tag v*.*.*` → production at `https://nol.cs.nycu.edu.tw/meal/`
- Root `/` 維持既有靜態網站，本作業不接管。

Architecture: Jenkins (on NOL host, in container with docker.sock mount) deploys
from its own workspace — no per-project source clone required on the host.

## Prerequisites

- Docker (with compose v2), git, curl, jq, gh CLI installed
- Jenkins already serves `https://nol.cs.nycu.edu.tw/jenkins/` with docker.sock mounted into the container
- NPM (nginx-proxy-manager) terminating TLS for `nol.cs.nycu.edu.tw`

## 1. Shared docker network

```bash
docker network inspect preview-net >/dev/null 2>&1 \
  || docker network create preview-net
```

## 2. Shared internal router

The router image is **self-contained**: `run-router.sh` builds an image with the
Caddyfile baked in (`infra/deploy/router/Dockerfile`) — there is **no bind
mount**, so the container has no host-path dependency and survives host reboots,
docker daemon restarts, and `/tmp` / Jenkins-workspace cleanup.

> ⚠️ Do **NOT** clone into `/tmp` or any path that gets wiped. An earlier setup
> bind-mounted the Caddyfile from `/tmp/cmos`; when `/tmp` was cleared, Docker
> recreated the missing mount source as an empty *directory*, the mount onto
> `/etc/caddy/Caddyfile` failed, and the container died with **exit 127** —
> 502ing every `/meal*` path. The baked-in image removes that failure mode.

Bootstrap once from any checkout (the build copies the Caddyfile into the image,
so the checkout is genuinely not needed afterwards):

```bash
git clone https://github.com/mizu5555/Corporate-Meal-Ordering-System.git ~/cmos
bash ~/cmos/infra/deploy/router/run-router.sh
curl -s http://127.0.0.1:18080/ ; echo
# expect: preview-router OK
```

`run-router.sh` is idempotent: it rebuilds the image and only recreates the
container when the Caddyfile changed or the container is missing/stopped.
`Jenkinsfile.cleanup` runs it **hourly**, so a dead router self-heals within an
hour without manual intervention. If the Caddyfile changes upstream and you want
it live immediately, just re-run the script.

**Troubleshooting `502 Bad Gateway` on `/meal*`:** the router is the single
host-facing entry on `127.0.0.1:18080`; if it is down, every stack 502s even
though the gateways are healthy. Check `docker ps -a | grep router` and re-run
`run-router.sh`.

## 3. NPM — add /meal-staging/ and /meal/ proxy locations

Edit the `nol.cs.nycu.edu.tw` proxy host in NPM UI. Go to **Advanced** tab and add to **Custom Nginx Configuration**:

```nginx
location /meal-staging/ {
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_pass http://127.0.0.1:18080;
}

location /meal/ {
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_pass http://127.0.0.1:18080;
}
```

Save. NPM reloads automatically. Verify (before any stack is deployed, expect 503 = router up but no upstream):

```bash
curl -skI https://nol.cs.nycu.edu.tw/meal-staging/health
curl -skI https://nol.cs.nycu.edu.tw/meal/health
```

## 4. Jenkins — Staging pipeline (`mealorder-staging`)

> **Deprecated by §11.2 (GHCR build-once).** Keep this job disabled; deploys now use the parameterized token-triggered jobs.

In the Jenkins UI:
1. **New Item → Multibranch Pipeline**, name `mealorder-staging`.
2. **Branch Sources → GitHub**, repo `mizu5555/Corporate-Meal-Ordering-System`, credentials = PAT with `repo` + `admin:repo_hook`.
3. **Behaviors → Add → Filter by name (with regex)** = `^main$`.
4. **Build Configuration → by Jenkinsfile**, Script Path = `Jenkinsfile.staging`.
5. **Scan triggers** — enable `Periodically if not otherwise run` = 1 minute.
6. Save → automatic scan triggers first build.

## 5. Jenkins — Production pipeline (`mealorder-prod`)

> **Deprecated by §11.2 (GHCR build-once).** Keep this job disabled; deploys now use the parameterized token-triggered jobs.

1. **New Item → Multibranch Pipeline**, name `mealorder-prod`.
2. **Branch Sources → GitHub**, same repo + credentials.
3. **Behaviors → Remove `Discover branches`. Add `Discover tags`.**
4. **Behaviors → Add → Filter by name (with regex)** = `^v\d+\.\d+\.\d+$`.
5. **Build Configuration → by Jenkinsfile**, Script Path = `Jenkinsfile.prod`.
6. Save. First scan likely finds no existing semver tag (until you push v0.1.0).

> Note: new tags are auto-built only after the multibranch has indexed them; the very first tag may need a manual "Build Now" on its branch entry.

## 6. Jenkins — Cleanup pipeline (`mealorder-cleanup`)

1. **New Item → Pipeline**, name `mealorder-cleanup`.
2. **Pipeline → Pipeline script from SCM**, Git repo + branch `*/main`, Script Path = `Jenkinsfile.cleanup`.
3. Save → click **Build Now** once (registers the cron declared inside the Jenkinsfile).

## 6.5 Jenkins — PR preview pipeline (`mealorder-preview`)

> **Deprecated by §11.2 (GHCR build-once).** Keep this job disabled; deploys now use the parameterized token-triggered jobs.

1. **New Item → Multibranch Pipeline**, name `mealorder-preview`.
2. **Branch Sources → GitHub**, repo `mizu5555/Corporate-Meal-Ordering-System`, credentials = your PAT.
3. **Behaviors** — adjust:
   - **Remove** `Discover branches` (PR-only pipeline).
   - **Add** `Discover pull requests from origin` (strategy: "Merging the pull request with the current target branch revision").
   - Optionally `Discover pull requests from forks` if you want fork-PR previews (security caveat: forked PRs can execute your Jenkinsfile).
4. **Build Configuration → by Jenkinsfile**, Script Path = `Jenkinsfile.preview`.
5. **Scan triggers** — enable `Periodically if not otherwise run` = 1 minute (or rely on webhook).
6. Save.

Then add a Custom Nginx location to the existing `nol.cs.nycu.edu.tw` proxy host in NPM:

```nginx
location /meal-preview/ {
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_pass http://127.0.0.1:18080;
}
```

(`/meal-staging/` and `/meal/` lines stay as-is — `/meal-preview/` is additive and keeps the `meal-*` namespace consistent with the other two.)

Preview slot cap is hard-coded to 3 in `Jenkinsfile.preview` (`PREVIEW_LIMIT`); adjust if NOL resources allow more.

## 7. Jenkins-service mount requirements

This Jenkins service container only needs:
- `/var/run/docker.sock` mounted in
- Its own `jenkins_home` bind/volume

**No per-project source mount required.** Each pipeline checks the repo out into its own Jenkins workspace and runs `docker compose` from there; the docker daemon receives build contexts over the socket.

## 8. Jenkins credentials

| ID | Type | Used for |
|---|---|---|
| `gh-pat` | Secret text | `gh pr list` inside the cleanup sweep |
| `github-app` | GitHub App or PAT | Branch source authentication |

## 9. First deploy

```bash
# 1. Merge a PR into main → mealorder-staging job triggers automatically
curl -sk https://nol.cs.nycu.edu.tw/meal-staging/health

# 2. From your laptop, cut the first prod tag
git tag v0.1.0 && git push origin v0.1.0
# → mealorder-prod multibranch detects the tag (may need a manual Scan + Build Now the first time)

curl -sk https://nol.cs.nycu.edu.tw/meal/health
```

## 10. End-to-end verification checklist

- [ ] PR open → GitHub Actions `unit` + `integration` green, no Jenkins build triggered
- [ ] Merge to `main` → `mealorder-staging` job green, `/meal-staging/health` returns 200
- [ ] `git push origin v0.1.0` → `mealorder-prod` job green, `/meal/health` returns 200
- [ ] Subsequent merge to `main` updates `/meal-staging/`, prod stays on v0.1.0
- [ ] `docker compose ls` shows `mealorder-staging`, `mealorder-prod`, `caddy-preview-router`
- [ ] `https://nol.cs.nycu.edu.tw/` static homepage unaffected
- [ ] Opening a PR triggers `mealorder-preview`; PR receives a comment with the preview URL
- [ ] `https://nol.cs.nycu.edu.tw/preview/<slug>/health` returns 200 for the open PR
- [ ] Closing the PR → within 1 hour, the preview stack is gone (`docker compose ls`)

## 11. GHCR build-once CI/CD setup

This section documents the one-time manual configuration required for the
build-once flow introduced in the `feature/cicd/ghcr-build-once` branch.
GitHub Actions builds and pushes images to GHCR once; Jenkins jobs pull and
deploy without rebuilding.

### 11.1 GitHub repo secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret name | Value |
|---|---|
| `JENKINS_URL` | NOL Jenkins base URL reachable from GitHub Actions (e.g. `https://nol.cs.nycu.edu.tw/jenkins`) |
| `JENKINS_USER` | Jenkins username that owns the API token below |
| `JENKINS_API_TOKEN` | Jenkins API token for `JENKINS_USER` (generate under user → Configure → API Token) |
| `JENKINS_STAGING_TOKEN` | "Trigger builds remotely" token set on the `meal-deploy-staging` job |
| `JENKINS_PREVIEW_TOKEN` | "Trigger builds remotely" token set on the `meal-deploy-preview` job |
| `JENKINS_PROD_TOKEN` | "Trigger builds remotely" token set on the `meal-deploy-prod` job |

### 11.2 Jenkins deploy jobs (replace old multibranch jobs)

Create **three parameterized Pipeline jobs** (not Multibranch) in Jenkins UI.
The old multibranch jobs (`mealorder-staging`, `mealorder-prod`, `mealorder-preview`)
must be **disabled or deleted** so they no longer trigger on SCM webhook events
and do not double-trigger alongside the new token-triggered jobs.

**Common setup for all three jobs:**

- **Pipeline → Pipeline script from SCM**, Git repo `https://github.com/mizu5555/Corporate-Meal-Ordering-System.git`, credentials = your PAT, branch `*/main`.
- Enable **Trigger builds remotely (e.g., from scripts)** and set the
  Authentication Token to match the corresponding GitHub secret value.
- Do **not** enable periodic SCM polling or webhook branch sources — these jobs
  are triggered exclusively via the remote-build token from GitHub Actions.

**`meal-deploy-staging`**

- Script Path: `Jenkinsfile.staging`
- Token: same value as `JENKINS_STAGING_TOKEN`
- String parameter: `IMAGE_TAG` (default empty) — the GHCR image tag to deploy

**`meal-deploy-preview`**

- Script Path: `Jenkinsfile.preview`
- Token: same value as `JENKINS_PREVIEW_TOKEN`
- String parameters:
  - `IMAGE_TAG` — the GHCR image tag to deploy
  - `PR_NUMBER` — pull request number (used for stack name and URL slug)
  - `PR_BRANCH` — source branch name

**`meal-deploy-prod`**

- Script Path: `Jenkinsfile.prod`
- Token: same value as `JENKINS_PROD_TOKEN`
- String parameter: `IMAGE_TAG` — the GHCR image tag to deploy (semver tag, e.g. `v1.2.3`)

> **Note — release tags must point to a commit already on `main`.**
> The `promote` job re-tags the existing `ghcr.io/mizu5555/mealorder-*:sha-<commit>` image.
> Create tags on a commit that was already pushed/merged to `main`
> (e.g. `git tag vX.Y.Z <sha-on-main>`). If the sha image does not exist
> (tag on a commit that was never built on `main`), `promote` fails with a
> GHCR `manifest unknown` error and prod is not deployed.

**`meal-deploy-cleanup`** (or `mealorder-cleanup`)

- Keep as-is with its cron trigger; no token trigger needed.
- Ensure its PAT credential (`github-token-eason`) has `delete:packages` scope — see §11.3.

### 11.3 Jenkins credentials

Go to **Manage Jenkins → Credentials** (the appropriate domain/store). The existing
`github-token-eason` credential is reused for everything — no new credential is needed:

| Credential ID | Type | Details |
|---|---|---|
| `github-token-eason` | Username + password | The existing credential, reused. **Extend** its backing PAT to include `read:packages` (so all three deploy jobs can `docker login ghcr.io` and pull) and `delete:packages` (so the cleanup job can delete closed-PR `pr-*` images), in addition to its existing `repo` scope (PR comments). Since these are *added* scopes on a classic token, the token string is unchanged — **no Jenkins credential update is required**, only the GitHub scope edit. |

### 11.4 GHCR package permissions

After the first GitHub Actions workflow push succeeds, four packages appear under
the `mizu5555` account: `mealorder-backend`, `mealorder-frontend`, `mealorder-db`,
`mealorder-gateway`.

For each package:

1. Go to `https://github.com/orgs/mizu5555/packages` (or the user's packages page).
2. Open the package → **Package settings**.
3. Under **Manage Actions access**, confirm the `mizu5555/Corporate-Meal-Ordering-System` repo has **Write** access (needed so Actions can push).
4. Confirm the `github-token-eason` PAT account has **Read** (pull) and **delete** (cleanup) capability for the package.

### 11.5 Branch protection — update required status check name

The GitHub Actions workflow `name:` changed from `Test` to `CI/CD` in this
refactor. If the `main` branch protection rule (or any other branch rule) lists
`Test` as a required status check, update it:

1. **Settings → Branches → Edit** the protection rule for `main`.
2. In **Require status checks to pass before merging**, remove `Test` and add
   the new check name(s) emitted by the `CI/CD` workflow (e.g. `unit-tests`,
   `integration-tests`, or `build-and-push` — check the Actions tab after the
   first run for the exact job names).
3. Save. Without this update the branch protection will either pass vacuously
   (old check name never fires) or block PRs unexpectedly.
