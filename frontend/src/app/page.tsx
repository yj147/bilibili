"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users,
  ShieldCheck,
  Activity,
  Terminal,
  Target,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useAccounts, useTargets, useReportLogs } from "@/lib/swr";
import { useLogStream } from "@/lib/websocket";
import BentoCard from "@/components/BentoCard";
import StatItem from "@/components/StatItem";

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
    <div className="min-h-screen bg-black text-white p-4 md:p-8 relative overflow-hidden">
      {/* Background Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full animate-float" />
      <div
        className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-purple-500/10 blur-[120px] rounded-full animate-float"
        style={{ animationDelay: "2s" }}
      />
      <div className="absolute inset-0 bg-grid-white pointer-events-none" />

      {/* Header */}
      <header className="max-w-7xl mx-auto flex justify-between items-center mb-12 relative z-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">
            Bili<span className="text-blue-500">Sentinel</span>
          </h1>
          <p className="text-white/40 text-sm italic">
            Anti-Antifans Studio — 哨兵之眼，正义执行
          </p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={() => mutateAccounts()}
            className="glass-card px-4 py-2 rounded-lg flex items-center gap-2 text-sm hover:bg-white/10 transition-colors"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />{" "}
            同步态势
          </button>
        </div>
      </header>

      {/* Bento Grid */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 grid-rows-auto gap-4 relative z-10">
        {/* Row 1: Key Stats */}
        <BentoCard title="核心概览" icon={Activity} className="md:col-span-2">
          <div className="grid grid-cols-3 gap-8">
            <StatItem label="在线账号" value={stats.accounts} />
            <StatItem
              label="待处理目标"
              value={stats.targets}
              color="text-purple-400"
            />
            <StatItem
              label="今日执行"
              value={stats.logs}
              color="text-green-400"
            />
          </div>
          <div className="mt-8 h-[60px] flex items-end gap-1">
            {dailyCounts.map((count, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${maxCount > 0 ? (count / maxCount) * 100 : 0}%` }}
                  transition={{ delay: i * 0.08, duration: 0.5 }}
                  className="w-full bg-gradient-to-t from-blue-600/50 to-blue-400 rounded-sm min-h-[2px]"
                />
              </div>
            ))}
          </div>
          <div className="flex gap-1 mt-1">
            {dayLabels.map((label, i) => (
              <div key={i} className="flex-1 text-center text-[8px] text-white/30">{label}</div>
            ))}
          </div>
        </BentoCard>

        <BentoCard
          title="账号健康度"
          icon={ShieldCheck}
          className="md:col-span-1"
        >
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-white/70">Cookie 存活</span>
              <span
                className={`text-sm font-bold ${
                  stats.health > 80 ? "text-green-400" : "text-red-400"
                }`}
              >
                {stats.health}%
              </span>
            </div>
            <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${stats.health}%` }}
                className={`h-full ${
                  stats.health > 80 ? "bg-green-500" : "bg-red-500"
                }`}
              />
            </div>
            <p className="text-xs text-white/40 italic">
              哨兵集群状态: {stats.health > 80 ? "优良" : "受损"}
            </p>
          </div>
        </BentoCard>

        <BentoCard title="实时状态" icon={Target} className="md:col-span-1">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs text-green-400 bg-green-400/10 p-2 rounded">
              <CheckCircle2 size={12} /> UA 自动轮换开启
            </div>
            <div className={`flex items-center gap-2 text-xs p-2 rounded ${wsConnected ? 'text-blue-400 bg-blue-400/10' : 'text-yellow-400 bg-yellow-400/10'}`}>
              <Activity size={12} className={wsConnected ? "animate-pulse" : ""} /> {wsConnected ? 'WebSocket 实时链路已打通' : 'WebSocket 连接中...'}
            </div>
            <div className="flex items-center gap-2 text-xs text-purple-400 bg-purple-400/10 p-2 rounded">
              <ShieldCheck size={12} /> 后端引擎 v1.0 运行中
            </div>
          </div>
        </BentoCard>

        {/* Row 2: Accounts & Real-time Logs */}
        <BentoCard
          title="账号矩阵"
          icon={Users}
          className="md:col-span-1 md:row-span-2"
        >
          <div className="space-y-4 h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            {accounts.length === 0 ? (
              <div className="text-center text-white/10 mt-20 text-xs italic">
                暂无哨兵在线
              </div>
            ) : (
              accounts.map((acc) => (
                <div
                  key={acc.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        acc.status === "valid"
                          ? "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"
                          : "bg-red-500"
                      }`}
                    />
                    <div>
                      <div className="text-sm font-medium">{acc.name}</div>
                      <div className="text-[10px] text-white/40">
                        UID: {acc.uid || "---"}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </BentoCard>

        <BentoCard
          title="哨兵任务日志"
          icon={Terminal}
          className="md:col-span-3 md:row-span-2"
        >
          <div className="bg-black/50 rounded-xl p-4 font-mono text-[10px] text-green-400/80 h-[400px] overflow-y-auto border border-white/5 custom-scrollbar">
            {logs.length === 0 ? (
              <div className="text-white/20 italic">等待任务下发中...</div>
            ) : (
              logs.map((log) => (
                <div key={log.id}>
                  <div
                    className="mb-1 flex gap-3 border-b border-white/5 pb-1 last:border-none cursor-pointer hover:bg-white/5 rounded px-1 -mx-1"
                    onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
                  >
                    <span className="text-white/30 shrink-0">
                      [{new Date(log.executed_at).toLocaleTimeString()}]
                    </span>
                    <span
                      className={`flex-1 ${log.success ? "text-green-400" : "text-red-400"}`}
                    >
                      Account [{log.account_name}] executed {log.action}
                      {log.success
                        ? "... SUCCESS"
                        : `... FAILED: ${log.error_message}`}
                    </span>
                    {(log.request_data || log.response_data) && (
                      <span className="text-white/20 shrink-0">
                        {expandedLogId === log.id ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
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
                        <div className="bg-white/5 rounded-lg p-3 ml-6 space-y-2">
                          {log.request_data && (
                            <div>
                              <span className="text-blue-400/60">Request:</span>
                              <pre className="text-white/40 text-[9px] mt-1 whitespace-pre-wrap break-all">
                                {JSON.stringify(log.request_data, null, 2)}
                              </pre>
                            </div>
                          )}
                          {log.response_data && (
                            <div>
                              <span className="text-purple-400/60">Response:</span>
                              <pre className="text-white/40 text-[9px] mt-1 whitespace-pre-wrap break-all">
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
            <motion.div
              animate={{ opacity: [1, 0] }}
              transition={{ repeat: Infinity, duration: 1 }}
              className="w-2 h-4 bg-green-500/50 inline-block"
            />
          </div>
        </BentoCard>
      </main>

      <footer className="max-w-7xl mx-auto mt-12 text-center text-white/20 text-xs">
        Bili-Sentinel v1.0.0
      </footer>
    </div>
  );
}
