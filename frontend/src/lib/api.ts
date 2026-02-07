/**
 * Bili-Sentinel Frontend API Client
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

async function request(path: string, options: RequestInit = {}) {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  // --- Accounts ---
  accounts: {
    list: () => request("/accounts/"),
    get: (id: number) => request(`/accounts/${id}`),
    create: (data: any) => request("/accounts/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: any) => request(`/accounts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/accounts/${id}`, { method: "DELETE" }),
    check: (id: number) => request(`/accounts/${id}/check`, { method: "POST" }),
  },

  // --- Targets ---
  targets: {
    list: (params: any = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/targets/?${query}`);
    },
    create: (data: any) => request("/targets/", { method: "POST", body: JSON.stringify(data) }),
    createBatch: (data: any) => request("/targets/batch", { method: "POST", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/targets/${id}`, { method: "DELETE" }),
  },

  // --- Reports ---
  reports: {
    execute: (targetId: number, accountIds?: number[]) => 
      request("/reports/execute", { 
        method: "POST", 
        body: JSON.stringify({ target_id: targetId, account_ids: accountIds }) 
      }),
    executeBatch: (targetIds?: number[], accountIds?: number[]) => 
      request("/reports/execute/batch", { 
        method: "POST", 
        body: JSON.stringify({ target_ids: targetIds, account_ids: accountIds }) 
      }),
    getLogs: (limit: number = 50) => request(`/reports/logs?limit=${limit}`),
  },

  // --- Auto-Reply ---
  autoreply: {
    getConfigs: () => request("/autoreply/config"),
    createConfig: (data: any) => request("/autoreply/config", { method: "POST", body: JSON.stringify(data) }),
    updateConfig: (id: number, data: any) => request(`/autoreply/config/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteConfig: (id: number) => request(`/autoreply/config/${id}`, { method: "DELETE" }),
    getStatus: () => request("/autoreply/status"),
    start: (interval: number = 30) => request(`/autoreply/start?interval=${interval}`, { method: "POST" }),
    stop: () => request("/autoreply/stop", { method: "POST" }),
  }
};
