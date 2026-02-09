"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Target, Plus, Upload, Trash2, Play, AlertTriangle,
  CheckCircle2, Filter, User, MessageCircle, Loader2, RefreshCw, X, Pencil,
  ChevronLeft, ChevronRight, Search
} from "lucide-react";
import { api } from "@/lib/api";
import { useTargets, useAccounts } from "@/lib/swr";
import type { Target as TargetType, CommentScanResult } from "@/lib/types";
import ToastContainer, { ToastItem, createToast } from "@/components/Toast";

export default function TargetsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const queryParams: Record<string, string> = { page: page.toString(), page_size: pageSize.toString() };
  if (statusFilter) queryParams.status = statusFilter;
  if (typeFilter) queryParams.type = typeFilter;

  const { data: targetData, mutate, isLoading } = useTargets(queryParams);
  const { data: accounts = [] } = useAccounts();
  const targets = targetData?.items ?? [];
  const total = targetData?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const loading = isLoading;

  const [executingId, setExecutingId] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTarget, setEditingTarget] = useState<TargetType | null>(null);
  const [formData, setFormData] = useState({ type: "video" as string, identifier: "", reason_id: 1, reason_content_id: 1, reason_text: "" });
  const [batchData, setBatchData] = useState({ type: "video" as string, identifiers: "", reason_id: 1, reason_content_id: 1, reason_text: "" });
  const [editFormData, setEditFormData] = useState({ reason_id: 1, reason_content_id: 1, reason_text: "", status: "pending" as string });
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanData, setScanData] = useState({ bvid: "", account_id: 0, reason_id: 9, reason_text: "", max_pages: 5, auto_report: false });
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<CommentScanResult | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((type: ToastItem["type"], message: string) => {
    setToasts((prev) => [...prev, createToast(type, message)]);
  }, []);
  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleExecute = async (id: number) => {
    setExecutingId(id);
    try { await api.reports.execute(id); mutate(); addToast("success", "执行成功"); }
    catch { addToast("error", "执行失败，请检查账号状态"); }
    finally { setExecutingId(null); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此目标？")) return;
    try { await api.targets.delete(id); mutate(); addToast("success", "目标已删除"); }
    catch { addToast("error", "删除失败"); }
  };

  const handleAdd = async () => {
    try {
      await api.targets.create(formData);
      setShowAddModal(false);
      setFormData({ type: "video", identifier: "", reason_id: 1, reason_content_id: 1, reason_text: "" });
      mutate();
      addToast("success", "目标添加成功");
    } catch { addToast("error", "添加失败"); }
  };

  const handleBatchAdd = async () => {
    const identifiers = batchData.identifiers.split("\n").map(s => s.trim()).filter(Boolean);
    if (identifiers.length === 0) { addToast("warning", "请输入至少一个目标"); return; }
    try {
      await api.targets.createBatch({
        type: batchData.type,
        identifiers,
        reason_id: batchData.reason_id,
        reason_content_id: batchData.reason_content_id,
        reason_text: batchData.reason_text || undefined,
      });
      setShowBatchModal(false);
      setBatchData({ type: "video", identifiers: "", reason_id: 1, reason_content_id: 1, reason_text: "" });
      mutate();
      addToast("success", `已导入 ${identifiers.length} 个目标`);
    } catch { addToast("error", "批量添加失败"); }
  };

  const handleExecuteAll = async () => {
    const pendingIds = targets.filter(t => t.status === 'pending').map(t => t.id);
    if (pendingIds.length === 0) { addToast("warning", "没有待处理目标"); return; }
    try { await api.reports.executeBatch(pendingIds); mutate(); addToast("success", "批量执行已启动"); }
    catch { addToast("error", "批量执行失败"); }
  };

  const handleEdit = (target: TargetType) => {
    setEditingTarget(target);
    setEditFormData({
      reason_id: target.reason_id ?? 1,
      reason_content_id: target.reason_content_id ?? 1,
      reason_text: target.reason_text ?? "",
      status: target.status,
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async () => {
    if (!editingTarget) return;
    try {
      await api.targets.update(editingTarget.id, editFormData);
      setShowEditModal(false);
      setEditingTarget(null);
      mutate();
      addToast("success", "目标更新成功");
    } catch { addToast("error", "更新失败"); }
  };

  const handleBulkDelete = async (status: string) => {
    const label = status === 'completed' ? '已完成' : '失败';
    if (!confirm(`确定清除所有${label}的目标？`)) return;
    try {
      await api.targets.deleteByStatus(status);
      mutate();
      addToast("success", `已清除${label}目标`);
    } catch { addToast("error", "清除失败"); }
  };

  const handleScanComments = async () => {
    if (!scanData.bvid.trim()) { addToast("warning", "请输入BV号"); return; }
    if (!scanData.account_id) { addToast("warning", "请选择账号"); return; }
    setScanning(true);
    setScanResult(null);
    try {
      const result = await api.reports.scanComments({
        bvid: scanData.bvid.trim(),
        account_id: scanData.account_id,
        reason_id: scanData.reason_id,
        reason_text: scanData.reason_text || undefined,
        max_pages: scanData.max_pages,
        auto_report: scanData.auto_report,
      });
      setScanResult(result);
      mutate();
      addToast("success", `扫描完成: 发现 ${result.comments_found} 条评论, 创建 ${result.targets_created} 个目标`);
    } catch (e) {
      addToast("error", e instanceof Error ? e.message : "扫描失败");
    } finally {
      setScanning(false);
    }
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
        <div className="flex gap-3 flex-wrap">
          <button onClick={() => mutate()} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 刷新
          </button>
          <button onClick={() => setShowAddModal(true)} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <Plus size={16} /> 添加目标
          </button>
          <button onClick={() => setShowBatchModal(true)} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <Upload size={16} /> 批量导入
          </button>
          <button onClick={() => { setScanResult(null); setShowScanModal(true); }} className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors">
            <Search size={16} /> 评论扫描
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

      {/* Filters & Pagination Controls */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
        <div className="flex gap-3 flex-wrap">
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs outline-none appearance-none">
            <option value="" className="bg-zinc-900">全部状态</option>
            <option value="pending" className="bg-zinc-900">待处理</option>
            <option value="processing" className="bg-zinc-900">处理中</option>
            <option value="completed" className="bg-zinc-900">已完成</option>
            <option value="failed" className="bg-zinc-900">失败</option>
          </select>
          <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs outline-none appearance-none">
            <option value="" className="bg-zinc-900">全部类型</option>
            <option value="video" className="bg-zinc-900">视频</option>
            <option value="comment" className="bg-zinc-900">评论</option>
            <option value="user" className="bg-zinc-900">用户</option>
          </select>
          <select value={pageSize.toString()} onChange={(e) => { setPageSize(parseInt(e.target.value)); setPage(1); }}
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs outline-none appearance-none">
            <option value="10" className="bg-zinc-900">10 条/页</option>
            <option value="20" className="bg-zinc-900">20 条/页</option>
            <option value="50" className="bg-zinc-900">50 条/页</option>
          </select>
          <button onClick={() => handleBulkDelete('completed')}
            className="glass-card px-3 py-2 rounded-xl text-xs flex items-center gap-1.5 hover:bg-green-500/10 hover:text-green-400 transition-colors">
            <CheckCircle2 size={14} /> 清除已完成
          </button>
          <button onClick={() => handleBulkDelete('failed')}
            className="glass-card px-3 py-2 rounded-xl text-xs flex items-center gap-1.5 hover:bg-red-500/10 hover:text-red-400 transition-colors">
            <AlertTriangle size={14} /> 清除失败
          </button>
        </div>
        <div className="flex items-center gap-2 text-xs text-white/40">
          <span>第 {page}/{totalPages} 页 (共 {total} 条)</span>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30 transition-colors">
            <ChevronLeft size={14} />
          </button>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30 transition-colors">
            <ChevronRight size={14} />
          </button>
        </div>
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
                    <button onClick={() => handleEdit(target)}
                      className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-white/60 hover:text-orange-400 transition-colors">
                      <Pencil size={16} />
                    </button>
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

      {/* Bottom pagination */}
      {total > pageSize && (
        <div className="flex justify-center items-center gap-3 mt-4 text-xs text-white/40">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
            className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30 transition-colors flex items-center gap-1">
            <ChevronLeft size={12} /> 上一页
          </button>
          <span>第 {page} / {totalPages} 页</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
            className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 disabled:opacity-30 transition-colors flex items-center gap-1">
            下一页 <ChevronRight size={12} />
          </button>
        </div>
      )}

      {/* Add single target modal */}
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
                  <label className="text-xs text-white/40 mb-1 block">{formData.type === "user" ? "举报类别" : "举报理由 ID"}</label>
                  {formData.type === "user" ? (
                    <select value={formData.reason_id} onChange={(e) => setFormData({...formData, reason_id: parseInt(e.target.value)})}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none appearance-none">
                      <option value={1} className="bg-zinc-900">色情低俗</option>
                      <option value={2} className="bg-zinc-900">不实信息</option>
                      <option value={3} className="bg-zinc-900">违禁</option>
                      <option value={4} className="bg-zinc-900">人身攻击</option>
                      <option value={5} className="bg-zinc-900">赌博诈骗</option>
                      <option value={6} className="bg-zinc-900">违规引流外链</option>
                    </select>
                  ) : (
                    <input type="number" value={formData.reason_id} onChange={(e) => setFormData({...formData, reason_id: parseInt(e.target.value) || 1})}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
                  )}
                </div>
                <div>
                  {formData.type === "user" ? (
                    <>
                      <label className="text-xs text-white/40 mb-1 block">举报内容</label>
                      <select value={formData.reason_content_id} onChange={(e) => setFormData({...formData, reason_content_id: parseInt(e.target.value)})}
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none appearance-none">
                        <option value={1} className="bg-zinc-900">头像违规</option>
                        <option value={2} className="bg-zinc-900">昵称违规</option>
                        <option value={3} className="bg-zinc-900">签名违规</option>
                      </select>
                    </>
                  ) : (
                    <>
                      <label className="text-xs text-white/40 mb-1 block">举报文本</label>
                      <input value={formData.reason_text} onChange={(e) => setFormData({...formData, reason_text: e.target.value})}
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" placeholder="可选" />
                    </>
                  )}
                </div>
              </div>
              <button onClick={handleAdd} className="w-full bg-purple-600 py-3 rounded-xl font-bold hover:bg-purple-500 transition-all mt-2">确认添加</button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Batch import modal */}
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

      {/* Edit target modal */}
      {showEditModal && editingTarget && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={() => setShowEditModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-md" />
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="glass-card w-full max-w-md rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2"><Pencil size={18} className="text-orange-400" /> 编辑目标</h2>
              <button onClick={() => setShowEditModal(false)}><X size={20} className="text-white/40" /></button>
            </div>
            <div className="mb-4 p-3 bg-white/5 rounded-xl">
              <span className="text-xs text-white/40">目标: </span>
              <span className="text-sm font-mono">{editingTarget.identifier}</span>
              <span className="text-[8px] ml-2 uppercase tracking-widest px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">{editingTarget.type}</span>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/40 mb-1 block">举报理由 ID</label>
                  <input type="number" value={editFormData.reason_id} onChange={(e) => setEditFormData({...editFormData, reason_id: parseInt(e.target.value) || 1})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
                </div>
                <div>
                  <label className="text-xs text-white/40 mb-1 block">内容理由 ID</label>
                  <input type="number" value={editFormData.reason_content_id} onChange={(e) => setEditFormData({...editFormData, reason_content_id: parseInt(e.target.value) || 1})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
                </div>
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">举报文本</label>
                <input value={editFormData.reason_text} onChange={(e) => setEditFormData({...editFormData, reason_text: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">状态</label>
                <select value={editFormData.status} onChange={(e) => setEditFormData({...editFormData, status: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none appearance-none">
                  <option value="pending" className="bg-zinc-900">待处理</option>
                  <option value="processing" className="bg-zinc-900">处理中</option>
                  <option value="completed" className="bg-zinc-900">已完成</option>
                  <option value="failed" className="bg-zinc-900">失败</option>
                </select>
              </div>
              <button onClick={handleEditSubmit} className="w-full bg-orange-600 py-3 rounded-xl font-bold hover:bg-orange-500 transition-all mt-2">保存更改</button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Comment Scan modal */}
      {showScanModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={() => setShowScanModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-md" />
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="glass-card w-full max-w-md rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2"><Search size={18} className="text-cyan-400" /> 评论扫描</h2>
              <button onClick={() => setShowScanModal(false)}><X size={20} className="text-white/40" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-white/40 mb-1 block">BV 号</label>
                <input value={scanData.bvid} onChange={(e) => setScanData({...scanData, bvid: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none font-mono" placeholder="BV1xxxxxxxxxx" />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">使用账号</label>
                <select value={scanData.account_id} onChange={(e) => setScanData({...scanData, account_id: parseInt(e.target.value)})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none appearance-none">
                  <option value={0} className="bg-zinc-900">-- 选择账号 --</option>
                  {accounts.filter(a => a.status === 'valid').map(a => (
                    <option key={a.id} value={a.id} className="bg-zinc-900">{a.name} (UID: {a.uid || '---'})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-white/40 mb-1 block">举报理由 ID</label>
                  <input type="number" value={scanData.reason_id} onChange={(e) => setScanData({...scanData, reason_id: parseInt(e.target.value) || 9})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
                </div>
                <div>
                  <label className="text-xs text-white/40 mb-1 block">最大页数</label>
                  <input type="number" value={scanData.max_pages} onChange={(e) => setScanData({...scanData, max_pages: parseInt(e.target.value) || 5})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" />
                </div>
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">举报文本 (可选)</label>
                <input value={scanData.reason_text} onChange={(e) => setScanData({...scanData, reason_text: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none" placeholder="可选补充说明" />
              </div>
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" checked={scanData.auto_report} onChange={(e) => setScanData({...scanData, auto_report: e.target.checked})}
                  className="w-4 h-4 rounded bg-white/5 border-white/10 accent-purple-500" />
                <span className="text-sm text-white/70">自动举报扫描到的评论</span>
              </label>
              <button onClick={handleScanComments} disabled={scanning}
                className="w-full bg-cyan-600 py-3 rounded-xl font-bold hover:bg-cyan-500 transition-all mt-2 flex items-center justify-center gap-2 disabled:opacity-50">
                {scanning ? <><Loader2 size={16} className="animate-spin" /> 扫描中...</> : <><Search size={16} /> 开始扫描</>}
              </button>
              <AnimatePresence>
                {scanResult && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="bg-white/5 rounded-xl p-4 space-y-2">
                    <h3 className="text-xs text-white/40 uppercase tracking-wider mb-2">扫描结果</h3>
                    <div className="flex justify-between text-sm"><span className="text-white/60">发现评论</span><span className="font-bold text-cyan-400">{scanResult.comments_found}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-white/60">创建目标</span><span className="font-bold text-purple-400">{scanResult.targets_created}</span></div>
                    {scanResult.reports_executed !== undefined && (
                      <div className="flex justify-between text-sm"><span className="text-white/60">已执行举报</span><span className="font-bold text-green-400">{scanResult.reports_executed}</span></div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </div>
      )}

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
