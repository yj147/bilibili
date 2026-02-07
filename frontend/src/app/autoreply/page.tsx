"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  MessageSquare, Plus, Search, Trash2,
  ToggleLeft, ToggleRight, MessageCircle, Hash,
  CornerDownRight, Save, Zap, Loader2, X
} from "lucide-react";
import { api } from "@/lib/api";
import type { AutoReplyConfig } from "@/lib/types";

export default function AutoReplyPage() {
  const [rules, setRules] = useState<AutoReplyConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({ keyword: "", response: "", priority: 0 });
  const [defaultReply, setDefaultReply] = useState("抱歉，我现在有点忙，稍后会回复你哦~");
  const [serviceStatus, setServiceStatus] = useState({ is_running: false, active_accounts: 0 });
  const [searchQuery, setSearchQuery] = useState("");

  const fetchData = async () => {
    try {
      setLoading(true);
      const [configs, status] = await Promise.all([
        api.autoreply.getConfigs(),
        api.autoreply.getStatus()
      ]);
      const defaultConfig = configs.find((c) => c.keyword === null);
      if (defaultConfig) setDefaultReply(defaultConfig.response);
      setRules(configs.filter((c) => c.keyword !== null));
      setServiceStatus(status);
    } catch (err) {
      console.error("Failed to fetch autoreply data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleAddRule = async () => {
    try {
      await api.autoreply.createConfig({ ...formData, is_active: true });
      setShowAddModal(false);
      setFormData({ keyword: "", response: "", priority: 0 });
      fetchData();
    } catch { alert("添加失败"); }
  };

  const handleDeleteRule = async (id: number) => {
    if (!confirm("确定删除此规则？")) return;
    try { await api.autoreply.deleteConfig(id); fetchData(); } catch { alert("删除失败"); }
  };

  const handleToggleRule = async (rule: AutoReplyConfig) => {
    try {
      await api.autoreply.updateConfig(rule.id, { is_active: !rule.is_active });
      fetchData();
    } catch { alert("操作失败"); }
  };

  const handleSaveDefault = async () => {
    try {
      const configs = await api.autoreply.getConfigs();
      const existing = configs.find((c) => c.keyword === null);
      if (existing) {
        await api.autoreply.updateConfig(existing.id, { response: defaultReply });
      } else {
        await api.autoreply.createConfig({ keyword: null, response: defaultReply, priority: -1, is_active: true });
      }
      alert("全局配置已保存");
    } catch { alert("保存失败"); }
  };

  const handleToggleService = async () => {
    try {
      if (serviceStatus.is_running) { await api.autoreply.stop(); }
      else { await api.autoreply.start(30); }
      const status = await api.autoreply.getStatus();
      setServiceStatus(status);
    } catch { alert("操作失败"); }
  };

  const filteredRules = rules.filter(r =>
    !searchQuery || r.keyword?.includes(searchQuery) || r.response?.includes(searchQuery)
  );

  return (
    <div className="p-4 md:p-8 relative">
      <div className="absolute top-0 right-0 w-[35%] h-[35%] bg-blue-500/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <MessageSquare className="text-blue-400" /> 自动回复配置
          </h1>
          <p className="text-white/40 text-sm mt-1">设置关键词触发规则，让哨兵替你处理日常私信互动</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleToggleService}
            className={`px-6 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all ${
              serviceStatus.is_running ? 'bg-red-600 hover:bg-red-500' : 'bg-green-600 hover:bg-green-500'
            }`}
          >
            {serviceStatus.is_running ? '停止服务' : '启动服务'}
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-blue-600 px-6 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-blue-500 transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)]"
          >
            <Plus size={18} /> 新增规则
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-card rounded-2xl p-2 flex items-center gap-3 border-white/5 mb-6">
            <Search className="ml-3 text-white/30" size={18} />
            <input
              type="text" placeholder="搜索关键词或回复内容..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none outline-none text-sm w-full py-2 placeholder:text-white/20"
            />
          </div>

          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-white/20" size={32} /></div>
          ) : filteredRules.length === 0 ? (
            <div className="text-center text-white/20 py-20 text-sm italic">暂无回复规则</div>
          ) : filteredRules.map((rule) => (
            <motion.div key={rule.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-2xl p-5 border-white/5 group relative overflow-hidden"
            >
              <div className="flex justify-between items-start mb-4 relative z-10">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400"><Hash size={18} /></div>
                  <div>
                    <h3 className="font-semibold text-white/90">{rule.keyword}</h3>
                    <p className="text-[10px] text-white/30 uppercase tracking-widest">触发关键词 · 优先级 {rule.priority}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => handleToggleRule(rule)} className={`p-2 transition-colors ${rule.is_active ? 'text-blue-400' : 'text-white/20'}`}>
                    {rule.is_active ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                  </button>
                </div>
              </div>
              <div className="flex gap-3 items-start bg-white/5 p-4 rounded-xl border border-white/5">
                <CornerDownRight size={16} className="text-white/20 mt-1 shrink-0" />
                <p className="text-sm text-white/60 leading-relaxed italic">&quot;{rule.response}&quot;</p>
              </div>
              <div className="mt-4 flex justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => handleDeleteRule(rule.id)} className="text-xs flex items-center gap-1.5 text-white/40 hover:text-red-400 transition-colors">
                  <Trash2 size={14} /> 删除
                </button>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="space-y-6">
          <div className="glass-card rounded-3xl p-6 border-white/5">
            <h3 className="text-sm font-bold text-white/70 mb-4 flex items-center gap-2">
              <Zap size={16} className="text-yellow-400" /> 全局兜底回复
            </h3>
            <p className="text-xs text-white/40 mb-4">当没有匹配到任何关键词时，哨兵将发送此回复：</p>
            <textarea
              value={defaultReply} onChange={(e) => setDefaultReply(e.target.value)}
              className="w-full bg-black/40 border border-white/5 rounded-xl p-4 text-sm text-white/60 h-32 focus:border-blue-500/50 outline-none transition-all resize-none"
            />
            <button onClick={handleSaveDefault} className="w-full mt-4 bg-white/5 hover:bg-white/10 py-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all">
              <Save size={14} /> 保存全局配置
            </button>
          </div>

          <div className="glass-card rounded-3xl p-6 border-white/5 overflow-hidden relative">
            <div className="absolute top-0 right-0 p-4 opacity-5"><MessageCircle size={100} /></div>
            <h3 className="text-sm font-bold text-white/70 mb-4">服务状态</h3>
            <div className="space-y-3">
              <div className={`flex items-center gap-2 text-xs p-2 rounded ${serviceStatus.is_running ? 'text-green-400 bg-green-400/10' : 'text-red-400 bg-red-400/10'}`}>
                <span className={`w-2 h-2 rounded-full ${serviceStatus.is_running ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                {serviceStatus.is_running ? '服务运行中' : '服务已停止'}
              </div>
              <div className="text-xs text-white/40">活跃账号: {serviceStatus.active_accounts}</div>
            </div>
          </div>
        </div>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={() => setShowAddModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-md" />
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="glass-card w-full max-w-md rounded-3xl p-8 relative z-10 border-white/10 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">新增回复规则</h2>
              <button onClick={() => setShowAddModal(false)}><X size={20} className="text-white/40" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-white/40 mb-1 block">触发关键词</label>
                <input value={formData.keyword} onChange={(e) => setFormData({...formData, keyword: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none" placeholder="例如：你好" />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">回复内容</label>
                <textarea value={formData.response} onChange={(e) => setFormData({...formData, response: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none h-24 resize-none" placeholder="自动回复内容..." />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">优先级</label>
                <input type="number" value={formData.priority} onChange={(e) => setFormData({...formData, priority: parseInt(e.target.value) || 0})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none" />
              </div>
              <button onClick={handleAddRule} className="w-full bg-blue-600 py-3 rounded-xl font-bold hover:bg-blue-500 transition-all mt-2">确认添加</button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
