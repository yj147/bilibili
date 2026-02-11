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
} from "lucide-react";
import { useAccounts, useTargets, useReportLogs } from "@/lib/swr";
import { useLogStream } from "@/lib/websocket";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Build an array of daily report counts for the last 7 days from log entries. */
function buildLast7DayCounts(logs: { executed_at: string; success: boolean }[]): { counts: number[]; labels: string[] } {
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const now = new Date();
  const counts: number[] = [];
  const labels: string[] = [];

  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    labels.push(dayNames[d.getDay()]);
    counts.push(logs.filter((l) => l.executed_at.slice(0, 10) === dateStr).length);
  }
  return { counts, labels };
}

export default function Dashboard() {
  const { data: accounts = [], mutate: mutateAccounts } = useAccounts();
  const { data: targetData } = useTargets();
  const { data: apiLogs = [] } = useReportLogs(500);
  const { logs: wsLogs, connected: wsConnected } = useLogStream(50);
  const loading = !accounts;
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);

  // Merge WS logs (real-time) with API logs (historical), WS first
  const wsAsReportLogs = wsLogs.map((entry, i) => ({
    id: -(i + 1),
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
  const logs = [...wsAsReportLogs, ...apiLogs.filter(al => !wsAsReportLogs.some(wl => wl.action === al.action && Math.abs(new Date(wl.executed_at).getTime() - new Date(al.executed_at).getTime()) < 2000))].slice(0, 50);

  // Bar chart: last 7 days of report activity
  const { counts: dailyCounts, labels: dayLabels } = buildLast7DayCounts(apiLogs);
  const maxCount = Math.max(...dailyCounts, 1);

  // Today's execution: only logs whose executed_at matches today's date
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayCount = apiLogs.filter((l) => l.success && l.executed_at.slice(0, 10) === todayStr).length;

  const activeCount = accounts.filter((a) => a.status === "valid").length;
  const health = accounts.length > 0 ? Math.round((activeCount / accounts.length) * 100) : 0;
  const stats = {
    accounts: accounts.length,
    targets: targetData?.total ?? 0,
    logs: todayCount,
    health,
  };

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
              <Activity size={16} className="text-primary" /> 核心概览
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
                <span className="text-sm text-muted-foreground">Cookie 存活</span>
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
                哨兵集群状态: {stats.health > 80 ? "优良" : "受损"}
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
                <CheckCircle2 size={14} /> UA 自动轮换开启
              </div>
              <div className={`flex items-center gap-2 text-sm p-2 rounded ${wsConnected ? 'text-blue-600 bg-blue-500/10' : 'text-yellow-600 bg-yellow-500/10'}`}>
                <Activity size={14} className={wsConnected ? "animate-pulse" : ""} /> {wsConnected ? 'WebSocket 已连接' : 'WebSocket 连接中...'}
              </div>
              <div className="flex items-center gap-2 text-sm text-purple-600 bg-purple-500/10 p-2 rounded">
                <ShieldCheck size={14} /> 后端引擎 v1.0 运行中
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Account List */}
        <Card className="md:col-span-1 md:row-span-2 card-elevated">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Users size={16} className="text-primary" /> 账号矩阵
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 h-[400px] overflow-y-auto pr-2">
              {accounts.length === 0 ? (
                <div className="text-center text-muted-foreground mt-20 text-sm">
                  暂无哨兵在线
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
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity size={16} className="text-accent" /> 任务日志
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[400px] overflow-y-auto pr-2">
              {logs.length === 0 ? (
                <div className="text-muted-foreground text-sm">等待任务下发中...</div>
              ) : (
                logs.map((log) => (
                  <div key={log.id}>
                    <div
                      className="py-1.5 flex gap-3 border-b last:border-none cursor-pointer hover:bg-muted rounded px-2 -mx-2"
                      onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
                    >
                      <span className="text-sm text-muted-foreground shrink-0">
                        [{new Date(log.executed_at).toLocaleTimeString()}]
                      </span>
                      <span className={`flex-1 text-sm ${log.success ? "text-green-600" : "text-red-600"}`}>
                        Account [{log.account_name}] executed {log.action}
                        {log.success ? " ... SUCCESS" : ` ... FAILED: ${log.error_message}`}
                      </span>
                      {(log.request_data || log.response_data) && (
                        <span className="text-muted-foreground shrink-0">
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
                          className="overflow-hidden mb-2"
                        >
                          <div className="bg-muted rounded-lg p-3 ml-6 space-y-2">
                            {log.request_data && (
                              <div>
                                <span className="text-sm font-medium text-muted-foreground">Request:</span>
                                <pre className="text-xs text-foreground mt-1 whitespace-pre-wrap break-all">
                                  {JSON.stringify(log.request_data, null, 2)}
                                </pre>
                              </div>
                            )}
                            {log.response_data && (
                              <div>
                                <span className="text-sm font-medium text-muted-foreground">Response:</span>
                                <pre className="text-xs text-foreground mt-1 whitespace-pre-wrap break-all">
                                  {JSON.stringify(log.response_data, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))
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
