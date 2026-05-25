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
// RBAC header pattern mirrors backend/core/vendor_identity.py:
//   x-user-role: vendor_manager
//   x-vendor-id: <seeded vendor id>
//
// `check()` thresholds are deliberately tight on the golden path. Tune to
// the staging environment when feeding real traffic into the Grafana
// dashboards from PR #28.

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const VENDOR_ID = __ENV.VENDOR_ID || '1';
const VUS = parseInt(__ENV.VUS || '5');
const DURATION = __ENV.DURATION || '30s';

const headers = {
  'Content-Type': 'application/json',
  'x-user-role': 'vendor_manager',
  'x-vendor-id': VENDOR_ID,
};

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

export default function () {
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
