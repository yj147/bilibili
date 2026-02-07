/**
 * Bili-Sentinel Frontend API Client
 */

import type {
  Account,
  AccountCreate,
  AutoReplyConfig,
  AutoReplyStatus,
  ReportLog,
  ScheduledTask,
  TargetListResponse,
  Target,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

async function request<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
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
    list: () => request<Account[]>("/accounts/"),
    get: (id: number) => request<Account>(`/accounts/${id}`),
    create: (data: AccountCreate) => request<Account>("/accounts/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<AccountCreate>) => request<Account>(`/accounts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/accounts/${id}`, { method: "DELETE" }),
    check: (id: number) => request(`/accounts/${id}/check`, { method: "POST" }),
  },

  // --- Targets ---
  targets: {
    list: (params: Record<string, string> = {}) => {
      const query = new URLSearchParams(params).toString();
      return request<TargetListResponse>(`/targets/?${query}`);
    },
    create: (data: { type: string; identifier: string; reason_id?: number; reason_text?: string }) =>
      request<Target>("/targets/", { method: "POST", body: JSON.stringify(data) }),
    createBatch: (data: { targets: Array<{ type: string; identifier: string }> }) =>
      request("/targets/batch", { method: "POST", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/targets/${id}`, { method: "DELETE" }),
  },

  // --- Reports ---
  reports: {
    execute: (targetId: number, accountIds?: number[]) =>
      request("/reports/execute", {
        method: "POST",
        body: JSON.stringify({ target_id: targetId, account_ids: accountIds }),
      }),
    executeBatch: (targetIds?: number[], accountIds?: number[]) =>
      request("/reports/execute/batch", {
        method: "POST",
        body: JSON.stringify({ target_ids: targetIds, account_ids: accountIds }),
      }),
    getLogs: (limit: number = 50) => request<ReportLog[]>(`/reports/logs?limit=${limit}`),
  },

  // --- Auto-Reply ---
  autoreply: {
    getConfigs: () => request<AutoReplyConfig[]>("/autoreply/config"),
    createConfig: (data: Omit<AutoReplyConfig, "id">) =>
      request<AutoReplyConfig>("/autoreply/config", { method: "POST", body: JSON.stringify(data) }),
    updateConfig: (id: number, data: Partial<AutoReplyConfig>) =>
      request<AutoReplyConfig>(`/autoreply/config/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteConfig: (id: number) => request(`/autoreply/config/${id}`, { method: "DELETE" }),
    getStatus: () => request<AutoReplyStatus>("/autoreply/status"),
    start: (interval: number = 30) => request(`/autoreply/start?interval=${interval}`, { method: "POST" }),
    stop: () => request("/autoreply/stop", { method: "POST" }),
  },

  // --- Config ---
  config: {
    getAll: () => request<Record<string, any>>('/config/'),
    get: (key: string) => request<{ key: string; value: any }>(`/config/${key}`),
    update: (key: string, value: any) => request(`/config/${key}`, { method: 'PUT', body: JSON.stringify({ value }) }),
    updateBatch: (configs: Record<string, any>) => request('/config/batch', { method: 'POST', body: JSON.stringify(configs) }),
  },

  // --- Scheduler ---
  scheduler: {
    getTasks: () => request<ScheduledTask[]>("/scheduler/tasks"),
    createTask: (data: { name: string; task_type: string; cron_expression?: string; interval_seconds?: number }) =>
      request<ScheduledTask>("/scheduler/tasks", { method: "POST", body: JSON.stringify(data) }),
    toggleTask: (id: number) => request(`/scheduler/tasks/${id}/toggle`, { method: "POST" }),
    deleteTask: (id: number) => request(`/scheduler/tasks/${id}`, { method: "DELETE" }),
    getHistory: (limit?: number) => request<ReportLog[]>(`/scheduler/history?limit=${limit || 50}`),
  },
};
