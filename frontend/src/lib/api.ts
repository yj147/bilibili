/**
 * Bili-Sentinel Frontend API Client
 */

import type {
  Account,
  AccountCreate,
  AutoReplyConfig,
  AutoReplyStatus,
  CommentScanResult,
  ReportLog,
  ScheduledTask,
  TargetListResponse,
  Target,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

async function request<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "未知错误" }));

    // 根据 B站错误码显示用户友好消息
    if (error.bilibili_code) {
      const biliCodeMessages: Record<number, string> = {
        [-352]: "账号触发风控，请稍后重试或更换账号",
        [-101]: "账号未登录或已失效，请重新登录",
        [-799]: "需要人机验证，请在B站完成验证后重试",
        [-412]: "请求过于频繁，请稍后重试",
      };
      const friendlyMessage = biliCodeMessages[error.bilibili_code];
      if (friendlyMessage) {
        throw new Error(friendlyMessage);
      }
    }

    throw new Error(error.detail || `请求失败 (${response.status})`);
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
    stats: () => request<{ total: number; pending: number; processing: number; completed: number; failed: number }>("/targets/stats"),
    create: (data: { type: string; identifier: string; reason_id?: number; reason_content_id?: number; reason_text?: string }) =>
      request<Target>("/targets/", { method: "POST", body: JSON.stringify(data) }),
    createBatch: (data: { type: string; identifiers: string[]; reason_id?: number; reason_content_id?: number; reason_text?: string }) =>
      request("/targets/batch", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: { reason_id?: number; reason_content_id?: number; reason_text?: string; status?: string }) =>
      request<Target>(`/targets/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/targets/${id}`, { method: "DELETE" }),
    deleteByStatus: (status: string) => request(`/targets/?status=${status}`, { method: "DELETE" }),
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
    scanComments: (data: { bvid: string; account_id: number; reason_id?: number; reason_text?: string; max_pages?: number; auto_report?: boolean }) =>
      request<CommentScanResult>("/reports/scan-comments", { method: "POST", body: JSON.stringify(data) }),
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
    getAll: () => request<Record<string, unknown>>('/config/'),
    get: (key: string) => request<{ key: string; value: unknown }>(`/config/${key}`),
    update: (key: string, value: unknown) => request(`/config/${key}`, { method: 'PUT', body: JSON.stringify({ value }) }),
    updateBatch: (configs: Record<string, unknown>) => request('/config/batch', { method: 'POST', body: JSON.stringify(configs) }),
  },

  // --- Auth ---
  auth: {
    qrGenerate: () => request<{ qrcode_key: string; url: string }>("/auth/qr/generate"),
    qrPoll: (qrcode_key: string, account_name?: string) =>
      request<{ status_code: number; message: string; cookies?: Record<string, string>; refresh_token?: string }>(
        "/auth/qr/poll", { method: "POST", body: JSON.stringify({ qrcode_key, account_name }) }
      ),
    qrLogin: (qrcode_key: string, account_name?: string) =>
      request<{ status_code: number; message: string; account?: Record<string, unknown> }>(
        "/auth/qr/login", { method: "POST", body: JSON.stringify({ qrcode_key, account_name }) }
      ),
    cookieStatus: (id: number) => request<{ needs_refresh: boolean; reason: string; timestamp?: number }>(`/auth/${id}/cookie-status`),
    refreshCookies: (id: number) => request<{ success: boolean; message: string }>(`/auth/${id}/refresh`, { method: "POST" }),
  },

  // --- Scheduler ---
  scheduler: {
    getTasks: () => request<ScheduledTask[]>("/scheduler/tasks"),
    createTask: (data: { name: string; task_type: string; cron_expression?: string; interval_seconds?: number }) =>
      request<ScheduledTask>("/scheduler/tasks", { method: "POST", body: JSON.stringify(data) }),
    updateTask: (id: number, data: { name?: string; cron_expression?: string; interval_seconds?: number; config_json?: Record<string, unknown> }) =>
      request<ScheduledTask>(`/scheduler/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    toggleTask: (id: number) => request(`/scheduler/tasks/${id}/toggle`, { method: "POST" }),
    deleteTask: (id: number) => request(`/scheduler/tasks/${id}`, { method: "DELETE" }),
    getHistory: (limit?: number) => request<ReportLog[]>(`/scheduler/history?limit=${limit || 50}`),
  },
};
