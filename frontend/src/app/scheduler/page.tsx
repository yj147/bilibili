"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Calendar, Clock, Play, Pause, RefreshCw, History,
  CheckCircle2, AlertCircle, Plus, Loader2, X, Trash2
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

export default function SchedulerPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({
    name: "", task_type: "report_batch" as string,
    cron_expression: "", interval_seconds: 300
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [taskRes, histRes] = await Promise.all([
        fetch(`${API_BASE}/scheduler/tasks`).then(r => r.json()),
        fetch(`${API_BASE}/scheduler/history?limit=20`).then(r => r.json()),
      ]);
      setTasks(taskRes);
      setHistory(histRes);
    } catch (err) {
      console.error("Failed to fetch scheduler data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreate = async () => {
    try {
      const body: any = { name: formData.name, task_type: formData.task_type };
      if (formData.cron_expression) body.cron_expression = formData.cron_expression;
      else body.interval_seconds = formData.interval_seconds;
      await fetch(`${API_BASE}/scheduler/tasks`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
      });
      setShowAddModal(false);
      setFormData({ name: "", task_type: "report_batch", cron_expression: "", interval_seconds: 300 });
      fetchData();
    } catch { alert("创建失败"); }
  };

  const handleToggle = async (id: number) => {
    try {
      await fetch(`${API_BASE}/scheduler/tasks/${id}/toggle`, { method: "POST" });
      fetchData();
    } catch { alert("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此任务？")) return;
    try {
      await fetch(`${API_BASE}/scheduler/tasks/${id}`, { method: "DELETE" });
      fetchData();
    } catch { alert("删除失败"); }
  };

  return (
    <div className="p-4 md:p-8 relative">
      <div className="absolute top-0 right-0 w-[40%] h-[40%] bg-purple-500/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Calendar className="text-purple-400" /> 任务调度中心
          </h1>
          <p className="text-white/40 text-sm mt-1">自动化任务管理，支持 Cron 表达式，让哨兵 7x24 小时待命</p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchData} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 刷新
          </button>
          <button onClick={() => setShowAddModal(true)}
            className="bg-purple-600 px-6 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-purple-500 transition-all shadow-[0_0_20px_rgba(147,51,234,0.3)]">
            <Plus size={18} /> 创建调度任务
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <h3 className="text-sm font-bold text-white/40 uppercase tracking-widest px-2">当前调度队列</h3>
          {loading && tasks.length === 0 ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-white/20" size={32} /></div>
          ) : tasks.length === 0 ? (
            <div className="text-center text-white/20 py-20 text-sm italic">暂无调度任务</div>
          ) : tasks.map((task) => (
            <motion.div key={task.id} whileHover={{ scale: 1.01 }}
              className="glass-card rounded-2xl p-6 border-white/5 flex items-center justify-between group">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl bg-white/5 ${task.is_active ? 'text-green-400' : 'text-zinc-500'}`}>
                  {task.is_active ? <RefreshCw className="animate-spin" size={24} style={{ animationDuration: '4s' }} /> : <Clock size={24} />}
                </div>
                <div>
                  <h4 className="font-bold text-lg">{task.name}</h4>
                  <div className="flex items-center gap-3 mt-1 text-xs text-white/30">
                    <span className="flex items-center gap-1"><Clock size={12} /> {task.cron_expression || `${task.interval_seconds}s`}</span>
                    <span className="w-1 h-1 rounded-full bg-white/10" />
                    <span>类型: {task.task_type === 'report_batch' ? '批量举报' : '私信轮询'}</span>
                    {task.last_run_at && <>
                      <span className="w-1 h-1 rounded-full bg-white/10" />
                      <span>上次: {new Date(task.last_run_at).toLocaleString()}</span>
                    </>}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${task.is_active ? 'bg-green-500/10 text-green-400' : 'bg-zinc-500/10 text-zinc-400'}`}>
                  {task.is_active ? 'ACTIVE' : 'PAUSED'}
                </span>
                <button onClick={() => handleToggle(task.id)} className="p-3 rounded-full bg-white/5 hover:bg-white/10 text-white/40 hover:text-white transition-all">
                  {task.is_active ? <Pause size={18} /> : <Play size={18} />}
                </button>
                <button onClick={() => handleDelete(task.id)} className="p-2 text-white/10 hover:text-red-400 transition-colors">
                  <Trash2 size={18} />
                </button>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white/40 uppercase tracking-widest px-2 flex items-center gap-2">
            <History size={16} /> 执行历史
          </h3>
          <div className="glass-card rounded-3xl p-6 border-white/5 h-[500px] overflow-y-auto custom-scrollbar">
            {history.length === 0 ? (
              <div className="text-center text-white/20 py-10 text-sm italic">暂无执行记录</div>
            ) : history.map((log: any, i: number) => (
              <div key={log.id || i} className="flex items-center gap-3 py-3 border-b border-white/5 last:border-none">
                {log.success ? <CheckCircle2 size={14} className="text-green-500" /> : <AlertCircle size={14} className="text-red-500" />}
                <div className="flex-1">
                  <p className="text-xs font-medium">{log.action}</p>
                  <p className="text-[10px] text-white/30">{new Date(log.executed_at).toLocaleString()}</p>
                </div>
                <span className={`text-[10px] uppercase font-bold ${log.success ? 'text-green-500/50' : 'text-red-500/50'}`}>
                  {log.success ? 'success' : 'failed'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={() => setShowAddModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-md" />
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="glass-card w-full max-w-md rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">创建调度任务</h2>
              <button onClick={() => setShowAddModal(false)}><X size={20} className="text-white/40" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-white/40 mb-1 block">任务名称</label>
                <input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-purple-500 outline-none" placeholder="例如：每日清理" />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">任务类型</label>
                <select value={formData.task_type} onChange={(e) => setFormData({...formData, task_type: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-purple-500 outline-none appearance-none">
                  <option value="report_batch" className="bg-zinc-900">批量举报</option>
                  <option value="autoreply_poll" className="bg-zinc-900">私信轮询</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">Cron 表达式 (可选)</label>
                <input value={formData.cron_expression} onChange={(e) => setFormData({...formData, cron_expression: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-purple-500 outline-none" placeholder="例如：0 2 * * *" />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">间隔秒数 (Cron 为空时使用)</label>
                <input type="number" value={formData.interval_seconds} onChange={(e) => setFormData({...formData, interval_seconds: parseInt(e.target.value) || 300})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-purple-500 outline-none" />
              </div>
              <button onClick={handleCreate} className="w-full bg-purple-600 py-3 rounded-xl font-bold hover:bg-purple-500 transition-all mt-2">确认创建</button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
