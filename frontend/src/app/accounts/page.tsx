"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  Users, 
  Plus, 
  Search, 
  ShieldCheck, 
  Trash2, 
  ExternalLink, 
  Key,
  RefreshCw,
  AlertCircle,
  Loader2
} from "lucide-react";
import { api } from "@/lib/api";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [checkingId, setCheckingId] = useState<number | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    sessdata: "",
    bili_jct: "",
    buvid3: "",
    group_tag: "default"
  });

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const data = await api.accounts.list();
      setAccounts(data);
    } catch (err) {
      console.error("Failed to fetch accounts", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.accounts.create(formData);
      setShowAddModal(false);
      setFormData({ name: "", sessdata: "", bili_jct: "", buvid3: "", group_tag: "default" });
      fetchAccounts();
    } catch (err) {
      alert("添加失败，请检查填写内容");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCheck = async (id: number) => {
    setCheckingId(id);
    try {
      await api.accounts.check(id);
      fetchAccounts();
    } catch (err) {
      console.error("Check failed", err);
    } finally {
      setCheckingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定要移除此哨兵账号吗？")) return;
    try {
      await api.accounts.delete(id);
      fetchAccounts();
    } catch (err) {
      console.error("Delete failed", err);
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
          <p className="text-white/40 text-sm mt-1">管理并巡检你的哨兵账号，确保 WBI 签名状态正常</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={fetchAccounts}
            className="glass-card px-4 py-2 rounded-xl text-sm flex items-center gap-2 hover:bg-white/5 transition-colors"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 刷新列表
          </button>
          <button 
            onClick={() => setShowAddModal(true)}
            className="bg-blue-600 px-6 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-blue-500 transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)]"
          >
            <Plus size={18} /> 导入新账号
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
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/5 bg-white/5">
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40 text-center">状态</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">账号信息</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40 text-center">WBI 状态</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">最后检测</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {accounts.map((acc, i) => (
                <tr key={acc.id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-6 py-4 text-center">
                    <div className={`w-2 h-2 rounded-full mx-auto ${acc.status === 'valid' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : acc.status === 'invalid' ? 'bg-red-500' : 'bg-zinc-600 animate-pulse'}`} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="font-medium text-sm">{acc.name}</span>
                      <span className="text-[10px] text-white/30 tracking-tight">UID: {acc.uid || '未同步'} · {acc.group_tag}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                      acc.status === 'valid' ? 'border-green-500/30 text-green-400 bg-green-500/5' : 'border-red-500/30 text-red-400 bg-red-500/5'
                    }`}>
                      {acc.status === 'valid' ? 'ACTIVE' : 'EXPIRED'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-white/50 font-mono text-[10px]">
                    {acc.last_check_at ? new Date(acc.last_check_at).toLocaleString() : '从不'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button 
                        onClick={() => handleCheck(acc.id)}
                        disabled={checkingId === acc.id}
                        className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-blue-400 transition-colors disabled:animate-spin"
                      >
                        <ShieldCheck size={16} />
                      </button>
                      <button 
                        onClick={() => handleDelete(acc.id)}
                        className="p-2 hover:bg-red-500/20 rounded-lg text-white/40 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

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
              <Key className="text-blue-500" /> 导入 Bilibili 凭证
            </h2>
            <form onSubmit={handleAddAccount} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">账号别名</label>
                  <input 
                    required
                    type="text" 
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    placeholder="例如：哨兵-04" 
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors" 
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">账号分组</label>
                  <select 
                    value={formData.group_tag}
                    onChange={(e) => setFormData({...formData, group_tag: e.target.value})}
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
                  onChange={(e) => setFormData({...formData, sessdata: e.target.value})}
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
                    onChange={(e) => setFormData({...formData, bili_jct: e.target.value})}
                    placeholder="粘贴 bili_jct 值..." 
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors" 
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-white/40 ml-1">buvid3 (可选)</label>
                  <input 
                    type="text" 
                    value={formData.buvid3}
                    onChange={(e) => setFormData({...formData, buvid3: e.target.value})}
                    placeholder="粘贴 buvid3 值..." 
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors" 
                  />
                </div>
              </div>
              <button 
                disabled={isSubmitting}
                className="w-full bg-blue-600 py-4 rounded-xl font-bold hover:bg-blue-500 transition-all shadow-[0_0_30px_rgba(37,99,235,0.4)] mt-4 flex items-center justify-center gap-2"
              >
                {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : "立即接入哨兵矩阵"}
              </button>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
}