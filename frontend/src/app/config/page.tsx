"use client";

import React from "react";
import { 
  Settings, 
  Shield, 
  Zap, 
  Database, 
  Bell, 
  Lock,
  Eye,
  Github,
  Save,
  Info
} from "lucide-react";

const ConfigSection = ({ title, icon: Icon, children }: any) => (
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

const ConfigItem = ({ label, description, children }: any) => (
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
        <button className="bg-white/5 border border-white/10 px-6 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 hover:bg-white/10 transition-all">
          <Save size={18} /> 保存所有更改
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
              <input type="range" min="1" max="10" defaultValue="2" className="accent-blue-500" />
              <span className="text-xs font-mono text-blue-400">2s</span>
            </div>
          </ConfigItem>
          <ConfigItem 
            label="最大执行延迟" 
            description="任务执行账号切换时的最大等待时间（秒）。"
          >
            <div className="flex items-center gap-3">
              <input type="range" min="10" max="60" defaultValue="10" className="accent-blue-500" />
              <span className="text-xs font-mono text-blue-400">10s</span>
            </div>
          </ConfigItem>
          <ConfigItem 
            label="UA 自动轮换" 
            description="每次请求随机选择不同的 User-Agent，模拟不同设备环境。"
          >
            <div className="w-12 h-6 bg-blue-600 rounded-full relative p-1 cursor-pointer">
              <div className="absolute right-1 w-4 h-4 bg-white rounded-full shadow-sm" />
            </div>
          </ConfigItem>
        </ConfigSection>

        {/* Integration Settings */}
        <ConfigSection title="通知集成" icon={Bell}>
          <ConfigItem 
            label="Webhook 通知" 
            description="当任务失败或账号失效时，向指定的 Webhook 发送通知。"
          >
            <input type="text" placeholder="https://..." className="bg-black/40 border border-white/5 rounded-lg px-3 py-2 text-xs w-full focus:border-blue-500 outline-none" />
          </ConfigItem>
          <ConfigItem 
            label="通知级别" 
            description="选择哪些类型的日志需要触发通知。"
          >
            <select className="bg-black/40 border border-white/5 rounded-lg px-3 py-2 text-xs outline-none cursor-pointer">
              <option>仅错误 (Error)</option>
              <option>错误与警告 (Warn)</option>
              <option>全部日志 (Info)</option>
            </select>
          </ConfigItem>
        </ConfigSection>

        {/* Data Management */}
        <ConfigSection title="数据与存储" icon={Database}>
          <ConfigItem 
            label="自动清理日志" 
            description="保留最近 30 天的执行日志，自动删除过期数据以节省空间。"
          >
             <div className="w-12 h-6 bg-blue-600 rounded-full relative p-1 cursor-pointer">
              <div className="absolute right-1 w-4 h-4 bg-white rounded-full shadow-sm" />
            </div>
          </ConfigItem>
          <ConfigItem 
            label="数据库备份" 
            description="导出当前的 SQLite 数据库备份文件。"
          >
            <button className="text-xs px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors">立即导出</button>
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
                <span className="text-white/60">v1.0.0-beta.4</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-white/30">运行环境</span>
                <span className="text-white/60">Node.js 20.x + FastAPI</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-white/30">作者</span>
                <span className="text-white/60 font-semibold text-blue-400">ENI Enchanted</span>
              </div>
            </div>
          </div>
          <div className="mt-8 flex gap-4">
            <button className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center gap-2 text-xs transition-all">
              <Github size={14} /> GitHub
            </button>
            <button className="flex-1 py-3 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center gap-2 text-xs transition-all">
              <Eye size={14} /> 项目文档
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
