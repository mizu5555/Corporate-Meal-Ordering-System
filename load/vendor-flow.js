// k6 load script for the vendor self-service golden path.
//
// Run locally against `docker compose up`:
//   k6 run -e BASE_URL=https://localhost --insecure-skip-tls-verify load/vendor-flow.js
//
// Run with tunable load:
//   k6 run -e BASE_URL=https://localhost -e VUS=10 -e DURATION=2m --insecure-skip-tls-verify load/vendor-flow.js
//
// The script exercises:
//   GET    /vendor/me/profile
//   GET    /vendor/me/categories
//   POST   /vendor/me/categories
//   POST   /vendor/me/menu                  (with daily_quota)
//   GET    /vendor/me/menu/{id}
//   PATCH  /vendor/me/menu/{id}             (set daily_quota=0 — quota-exhausted state)
//   DELETE /vendor/me/menu/{id}
//   DELETE /vendor/me/categories/{id}
//
// Auth: real JWT, not the x-user-role/x-vendor-id header fallback. The deployed
// gateway (infra/caddy/Caddyfile) strips those identity headers so clients
// cannot spoof roles — header-based auth only works when hitting the backend
// directly (:8000) and 403s through any public URL. setup() logs in once via
// POST /auth/login; every VU sends `Authorization: Bearer <token>`. vendor_id
// rides inside the token, so no VENDOR_ID env is needed.
//
// Default credentials are the seeded vendor_manager from
// backend/db/migrations/003_auth.sql (Sunny Kitchen), present on every deploy.
// Override with VENDOR_EMAIL / VENDOR_PASSWORD. This is a real demo vendor, so
// teardown() must NOT delete it — it only sweeps the k6-* rows this run created.
//
// `check()` thresholds are deliberately tight on the golden path. Tune to
// the staging environment when feeding real traffic into the Grafana
// dashboards from PR #28.

import http from 'k6/http';
import { check, sleep, group, fail } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const VENDOR_EMAIL = __ENV.VENDOR_EMAIL || 'vendor@corpmeal.local';
const VENDOR_PASSWORD = __ENV.VENDOR_PASSWORD || 'password123';
const VUS = parseInt(__ENV.VUS || '5');
const DURATION = __ENV.DURATION || '30s';

// Prefixes for the rows this script creates. teardown() keys off these so the
// shared demo vendor's own catalogue is never touched.
const CAT_PREFIX = 'k6-cat-';
const ITEM_PREFIX = 'k6-item-';

// Per-request headers carrying the Bearer token minted in setup(). The token
// already encodes role + vendor_id, so no x-user-role/x-vendor-id is sent.
function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

const flowDuration = new Trend('vendor_flow_duration_ms');
const quotaSetOk = new Counter('vendor_quota_set_total');

export const options = {
  scenarios: {
    vendor_flow: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: VUS },
        { duration: DURATION, target: VUS },
        { duration: '5s', target: 0 },
      ],
      gracefulRampDown: '5s',
    },
  },
  thresholds: {
    // Golden path must not fail. Tighten after baselining.
    'checks{group:::profile}': ['rate>0.99'],
    'checks{group:::category}': ['rate>0.99'],
    'checks{group:::menu}': ['rate>0.99'],
    'http_req_duration{name:GET /vendor/me/profile}': ['p(95)<800'],
    'http_req_duration{name:POST /vendor/me/menu}': ['p(95)<1500'],
  },
};

// Log in once before the load ramp. The returned object is handed to every VU
// (default function) and to teardown(). A failed login aborts the whole run —
// there is no point load-testing the golden path without a valid token.
export function setup() {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: VENDOR_EMAIL, password: VENDOR_PASSWORD }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'POST /auth/login' } },
  );
  if (res.status !== 200) {
    fail(`login failed: status=${res.status} body=${res.body}`);
  }
  const token = res.json('access_token');
  if (!token) {
    fail(`login response missing access_token: ${res.body}`);
  }
  return { token };
}

