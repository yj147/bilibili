"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Settings,
  Shield,
  Database,
  Bell,
  Eye,
  Github,
  Save,
  Info,
  Loader2
} from "lucide-react";
import { useConfigs, useSystemInfo } from "@/lib/swr";
import { api } from "@/lib/api";
import ToastContainer, { ToastItem, createToast } from "@/components/Toast";

const ConfigSection = ({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) => (
  <div className="glass-card rounded-3xl p-8 border-white/5 space-y-6">
    <div className="flex items-center gap-3 border-b border-white/5 pb-4">
      <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
        <Icon size={20} />
      </div>
      <h3 className="text-lg font-bold">{title}</h3>
    </div>
    <div className="space-y-6">
      {children}
    </div>
  </div>
);

const ConfigItem = ({ label, description, children }: { label: string; description: string; children: React.ReactNode }) => (
  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div className="max-w-md">
      <p className="text-sm font-semibold mb-1">{label}</p>
      <p className="text-xs text-white/40 leading-relaxed">{description}</p>
    </div>
    <div className="shrink-0 min-w-[200px] flex justify-end">
      {children}
    </div>
  </div>
);

export default function ConfigPage() {
  const { data: configs, mutate: mutateConfigs } = useConfigs();
  const { data: systemInfo } = useSystemInfo();
  const [saving, setSaving] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((type: ToastItem["type"], message: string) => {
    setToasts((prev) => [...prev, createToast(type, message)]);
  }, []);
  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const [formState, setFormState] = useState({
    min_delay: "2",
    max_delay: "10",
    ua_rotation: true,
    webhook_url: "",
    notify_level: "error",
    auto_clean_logs: true,
    log_retention_days: "30",
  });

  useEffect(() => {
    if (configs) {
      setFormState(prev => ({
        min_delay: String(configs.min_delay ?? prev.min_delay),
        max_delay: String(configs.max_delay ?? prev.max_delay),
        ua_rotation: Boolean(configs.ua_rotation ?? prev.ua_rotation),
        webhook_url: String(configs.webhook_url ?? prev.webhook_url),
        notify_level: String(configs.notify_level ?? prev.notify_level),
        auto_clean_logs: Boolean(configs.auto_clean_logs ?? prev.auto_clean_logs),
        log_retention_days: String(configs.log_retention_days ?? prev.log_retention_days),
      }));
    }
  }, [configs]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.config.updateBatch({
        min_delay: parseInt(formState.min_delay) || 2,
        max_delay: parseInt(formState.max_delay) || 10,
        ua_rotation: formState.ua_rotation,
        webhook_url: formState.webhook_url,
        notify_level: formState.notify_level,
        auto_clean_logs: formState.auto_clean_logs,
        log_retention_days: parseInt(formState.log_retention_days) || 30,
      });
      mutateConfigs();
      addToast("success", "配置已保存");
    } catch {
      addToast("error", "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-8 relative">
      <div className="absolute top-0 right-0 w-[30%] h-[30%] bg-blue-500/5 blur-[100px] rounded-full pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Settings className="text-zinc-400" /> 系统配置
          </h1>
          <p className="text-white/40 text-sm mt-1">调整 Bili-Sentinel 的全局参数、防封策略与通知集成</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-white/5 border border-white/10 px-6 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-white/10 transition-all disabled:opacity-50"
        >
          {saving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />} 保存所有更改
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Anti-Detection Settings */}
        <ConfigSection title="防封策略" icon={Shield}>
          <ConfigItem
            label="最小执行延迟"
            description="任务执行账号切换时的最小等待时间（秒）。设置过低会增加封号风险。"
          >
            <div className="flex items-center gap-3">
              <input type="range" min="1" max="10" value={formState.min_delay}
                onChange={(e) => setFormState({...formState, min_delay: e.target.value})}
                className="accent-blue-500" />
              <span className="text-xs font-mono text-blue-400">{formState.min_delay}s</span>
            </div>
          </ConfigItem>
          <ConfigItem
            label="最大执行延迟"
            description="任务执行账号切换时的最大等待时间（秒）。"
          >
            <div className="flex items-center gap-3">
              <input type="range" min="10" max="60" value={formState.max_delay}
                onChange={(e) => setFormState({...formState, max_delay: e.target.value})}
                className="accent-blue-500" />
              <span className="text-xs font-mono text-blue-400">{formState.max_delay}s</span>
            </div>
          </ConfigItem>
          <ConfigItem
            label="UA 自动轮换"
            description="每次请求随机选择不同的 User-Agent，模拟不同设备环境。"
          >
            <button onClick={() => setFormState({...formState, ua_rotation: !formState.ua_rotation})}
              className={`w-12 h-6 rounded-full relative p-1 cursor-pointer transition-colors ${formState.ua_rotation ? 'bg-blue-600' : 'bg-zinc-600'}`}>
              <div className={`absolute w-4 h-4 bg-white rounded-full shadow-sm transition-all ${formState.ua_rotation ? 'right-1' : 'left-1'}`} />
            </button>
          </ConfigItem>
        </ConfigSection>

        {/* Integration Settings */}
        <ConfigSection title="通知集成" icon={Bell}>
          <ConfigItem
            label="Webhook 通知"
            description="当任务失败或账号失效时，向指定的 Webhook 发送通知。"
          >
            <input type="text" placeholder="https://..." value={formState.webhook_url}
              onChange={(e) => setFormState({...formState, webhook_url: e.target.value})}
              className="bg-black/40 border border-white/5 rounded-lg px-3 py-2 text-xs w-full focus:border-blue-500 outline-none" />
          </ConfigItem>
          <ConfigItem
            label="通知级别"
            description="选择哪些类型的日志需要触发通知。"
          >
            <select value={formState.notify_level}
              onChange={(e) => setFormState({...formState, notify_level: e.target.value})}
              className="bg-black/40 border border-white/5 rounded-lg px-3 py-2 text-xs outline-none cursor-pointer">
              <option value="error">仅错误 (Error)</option>
              <option value="warn">错误与警告 (Warn)</option>
              <option value="info">全部日志 (Info)</option>
            </select>
          </ConfigItem>
        </ConfigSection>

        {/* Data Management */}
        <ConfigSection title="数据与存储" icon={Database}>
          <ConfigItem
            label="自动清理日志"
            description="自动删除过期的执行日志以节省空间。"
          >
            <button onClick={() => setFormState({...formState, auto_clean_logs: !formState.auto_clean_logs})}
              className={`w-12 h-6 rounded-full relative p-1 cursor-pointer transition-colors ${formState.auto_clean_logs ? 'bg-blue-600' : 'bg-zinc-600'}`}>
              <div className={`absolute w-4 h-4 bg-white rounded-full shadow-sm transition-all ${formState.auto_clean_logs ? 'right-1' : 'left-1'}`} />
            </button>
          </ConfigItem>
          <ConfigItem
            label="日志保留天数"
            description="日志保留多少天后自动清理。"
          >
            <input type="number" min="1" max="365" value={formState.log_retention_days}
              onChange={(e) => setFormState({...formState, log_retention_days: e.target.value})}
              className="bg-black/40 border border-white/5 rounded-lg px-3 py-2 text-xs w-20 focus:border-blue-500 outline-none text-center" />
          </ConfigItem>
        </ConfigSection>

        {/* System Info */}
        <div className="glass-card rounded-3xl p-8 border-white/5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-zinc-500/10 text-zinc-400">
                <Info size={20} />
              </div>
              <h3 className="text-lg font-bold">关于 Bili-Sentinel</h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between text-xs">
                <span className="text-white/30">内核版本</span>
                <span className="text-white/60">{systemInfo?.version ?? 'loading...'}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-white/30">运行环境</span>
                <span className="text-white/60">{systemInfo ? `Python ${systemInfo.python} · ${systemInfo.platform}` : 'loading...'}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-white/30">在线账号</span>
                <span className="text-white/60">{systemInfo?.accounts ?? '-'}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-white/30">目标总数</span>
                <span className="text-white/60">{systemInfo?.targets ?? '-'}</span>
              </div>
            </div>
          </div>
          <div className="mt-8 flex gap-4">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer"
              className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center gap-2 text-xs transition-all cursor-pointer">
              <Github size={14} /> GitHub
            </a>
            <a href="#" onClick={(e) => { e.preventDefault(); addToast("info", "文档正在建设中"); }}
              className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center gap-2 text-xs transition-all cursor-pointer">
              <Eye size={14} /> 项目文档
            </a>
          </div>
        </div>
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
