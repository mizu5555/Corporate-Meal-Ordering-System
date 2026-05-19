import { apiFetch } from "./client";
import { MOCK_MENU } from "./mockData";

function withMockFallback(apiCall, mockResult) {
  return apiCall().catch(() => mockResult);
}

export function getMyMenu() {
  return withMockFallback(
    () => apiFetch("/vendor/me/menu"),
    (MOCK_MENU[1] ?? []).map((item) => ({
      ...item,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
  );
}