export default function (data) {
  const headers = authHeaders(data.token);
  const t0 = Date.now();

  group('profile', () => {
    const res = http.get(`${BASE_URL}/vendor/me/profile`, {
      headers,
      tags: { name: 'GET /vendor/me/profile' },
    });
    check(res, {
      'profile 200': (r) => r.status === 200,
      'profile has id': (r) => r.json('id') !== undefined,
    });
  });

  let categoryId;
  group('category', () => {
    const list = http.get(`${BASE_URL}/vendor/me/categories`, {
      headers,
      tags: { name: 'GET /vendor/me/categories' },
    });
    check(list, { 'categories 200': (r) => r.status === 200 });

    const created = http.post(
      `${BASE_URL}/vendor/me/categories`,
      JSON.stringify({ name: `k6-cat-${__VU}-${__ITER}`, sort_order: 0 }),
      { headers, tags: { name: 'POST /vendor/me/categories' } },
    );
    check(created, { 'category created 201': (r) => r.status === 201 });
    categoryId = created.json('id');
  });

  let itemId;
  group('menu', () => {
    const created = http.post(
      `${BASE_URL}/vendor/me/menu`,
      JSON.stringify({
        name: `k6-item-${__VU}-${__ITER}`,
        description: 'k6 generated',
        price_cents: 12000,
        category_id: categoryId,
        daily_quota: 50,
      }),
      { headers, tags: { name: 'POST /vendor/me/menu' } },
    );
    check(created, {
      'menu created 201': (r) => r.status === 201,
      'menu daily_quota=50': (r) => r.json('daily_quota') === 50,
    });
    itemId = created.json('id');

    const got = http.get(`${BASE_URL}/vendor/me/menu/${itemId}`, {
      headers,
      tags: { name: 'GET /vendor/me/menu/{id}' },
    });
    check(got, { 'menu get 200': (r) => r.status === 200 });

    // Simulate quota-exhausted state: set daily_quota=0. This is the
    // documented sentinel for "pause supply while keeping the row".
    const patched = http.patch(
      `${BASE_URL}/vendor/me/menu/${itemId}`,
      JSON.stringify({ daily_quota: 0 }),
      { headers, tags: { name: 'PATCH /vendor/me/menu/{id}' } },
    );
    if (check(patched, {
      'menu patch 200': (r) => r.status === 200,
      'menu daily_quota=0': (r) => r.json('daily_quota') === 0,
    })) {
      quotaSetOk.add(1);
    }

    const del = http.del(`${BASE_URL}/vendor/me/menu/${itemId}`, null, {
      headers,
      tags: { name: 'DELETE /vendor/me/menu/{id}' },
    });
    check(del, { 'menu delete 204': (r) => r.status === 204 });
  });

  // Tidy up the category we created so repeated runs do not balloon state.
  if (categoryId) {
    http.del(`${BASE_URL}/vendor/me/categories/${categoryId}`, null, {
      headers,
      tags: { name: 'DELETE /vendor/me/categories/{id}' },
    });
  }

  flowDuration.add(Date.now() - t0);
  sleep(1);
}

// Backstop cleanup. Each iteration already deletes the rows it created, but an
// aborted iteration (failed check, crashed VU) can leave k6-* rows behind. This
// sweeps any survivors so the shared demo vendor is left exactly as it started.
// menu_items.category_id is ON DELETE SET NULL, so items must go before
// categories. The vendor row itself is never deleted.
export function teardown(data) {
  const headers = authHeaders(data.token);

  const items = http.get(`${BASE_URL}/vendor/me/menu`, { headers });
  if (items.status === 200) {
    for (const item of items.json()) {
      if (typeof item.name === 'string' && item.name.startsWith(ITEM_PREFIX)) {
        http.del(`${BASE_URL}/vendor/me/menu/${item.id}`, null, { headers });
      }
    }
  }

  const cats = http.get(`${BASE_URL}/vendor/me/categories`, { headers });
  if (cats.status === 200) {
    for (const cat of cats.json()) {
      if (typeof cat.name === 'string' && cat.name.startsWith(CAT_PREFIX)) {
        http.del(`${BASE_URL}/vendor/me/categories/${cat.id}`, null, { headers });
      }
    }
  }
}
