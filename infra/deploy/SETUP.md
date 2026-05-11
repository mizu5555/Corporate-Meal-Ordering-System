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

Clone the repo somewhere ONLY for running the router script (the router itself only mounts the Caddyfile; once the container is up the clone isn't needed):

```bash
git clone https://github.com/mizu5555/Corporate-Meal-Ordering-System.git /tmp/cmos
bash /tmp/cmos/infra/deploy/router/run-router.sh
curl -s http://127.0.0.1:18080/ ; echo
# expect: preview-router OK
```

If the Caddyfile changes upstream, re-run the script (it recreates the container).

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

In the Jenkins UI:
1. **New Item → Multibranch Pipeline**, name `mealorder-staging`.
2. **Branch Sources → GitHub**, repo `mizu5555/Corporate-Meal-Ordering-System`, credentials = PAT with `repo` + `admin:repo_hook`.
3. **Behaviors → Add → Filter by name (with regex)** = `^main$`.
4. **Build Configuration → by Jenkinsfile**, Script Path = `Jenkinsfile.staging`.
5. **Scan triggers** — enable `Periodically if not otherwise run` = 1 minute.
6. Save → automatic scan triggers first build.

## 5. Jenkins — Production pipeline (`mealorder-prod`)

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
