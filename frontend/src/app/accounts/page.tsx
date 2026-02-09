"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Users,
  Plus,
  ShieldCheck,
  Trash2,
  Key,
  RefreshCw,
  Loader2,
  QrCode,
  AlertTriangle,
  Cookie,
  Pencil,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAccounts } from "@/lib/swr";
import type { Account } from "@/lib/types";
import QRLoginModal from "@/components/QRLoginModal";
import ToastContainer, { ToastItem, createToast } from "@/components/Toast";

export default function AccountsPage() {
  const { data: accounts = [], mutate, isLoading } = useAccounts();
  const loading = isLoading;
  const [showAddModal, setShowAddModal] = useState(false);
  const [showQRModal, setShowQRModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const notifiedRef = useRef<Set<number>>(new Set());

  const addToast = useCallback((type: ToastItem["type"], message: string) => {
    setToasts((prev) => [...prev, createToast(type, message)]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    for (const acc of accounts) {
      if ((acc.status === "expiring" || acc.status === "invalid") && !notifiedRef.current.has(acc.id)) {
        notifiedRef.current.add(acc.id);
        if (acc.status === "expiring") {
          addToast("warning", "[" + acc.name + "] Cookie 即将过期，请刷新或重新扫码登录");
        } else if (acc.status === "invalid") {
          addToast("error", "[" + acc.name + "] Cookie 已失效，请重新扫码登录");
        }
      }
    }
  }, [accounts, addToast]);

  const [formData, setFormData] = useState({
    name: "",
    sessdata: "",
    bili_jct: "",
    buvid3: "",
    group_tag: "default",
  });

  const [editFormData, setEditFormData] = useState({
    name: "",
    sessdata: "",
    bili_jct: "",
    buvid3: "",
    buvid4: "",
    group_tag: "default",
    is_active: true,
  });

  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.accounts.create(formData);
      setShowAddModal(false);
      setFormData({ name: "", sessdata: "", bili_jct: "", buvid3: "", group_tag: "default" });
      mutate();
      addToast("success", "账号添加成功");
    } catch {
      addToast("error", "添加失败，请检查填写内容");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = (acc: Account) => {
    setEditingAccount(acc);
    setEditFormData({
      name: acc.name,
      sessdata: acc.sessdata,
      bili_jct: acc.bili_jct,
      buvid3: acc.buvid3 || "",
      buvid4: acc.buvid4 || "",
      group_tag: acc.group_tag || "default",
      is_active: acc.is_active,
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAccount) return;
    setIsSubmitting(true);
    try {
      await api.accounts.update(editingAccount.id, editFormData);
      setShowEditModal(false);
      setEditingAccount(null);
      mutate();
      addToast("success", "账号更新成功");
    } catch {
      addToast("error", "更新失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCheck = async (id: number) => {
    setCheckingId(id);
    try {
      await api.accounts.check(id);
      mutate();
      addToast("success", "检测完成");
    } catch (err) {
      console.error("Check failed", err);
      addToast("error", "检测失败");
    } finally {
      setCheckingId(null);
    }
  };

  const handleRefreshCookie = async (id: number) => {
    setRefreshingId(id);
    try {
      const result = await api.auth.refreshCookies(id);
      if (result.success) {
        mutate();
        addToast("success", "Cookie 刷新成功");
      } else {
        addToast("error", result.message || "Cookie 刷新失败");
      }
    } catch {
      addToast("error", "Cookie 刷新请求失败");
    } finally {
      setRefreshingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定要移除此哨兵账号吗？")) return;
    try {
      await api.accounts.delete(id);
      mutate();
      addToast("success", "账号已移除");
    } catch (err) {
      console.error("Delete failed", err);
      addToast("error", "删除失败");
    }
  };

  const statusDisplay = (status: string) => {
    switch (status) {
      case "valid":
        return { label: "ACTIVE", dotClass: "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]", badgeClass: "border-green-500/30 text-green-400 bg-green-500/5" };
      case "expiring":
        return { label: "EXPIRING", dotClass: "bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.4)]", badgeClass: "border-yellow-500/30 text-yellow-400 bg-yellow-500/5" };
      case "invalid":
        return { label: "EXPIRED", dotClass: "bg-red-500", badgeClass: "border-red-500/30 text-red-400 bg-red-500/5" };
      default:
        return { label: "UNKNOWN", dotClass: "bg-zinc-600 animate-pulse", badgeClass: "border-zinc-500/30 text-zinc-400 bg-zinc-500/5" };
    }
  };

  return (
    <div className="p-4 md:p-8 relative">
      <div className="absolute top-0 right-0 w-[30%] h-[30%] bg-blue-500/5 blur-[100px] rounded-full pointer-events-none" />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Users className="text-blue-500" /> 账号管理矩阵
          </h1>
          <p className="text-white/40 text-sm mt-1">
            管理并巡检你的哨兵账号，确保 WBI 签名状态正常
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => mutate()}
            className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors cursor-pointer"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 刷新列表
          </button>
          <button
            onClick={() => setShowQRModal(true)}
            className="bg-purple-600 px-5 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-purple-500 transition-all shadow-[0_0_20px_rgba(147,51,234,0.3)] cursor-pointer"
          >
            <QrCode size={18} /> 扫码登录
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-blue-600 px-5 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-blue-500 transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)] cursor-pointer"
          >
            <Plus size={18} /> 手动导入
          </button>
        </div>
      </div>

      <div className="glass-card rounded-3xl overflow-hidden border-white/5 min-h-[400px]">
        {loading && accounts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[400px] text-white/20">
            <Loader2 className="animate-spin mb-4" size={40} />
            <p>正在同步哨兵矩阵...</p>
          </div>
        ) : accounts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[400px] text-white/20">
            <Users className="mb-4 opacity-10" size={60} />
            <p>尚未接入任何哨兵账号</p>
            <button
              onClick={() => setShowQRModal(true)}
              className="mt-4 px-5 py-2 bg-purple-600 hover:bg-purple-500 rounded-xl text-sm font-medium flex items-center gap-2 text-white transition-colors cursor-pointer"
            >
              <QrCode size={16} /> 扫码登录添加
            </button>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/5 bg-white/5">
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40 text-center">状态</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">账号信息</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40 text-center">凭证状态</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">最后检测</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {accounts.map((acc) => {
                const sd = statusDisplay(acc.status);
                return (
                  <tr key={acc.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-6 py-4 text-center">
                      <div className={`w-2 h-2 rounded-full mx-auto ${sd.dotClass}`} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-medium text-sm">{acc.name}</span>
                        <span className="text-[10px] text-white/30 tracking-tight">
                          UID: {acc.uid || "未同步"} · {acc.group_tag}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border inline-flex items-center gap-1 ${sd.badgeClass}`}>
                        {acc.status === "expiring" && <AlertTriangle size={10} />}
                        {sd.label}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-white/50 font-mono text-[10px]">
                      {acc.last_check_at ? new Date(acc.last_check_at).toLocaleString() : "从不"}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => handleEdit(acc)}
                          title="编辑账号"
                          className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-orange-400 transition-colors cursor-pointer"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          onClick={() => handleCheck(acc.id)}
                          disabled={checkingId === acc.id}
                          title="检测有效性"
                          className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-blue-400 transition-colors cursor-pointer"
                        >
                          {checkingId === acc.id ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                        </button>
                        <button
                          onClick={() => handleRefreshCookie(acc.id)}
                          disabled={refreshingId === acc.id}
                          title="刷新 Cookie"
                          className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-yellow-400 transition-colors cursor-pointer"
                        >
                          {refreshingId === acc.id ? <Loader2 size={16} className="animate-spin" /> : <Cookie size={16} />}
                        </button>
                        <button
                          onClick={() => handleDelete(acc.id)}
                          title="移除账号"
                          className="p-2 hover:bg-red-500/20 rounded-lg text-white/40 hover:text-red-400 transition-colors cursor-pointer"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Manual import modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => setShowAddModal(false)}
            className="absolute inset-0 bg-black/80 backdrop-blur-md"
          />
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="glass-card w-full max-w-xl rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl"
          >
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-3 text-glow">
              <Key className="text-blue-500" /> 手动导入凭证
            </h2>
            <form onSubmit={handleAddAccount} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">账号别名</label>
                  <input
                    required
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="例如：哨兵-04"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">账号分组</label>
                  <select
                    value={formData.group_tag}
                    onChange={(e) => setFormData({ ...formData, group_tag: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors appearance-none"
                  >
                    <option value="default" className="bg-zinc-900">默认组</option>
                    <option value="report" className="bg-zinc-900">举报组</option>
                    <option value="reply" className="bg-zinc-900">回复组</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-white/40 ml-1">SESSDATA</label>
                <textarea
                  required
                  value={formData.sessdata}
                  onChange={(e) => setFormData({ ...formData, sessdata: e.target.value })}
                  placeholder="粘贴 Cookie 中的 SESSDATA 值..."
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors h-20 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">bili_jct (CSRF)</label>
                  <input
                    required
                    type="text"
                    value={formData.bili_jct}
                    onChange={(e) => setFormData({ ...formData, bili_jct: e.target.value })}
                    placeholder="粘贴 bili_jct 值..."
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">buvid3 (可选)</label>
                  <input
                    type="text"
                    value={formData.buvid3}
                    onChange={(e) => setFormData({ ...formData, buvid3: e.target.value })}
                    placeholder="粘贴 buvid3 值..."
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors"
                  />
                </div>
              </div>
              <button
                disabled={isSubmitting}
                className="w-full bg-blue-600 py-4 rounded-xl font-bold hover:bg-blue-500 transition-all shadow-[0_0_30px_rgba(37,99,235,0.4)] mt-4 flex items-center justify-center gap-2 cursor-pointer"
              >
                {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : "立即接入哨兵矩阵"}
              </button>
            </form>
          </motion.div>
        </div>
      )}

      {/* Edit account modal */}
      {showEditModal && editingAccount && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => setShowEditModal(false)}
            className="absolute inset-0 bg-black/80 backdrop-blur-md"
          />
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="glass-card w-full max-w-xl rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl"
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold flex items-center gap-3">
                <Pencil className="text-orange-400" /> 编辑账号
              </h2>
              <button onClick={() => setShowEditModal(false)}><X size={20} className="text-white/40" /></button>
            </div>
            <form onSubmit={handleEditSubmit} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">账号别名</label>
                  <input
                    type="text"
                    value={editFormData.name}
                    onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-orange-500 outline-none transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">账号分组</label>
                  <select
                    value={editFormData.group_tag}
                    onChange={(e) => setEditFormData({ ...editFormData, group_tag: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-orange-500 outline-none transition-colors appearance-none"
                  >
                    <option value="default" className="bg-zinc-900">默认组</option>
                    <option value="report" className="bg-zinc-900">举报组</option>
                    <option value="reply" className="bg-zinc-900">回复组</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-white/40 ml-1">SESSDATA</label>
                <textarea
                  value={editFormData.sessdata}
                  onChange={(e) => setEditFormData({ ...editFormData, sessdata: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-orange-500 outline-none transition-colors h-20 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">bili_jct (CSRF)</label>
                  <input
                    type="text"
                    value={editFormData.bili_jct}
                    onChange={(e) => setEditFormData({ ...editFormData, bili_jct: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-orange-500 outline-none transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">buvid3</label>
                  <input
                    type="text"
                    value={editFormData.buvid3}
                    onChange={(e) => setEditFormData({ ...editFormData, buvid3: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-orange-500 outline-none transition-colors"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">buvid4</label>
                  <input
                    type="text"
                    value={editFormData.buvid4}
                    onChange={(e) => setEditFormData({ ...editFormData, buvid4: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-orange-500 outline-none transition-colors"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">状态</label>
                  <button
                    type="button"
                    onClick={() => setEditFormData({ ...editFormData, is_active: !editFormData.is_active })}
                    className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
                      editFormData.is_active ? 'bg-green-600/20 text-green-400 border border-green-500/30' : 'bg-red-600/20 text-red-400 border border-red-500/30'
                    }`}
                  >
                    {editFormData.is_active ? "启用中" : "已禁用"}
                  </button>
                </div>
              </div>
              <button
                disabled={isSubmitting}
                className="w-full bg-orange-600 py-4 rounded-xl font-bold hover:bg-orange-500 transition-all shadow-[0_0_30px_rgba(234,88,12,0.3)] mt-2 flex items-center justify-center gap-2 cursor-pointer"
              >
                {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : "保存更改"}
              </button>
            </form>
          </motion.div>
        </div>
      )}

      {/* QR Login modal */}
      {showQRModal && (
        <QRLoginModal
          onClose={() => setShowQRModal(false)}
          onSuccess={() => mutate()}
        />
      )}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
