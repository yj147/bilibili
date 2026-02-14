"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users,
  ShieldCheck,
  Activity,
  Target,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Ban,
  Clock,
  Trash2,
  ShieldAlert,
  Filter,
} from "lucide-react";
import { parseDateWithUtcFallback } from "@/lib/datetime";
import { useAccounts, useTargets, useReportLogs } from "@/lib/swr";
import { useLogStream } from "@/lib/websocket";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Build an array of daily report counts for the last 7 days from log entries. */
function buildLast7DayCounts(logs: { executed_at: string; success: boolean }[]): { counts: number[]; labels: string[] } {
  const dayNames = ["日", "一", "二", "三", "四", "五", "六"];
  const now = new Date();
  const counts: number[] = [];
  const labels: string[] = [];

  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    labels.push(dayNames[d.getDay()]);
    counts.push(
      logs.filter((l) => parseDateWithUtcFallback(l.executed_at).toISOString().slice(0, 10) === dateStr).length
    );
  }
  return { counts, labels };
}

export default function Dashboard() {
  const { data: accountData, mutate: mutateAccounts } = useAccounts();
  const accounts = accountData?.items ?? [];
  const { data: targetData } = useTargets();
  const { data: apiLogs = [] } = useReportLogs(500);
  const { logs: wsLogs, connected: wsConnected } = useLogStream(50);
  const loading = !accounts;
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);
  const [logFilter, setLogFilter] = useState<"all" | "success" | "error">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [timeRange, setTimeRange] = useState<"today" | "week" | "all">("all");

  // Merge WS logs (real-time) with API logs (historical), WS first
  const wsAsReportLogs = wsLogs.map((entry, i) => ({
    id: entry.id ?? -(i + 1),
    target_id: Number(entry.data?.target_id ?? 0),
    account_id: entry.data?.account_id != null ? Number(entry.data.account_id) : null,
    account_name: String(entry.data?.account_name ?? 'system'),
    action: entry.message || entry.type,
    request_data: null as Record<string, unknown> | null,
    response_data: null as Record<string, unknown> | null,
    success: entry.type !== 'error',
    error_message: entry.type === 'error' ? entry.message : null,
    executed_at: new Date(entry.timestamp).toISOString(),
  }));
  const wsLogIds = new Set(wsAsReportLogs.filter(wl => wl.id > 0).map(wl => wl.id));
  const logs = [
    ...wsAsReportLogs,
    ...apiLogs.filter(al => !wsLogIds.has(al.id)),
  ].slice(0, 50);

  // Bar chart: last 7 days of report activity
  const { counts: dailyCounts, labels: dayLabels } = buildLast7DayCounts(apiLogs);
  const maxCount = Math.max(...dailyCounts, 1);

  // Today's execution: only logs whose executed_at matches today's date
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayCount = apiLogs.filter(
    (l) => l.success && parseDateWithUtcFallback(l.executed_at).toISOString().slice(0, 10) === todayStr
  ).length;

  const activeCount = accounts.filter((a) => a.status === "valid").length;
  const health = accounts.length > 0 ? Math.round((activeCount / accounts.length) * 100) : 0;
  const stats = {
    accounts: accounts.length,
    targets: targetData?.total ?? 0,
    logs: todayCount,
    health,
  };

  // Log helpers for color-coded badges
  type LogEntry = typeof logs[number];
  function getLogErrorCode(log: LogEntry): number | null {
    if (log.success) return 0;
    const resp = log.response_data as Record<string, unknown> | null;
    if (resp && typeof resp.code === "number") return resp.code;
    if (log.error_message?.includes("-352")) return -352;
    if (log.error_message?.includes("12019") || log.error_message?.includes("频率")) return 12019;
    if (log.error_message?.includes("12022") || log.error_message?.includes("删除")) return 12022;
    if (log.error_message?.includes("12008") || log.error_message?.includes("举报过")) return 12008;
    return null;
  }

  function getLogBadge(code: number | null, success: boolean) {
    if (success || code === 0) return { label: "成功", icon: CheckCircle2, bgClass: "bg-green-100", iconClass: "text-green-600", badgeClass: "bg-green-100 text-green-700" };
    if (code === 12022) return { label: "已删除", icon: Trash2, bgClass: "bg-slate-100", iconClass: "text-slate-500", badgeClass: "bg-slate-100 text-slate-600" };
    if (code === 12008) return { label: "已举报", icon: Ban, bgClass: "bg-blue-100", iconClass: "text-blue-500", badgeClass: "bg-blue-100 text-blue-600" };
    if (code === 12019) return { label: "频率限制", icon: Clock, bgClass: "bg-amber-100", iconClass: "text-amber-600", badgeClass: "bg-amber-100 text-amber-700" };
    if (code === -352) return { label: "风控拦截", icon: ShieldAlert, bgClass: "bg-red-100", iconClass: "text-red-500", badgeClass: "bg-red-100 text-red-600" };
    return { label: "失败", icon: AlertTriangle, bgClass: "bg-red-50", iconClass: "text-red-500", badgeClass: "bg-red-50 text-red-600" };
  }

  const filteredLogs = logs
    .filter((l) => logFilter === "all" || (logFilter === "success" ? l.success : !l.success))
    .filter((l) => {
      if (!searchQuery.trim()) return true;
      const query = searchQuery.toLowerCase();
      const accountName = l.account_name?.toLowerCase() ?? '';
      const action = l.action.toLowerCase();
      return accountName.includes(query) || action.includes(query);
    })
    .filter((l) => {
      if (timeRange === "all") return true;
      const logDate = parseDateWithUtcFallback(l.executed_at);
      const now = new Date();
      if (timeRange === "today") {
        return logDate.toISOString().slice(0, 10) === now.toISOString().slice(0, 10);
      }
      if (timeRange === "week") {
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        return logDate >= weekAgo;
      }
      return true;
    });

  const successCount = filteredLogs.filter((l) => l.success).length;
  const failCount = filteredLogs.length - successCount;
  const successRate = filteredLogs.length > 0 ? Math.round((successCount / filteredLogs.length) * 100) : 0;

  return (
    <div className="p-6 md:p-8">
      {/* Header */}
      <header className="max-w-7xl mx-auto flex justify-between items-center mb-8">
        <h1 className="text-2xl font-semibold">Bili-Sentinel</h1>
        <button
          onClick={() => mutateAccounts()}
          className="px-4 py-2 rounded-lg border flex items-center gap-2 text-sm hover:bg-muted transition-all duration-200 cursor-pointer card-static"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          刷新
        </button>
      </header>

      {/* Main Grid */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 grid-rows-auto gap-4">
        {/* Stats Overview */}
        <Card className="md:col-span-2 card-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity size={16} className="text-primary" /> 数据总览
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-8">
              <div className="flex flex-col">
                <span className="text-sm text-muted-foreground">在线账号</span>
                <span className="text-2xl font-bold text-foreground">{stats.accounts}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm text-muted-foreground">待处理目标</span>
                <span className="text-2xl font-bold text-foreground">{stats.targets}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm text-muted-foreground">今日执行</span>
                <span className="text-2xl font-bold text-foreground">{stats.logs}</span>
              </div>
            </div>
            <div className="mt-6 h-[60px] flex items-end gap-1">
              {dailyCounts.map((count, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: `${maxCount > 0 ? (count / maxCount) * 100 : 0}%` }}
                    transition={{ delay: i * 0.08, duration: 0.5 }}
                    className="w-full bg-primary/60 rounded-sm min-h-[2px]"
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-1 mt-1">
              {dayLabels.map((label, i) => (
                <div key={i} className="flex-1 text-center text-xs text-muted-foreground">{label}</div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Account Health */}
        <Card className="md:col-span-1 card-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck size={16} className="text-green-500" /> 账号健康度
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">登录有效率</span>
                <span className={`text-sm font-bold ${stats.health > 80 ? "text-green-600" : "text-red-600"}`}>
                  {stats.health}%
                </span>
              </div>
              <div className="w-full bg-muted h-2 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${stats.health}%` }}
                  className={`h-full ${stats.health > 80 ? "bg-green-500" : "bg-red-500"}`}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                账号整体状态: {stats.health > 80 ? "正常" : "异常"}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Live Status */}
        <Card className="md:col-span-1 card-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Target size={16} className="text-accent" /> 实时状态
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-green-600 bg-green-500/10 p-2 rounded">
                <CheckCircle2 size={14} /> 设备伪装已开启
              </div>
              <div className={`flex items-center gap-2 text-sm p-2 rounded ${wsConnected ? 'text-blue-600 bg-blue-500/10' : 'text-yellow-600 bg-yellow-500/10'}`}>
                <Activity size={14} className={wsConnected ? "animate-pulse" : ""} /> {wsConnected ? '实时推送已连接' : '正在连接...'}
              </div>
              <div className="flex items-center gap-2 text-sm text-purple-600 bg-purple-500/10 p-2 rounded">
                <ShieldCheck size={14} /> 服务正常运行
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Account List */}
        <Card className="md:col-span-1 md:row-span-2 card-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Users size={16} className="text-primary" /> 账号列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 h-[400px] overflow-y-auto pr-2">
              {accounts.length === 0 ? (
                <div className="text-center text-muted-foreground mt-20 text-sm">
                  暂无账号
                </div>
              ) : (
                accounts.map((acc) => (
                  <div
                    key={acc.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          acc.status === "valid" ? "bg-green-500" : "bg-red-500"
                        }`}
                      />
                      <div>
                        <div className="text-sm font-medium">{acc.name}</div>
                        <div className="text-xs text-muted-foreground">
                          UID: {acc.uid || "---"}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Log Area */}
        <Card className="md:col-span-3 md:row-span-2 card-elevated">
          <CardHeader className="pb-3 space-y-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Activity size={16} className="text-accent" /> 任务日志
                <span className="text-xs text-muted-foreground font-normal ml-1">({filteredLogs.length})</span>
              </CardTitle>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-green-600">成功: {successCount}</span>
                  <span className="text-red-600">失败: {failCount}</span>
                  <span className="text-muted-foreground">成功率: {successRate}%</span>
                </div>
                <div className="flex gap-1">
                  {(["all", "success", "error"] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setLogFilter(f)}
                      className={`px-2.5 py-1 text-xs rounded-md transition-colors cursor-pointer ${
                        logFilter === f
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {f === "all" ? "全部" : f === "success" ? "成功" : "失败"}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <input
              type="text"
              placeholder="搜索账号名称或操作..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-1.5 text-sm rounded-md border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <div className="flex gap-1">
              {(["today", "week", "all"] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-2.5 py-1 text-xs rounded-md transition-colors cursor-pointer ${
                    timeRange === range
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {range === "today" ? "今天" : range === "week" ? "最近7天" : "全部"}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[400px] overflow-y-auto pr-2 space-y-1">
              {filteredLogs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <Filter size={32} className="opacity-20 mb-3" />
                  <span className="text-sm">暂无{logFilter === "all" ? "任务" : logFilter === "success" ? "成功" : "失败"}记录</span>
                </div>
              ) : (
                filteredLogs.map((log) => {
                  const errCode = getLogErrorCode(log);
                  const badge = getLogBadge(errCode, log.success);
                  return (
                    <div key={log.id}>
                      <div
                        className="py-2 px-3 flex items-start gap-3 rounded-lg cursor-pointer hover:bg-muted/60 transition-colors group"
                        onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
                      >
                        <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${badge.bgClass}`}>
                          <badge.icon size={12} className={badge.iconClass} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-foreground truncate">
                              {log.account_name}
                            </span>
                            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.badgeClass}`}>
                              {badge.label}
                            </span>
                            <span className="text-xs text-muted-foreground ml-auto shrink-0">
                              {parseDateWithUtcFallback(log.executed_at).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5 truncate">
                            {log.action}
                            {!log.success && log.error_message && (
                              <span className="text-red-500/80"> - {log.error_message}</span>
                            )}
                          </p>
                        </div>
                        {(log.request_data || log.response_data) && (
                          <span className="text-muted-foreground shrink-0 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            {expandedLogId === log.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          </span>
                        )}
                      </div>
                      <AnimatePresence>
                        {expandedLogId === log.id && (log.request_data || log.response_data) && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="bg-muted/50 rounded-lg p-3 ml-9 mb-1 space-y-2 border border-border/50">
                              {log.request_data && (
                                <div>
                                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Request</span>
                                  <pre className="text-xs text-foreground mt-1 whitespace-pre-wrap break-all font-mono bg-background/50 rounded p-2">
                                    {JSON.stringify(log.request_data, null, 2)}
                                  </pre>
                                </div>
                              )}
                              {log.response_data && (
                                <div>
                                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Response</span>
                                  <pre className="text-xs text-foreground mt-1 whitespace-pre-wrap break-all font-mono bg-background/50 rounded p-2">
                                    {JSON.stringify(log.response_data, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>
      </main>

      <footer className="max-w-7xl mx-auto mt-8 text-center text-xs text-muted-foreground">
        Bili-Sentinel v1.0.0
      </footer>
    </div>
  );
}
