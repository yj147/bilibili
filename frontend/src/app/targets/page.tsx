"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Target, Plus, Upload, Trash2, Play, AlertTriangle,
  CheckCircle2, Filter, User, MessageCircle, Loader2, RefreshCw, X
} from "lucide-react";
import { api } from "@/lib/api";
import type { Target as TargetType } from "@/lib/types";

export default function TargetsPage() {
  const [targets, setTargets] = useState<TargetType[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [executingId, setExecutingId] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [formData, setFormData] = useState({ type: "video" as string, identifier: "", reason_id: 1, reason_text: "" });
  const [batchData, setBatchData] = useState({ type: "video" as string, identifiers: "", reason_id: 1, reason_text: "" });

  const fetchTargets = async () => {
    try {
      setLoading(true);
      const data = await api.targets.list();
      setTargets(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch targets", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTargets(); }, []);

  const handleExecute = async (id: number) => {
    setExecutingId(id);
    try { await api.reports.execute(id); fetchTargets(); }
    catch { alert("执行失败，请检查账号状态"); }
    finally { setExecutingId(null); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此目标？")) return;
    try { await api.targets.delete(id); fetchTargets(); }
    catch { alert("删除失败"); }
  };

  const handleAdd = async () => {
    try {
      await api.targets.create(formData);
      setShowAddModal(false);
      setFormData({ type: "video", identifier: "", reason_id: 1, reason_text: "" });
      fetchTargets();
    } catch { alert("添加失败"); }
  };

  const handleBatchAdd = async () => {
    const identifiers = batchData.identifiers.split("\n").map(s => s.trim()).filter(Boolean);
    if (identifiers.length === 0) { alert("请输入至少一个目标"); return; }
    try {
      await api.targets.createBatch({ targets: identifiers.map(id => ({ type: batchData.type, identifier: id })) });
      setShowBatchModal(false);
      setBatchData({ type: "video", identifiers: "", reason_id: 1, reason_text: "" });
      fetchTargets();
    } catch { alert("批量添加失败"); }
  };

  const handleExecuteAll = async () => {
    const pendingIds = targets.filter(t => t.status === 'pending').map(t => t.id);
    if (pendingIds.length === 0) { alert("没有待处理目标"); return; }
    try { await api.reports.executeBatch(pendingIds); fetchTargets(); }
    catch { alert("批量执行失败"); }
  };

  const stats = [
    { label: "总目标数", value: total.toString(), icon: Target, color: "text-blue-400" },
    { label: "待处理", value: targets.filter(t => t.status === 'pending').length.toString(), icon: Filter, color: "text-yellow-400" },
    { label: "已清理", value: targets.filter(t => t.status === 'completed').length.toString(), icon: CheckCircle2, color: "text-green-400" },
    { label: "处理失败", value: targets.filter(t => t.status === 'failed').length.toString(), icon: AlertTriangle, color: "text-red-400" },
  ];

  return (
    <div className="p-4 md:p-8 relative">
      <div className="absolute top-0 right-0 w-[40%] h-[40%] bg-purple-500/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Target className="text-purple-500" /> 目标猎场
          </h1>
          <p className="text-white/40 text-sm mt-1">管理待处理的 BV 号、UID 或评论，设定举报理由与优先级</p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchTargets} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 刷新
          </button>
          <button onClick={() => setShowAddModal(true)} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <Plus size={16} /> 添加目标
          </button>
          <button onClick={() => setShowBatchModal(true)} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <Upload size={16} /> 批量导入
          </button>
          <button onClick={handleExecuteAll}
            className="bg-purple-600 px-6 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-purple-500 transition-all shadow-[0_0_20px_rgba(147,51,234,0.3)]">
            <Play size={18} /> 全域巡航
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {stats.map((stat, i) => (
          <div key={i} className="glass-card rounded-2xl p-4 flex items-center gap-4 border-white/5">
            <div className={`p-3 rounded-xl bg-white/5 ${stat.color}`}><stat.icon size={20} /></div>
            <div>
              <p className="text-[10px] text-white/40 uppercase tracking-wider">{stat.label}</p>
              <p className="text-xl font-bold">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="glass-card rounded-3xl border-white/5 overflow-hidden min-h-[300px]">
        <div className="p-6 border-b border-white/5 flex items-center justify-between bg-white/5">
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-widest">目标执行队列</h3>
        </div>
        {loading && targets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] text-white/20">
            <Loader2 className="animate-spin mb-4" size={32} /><p className="text-sm">正在加载猎场数据...</p>
          </div>
        ) : targets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] text-white/10">
            <Target className="mb-4 opacity-5" size={48} /><p className="text-sm italic">当前猎场空旷，尚未发现攻击目标</p>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {targets.map((target) => (
              <div key={target.id} className="flex items-center justify-between p-4 px-6 hover:bg-white/[0.02] transition-colors group">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-white/30">
                    {target.type === 'video' ? <Play size={18} /> : target.type === 'user' ? <User size={18} /> : <MessageCircle size={18} />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">{target.identifier}</span>
                      <span className={`text-[8px] uppercase tracking-widest px-1.5 py-0.5 rounded ${target.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'}`}>
                        {target.type}
                      </span>
                    </div>
                    <div className="text-[10px] text-white/30 flex items-center gap-2 mt-0.5">
                      <span>理由 ID: {target.reason_id}</span>
                      <span className="w-1 h-1 rounded-full bg-white/10" />
                      <span className="truncate max-w-[200px]">{target.reason_text}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="flex flex-col items-end">
                    <span className={`text-[10px] flex items-center gap-1 font-medium ${
                      target.status === 'completed' ? 'text-green-400' : target.status === 'failed' ? 'text-red-400' : 'text-yellow-400'}`}>
                      {target.status === 'completed' && <CheckCircle2 size={10} />}
                      {target.status === 'failed' && <AlertTriangle size={10} />}
                      {target.status === 'processing' && <Loader2 size={10} className="animate-spin" />}
                      {target.status.toUpperCase()}
                    </span>
                    <span className="text-[8px] text-white/20">重试次数: {target.retry_count}</span>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleExecute(target.id)} disabled={executingId === target.id || target.status === 'processing'}
                      className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-white/60 hover:text-green-400 transition-colors disabled:opacity-50">
                      {executingId === target.id ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                    </button>
                    <button onClick={() => handleDelete(target.id)} className="p-2 hover:bg-red-500/10 rounded-lg text-white/20 hover:text-red-400 transition-colors">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={() => setShowAddModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-md" />
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="glass-card w-full max-w-md rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">添加目标</h2>
              <button onClick={() => setShowAddModal(false)}><X size={20} className="text-white/40" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-white/40 mb-1 block">目标类型</label>
                <select value={formData.type} onChange={(e) => setFormData({...formData, type: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none appearance-none">
                  <option value="video" className="bg-zinc-900">视频 (BV号)</option>
                  <option value="comment" className="bg-zinc-900">评论 (oid:rpid)</option>
                  <option value="user" className="bg-zinc-900">用户 (UID)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">目标标识</label>
                <input value={formData.identifier} onChange={(e) => setFormData({...formData, identifier: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" placeholder="BV号 / oid:rpid / UID" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/40 mb-1 block">举报理由 ID</label>
                  <input type="number" value={formData.reason_id} onChange={(e) => setFormData({...formData, reason_id: parseInt(e.target.value) || 1})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
                </div>
                <div>
                  <label className="text-xs text-white/40 mb-1 block">举报文本</label>
                  <input value={formData.reason_text} onChange={(e) => setFormData({...formData, reason_text: e.target.value})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" placeholder="可选" />
                </div>
              </div>
              <button onClick={handleAdd} className="w-full bg-purple-600 py-3 rounded-xl font-bold hover:bg-purple-500 transition-all mt-2">确认添加</button>
            </div>
          </motion.div>
        </div>
      )}

      {showBatchModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={() => setShowBatchModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-md" />
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="glass-card w-full max-w-md rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">批量导入目标</h2>
              <button onClick={() => setShowBatchModal(false)}><X size={20} className="text-white/40" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-white/40 mb-1 block">目标类型</label>
                <select value={batchData.type} onChange={(e) => setBatchData({...batchData, type: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none appearance-none">
                  <option value="video" className="bg-zinc-900">视频</option>
                  <option value="comment" className="bg-zinc-900">评论</option>
                  <option value="user" className="bg-zinc-900">用户</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">目标列表（每行一个）</label>
                <textarea value={batchData.identifiers} onChange={(e) => setBatchData({...batchData, identifiers: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none h-32 resize-none font-mono"
                  placeholder={"BV1xx411c7xx\nBV1yy411c8yy\nBV1zz411c9zz"} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/40 mb-1 block">举报理由 ID</label>
                  <input type="number" value={batchData.reason_id} onChange={(e) => setBatchData({...batchData, reason_id: parseInt(e.target.value) || 1})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
                </div>
                <div>
                  <label className="text-xs text-white/40 mb-1 block">举报文本</label>
                  <input value={batchData.reason_text} onChange={(e) => setBatchData({...batchData, reason_text: e.target.value})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" placeholder="可选" />
                </div>
              </div>
              <button onClick={handleBatchAdd} className="w-full bg-purple-600 py-3 rounded-xl font-bold hover:bg-purple-500 transition-all mt-2">确认导入</button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
