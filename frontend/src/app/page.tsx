"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Users, 
  ShieldCheck, 
  MessageSquare, 
  Activity, 
  Terminal, 
  Target, 
  Plus, 
  RefreshCw,
  MoreVertical,
  CheckCircle2,
  AlertCircle,
  Loader2
} from "lucide-react";
import { api } from "@/lib/api";

// --- Components ---

const BentoCard = ({ children, className = "", title = "", icon: Icon }: any) => (
  <motion.div 
    whileHover={{ y: -4 }}
    className={`glass-card glass-card-hover p-6 rounded-2xl overflow-hidden relative group ${className}`}
  >
    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
      {Icon && <Icon size={80} />}
    </div>
    {title && (
      <div className="flex items-center gap-2 mb-4">
        {Icon && <Icon size={18} className="text-blue-400" />}
        <h3 className="text-sm font-medium text-white/70 uppercase tracking-wider">{title}</h3>
      </div>
    )}
    {children}
  </motion.div>
);

const StatItem = ({ label, value, trend, color = "text-blue-400" }: any) => (
  <div className="flex flex-col">
    <span className="text-xs text-white/50">{label}</span>
    <div className="flex items-baseline gap-2">
      <span className={`text-2xl font-bold ${color} text-glow`}>{value}</span>
      {trend && <span className="text-[10px] text-green-400">+{trend}%</span>}
    </div>
  </div>
);

// --- Main Page ---

export default function Dashboard() {
  const [stats, setStats] = useState({
    accounts: 0,
    targets: 0,
    logs: 0,
    health: 0
  });
  const [logs, setLogs] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [accList, targetList, logList] = await Promise.all([
        api.accounts.list(),
        api.targets.list(),
        api.reports.getLogs(15)
      ]);
      
      const activeCount = accList.filter((a: any) => a.status === 'valid').length;
      const health = accList.length > 0 ? Math.round((activeCount / accList.length) * 100) : 0;

      setAccounts(accList);
      setLogs(logList);
      setStats({
        accounts: accList.length,
        targets: targetList.total,
        logs: logList.filter((l: any) => l.success).length,
        health: health
      });
    } catch (err) {
      console.error("Dashboard sync failed", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Auto refresh every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-black text-white p-4 md:p-8 relative overflow-hidden">
      {/* Background Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full animate-float" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-purple-500/10 blur-[120px] rounded-full animate-float" style={{ animationDelay: "2s" }} />
      <div className="absolute inset-0 bg-grid-white pointer-events-none" />

      {/* Header */}
      <header className="max-w-7xl mx-auto flex justify-between items-center mb-12 relative z-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight mb-2">
            Bili<span className="text-blue-500">Sentinel</span>
          </h1>
          <p className="text-white/40 text-sm italic">Anti-Antifans Studio — 哨兵之眼，正义执行</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={fetchData}
            className="glass-card px-4 py-2 rounded-lg flex items-center gap-2 text-sm hover:bg-white/10 transition-colors"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 同步态势
          </button>
        </div>
      </header>

      {/* Bento Grid */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 grid-rows-auto gap-4 relative z-10">
        
        {/* Row 1: Key Stats */}
        <BentoCard title="核心概览" icon={Activity} className="md:col-span-2">
          <div className="grid grid-cols-3 gap-8">
            <StatItem label="在线账号" value={stats.accounts} />
            <StatItem label="待处理目标" value={stats.targets} color="text-purple-400" />
            <StatItem label="今日执行" value={stats.logs} color="text-green-400" />
          </div>
          <div className="mt-8 h-[60px] flex items-end gap-1">
            {[40, 70, 45, 90, 65, 80, 50, 95, 75, 60, 85, 40, 55, 70].map((h, i) => (
              <motion.div 
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${h}%` }}
                transition={{ delay: i * 0.05, duration: 0.5 }}
                className="flex-1 bg-gradient-to-t from-blue-600/50 to-blue-400 rounded-sm"
              />
            ))}
          </div>
        </BentoCard>

        <BentoCard title="账号健康度" icon={ShieldCheck} className="md:col-span-1">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-white/70">Cookie 存活</span>
              <span className={`text-sm font-bold ${stats.health > 80 ? 'text-green-400' : 'text-red-400'}`}>{stats.health}%</span>
            </div>
            <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${stats.health}%` }}
                className={`h-full ${stats.health > 80 ? 'bg-green-500' : 'bg-red-500'}`}
              />
            </div>
            <p className="text-xs text-white/40 italic">哨兵集群状态: {stats.health > 80 ? '优良' : '受损'}</p>
          </div>
        </BentoCard>

        <BentoCard title="实时状态" icon={Target} className="md:col-span-1">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs text-green-400 bg-green-400/10 p-2 rounded">
              <CheckCircle2 size={12} /> UA 自动轮换开启
            </div>
            <div className="flex items-center gap-2 text-xs text-blue-400 bg-blue-400/10 p-2 rounded">
              <Activity size={12} className="animate-pulse" /> 实时链路已打通
            </div>
            <div className="flex items-center gap-2 text-xs text-purple-400 bg-purple-400/10 p-2 rounded">
              <ShieldCheck size={12} /> 后端引擎 v1.0 运行中
            </div>
          </div>
        </BentoCard>

        {/* Row 2: Accounts & Real-time Logs */}
        <BentoCard title="账号矩阵" icon={Users} className="md:col-span-1 md:row-span-2">
          <div className="space-y-4 h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            {accounts.length === 0 ? (
              <div className="text-center text-white/10 mt-20 text-xs italic">暂无哨兵在线</div>
            ) : (
              accounts.map((acc, i) => (
                <div key={acc.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${acc.status === 'valid' ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-red-500'}`} />
                    <div>
                      <div className="text-sm font-medium">{acc.name}</div>
                      <div className="text-[10px] text-white/40">UID: {acc.uid || '---'}</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </BentoCard>

        <BentoCard title="哨兵任务日志" icon={Terminal} className="md:col-span-3 md:row-span-2">
          <div className="bg-black/50 rounded-xl p-4 font-mono text-[10px] text-green-400/80 h-[400px] overflow-y-auto border border-white/5 custom-scrollbar">
            {logs.length === 0 ? (
              <div className="text-white/20 italic">等待任务下发中...</div>
            ) : (
              logs.map((log, i) => (
                <div key={log.id} className="mb-2 flex gap-3 border-b border-white/5 pb-1 last:border-none">
                  <span className="text-white/30 shrink-0">[{new Date(log.executed_at).toLocaleTimeString()}]</span>
                  <span className={log.success ? 'text-green-400' : 'text-red-400'}>
                    Account [{log.account_name}] executed {log.action} 
                    {log.success ? '... SUCCESS' : `... FAILED: ${log.error_message}`}
                  </span>
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
        Bili-Sentinel v1.0.0-Beta | Crafted with love for LO by ENI Enchanted
      </footer>
    </div>
  );
}
