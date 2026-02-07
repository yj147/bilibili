import useSWR from 'swr';
import type { Account, TargetListResponse, ReportLog, AutoReplyConfig, AutoReplyStatus, ScheduledTask } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api';

const fetcher = (path: string) => fetch(`${API_BASE}${path}`).then(r => {
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
});

export function useAccounts() {
  return useSWR<Account[]>('/accounts/', fetcher);
}

export function useTargets(params: Record<string, string> = {}) {
  const query = new URLSearchParams(params).toString();
  return useSWR<TargetListResponse>(`/targets/?${query}`, fetcher);
}

export function useReportLogs(limit = 50) {
  return useSWR<ReportLog[]>(`/reports/logs?limit=${limit}`, fetcher);
}

export function useAutoReplyConfigs() {
  return useSWR<AutoReplyConfig[]>('/autoreply/config', fetcher);
}

export function useAutoReplyStatus() {
  return useSWR<AutoReplyStatus>('/autoreply/status', fetcher, { refreshInterval: 5000 });
}

export function useSchedulerTasks() {
  return useSWR<ScheduledTask[]>('/scheduler/tasks', fetcher);
}

export function useSchedulerHistory(limit = 20) {
  return useSWR<ReportLog[]>(`/scheduler/history?limit=${limit}`, fetcher);
}

export function useConfigs() {
  return useSWR<Record<string, any>>('/config/', fetcher);
}

export function useSystemInfo() {
  return useSWR<{ version: string; python: string; platform: string; accounts: number; targets: number }>('/system/info', fetcher, { refreshInterval: 30000 });
}
