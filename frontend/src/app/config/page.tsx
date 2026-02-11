"use client";

import React, { useState, useEffect } from "react";
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
import { toast, Toaster } from "sonner";
import { useConfigs, useSystemInfo } from "@/lib/swr";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ConfigSection = ({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) => (
  <Card className="card-elevated">
    <CardContent className="p-8 space-y-6">
      <div className="flex items-center gap-3 border-b pb-4">
        <div className="p-2 rounded-lg bg-muted text-primary">
          <Icon size={20} />
        </div>
        <h3 className="text-lg font-bold">{title}</h3>
      </div>
      <div className="space-y-6">
        {children}
      </div>
    </CardContent>
  </Card>
);

const ConfigItem = ({ label, description, children }: { label: string; description: string; children: React.ReactNode }) => (
  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div className="max-w-md">
      <p className="text-sm font-semibold mb-1">{label}</p>
      <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
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
      toast.success("配置已保存");
    } catch {
      toast.error("保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Settings className="text-primary" /> 设置
          </h1>
          <p className="text-muted-foreground text-sm mt-1">调整系统运行参数</p>
        </div>
        <Button onClick={handleSave} disabled={saving} variant="outline">
          {saving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />} 保存所有更改
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Anti-Detection Settings */}
        <ConfigSection title="安全防护" icon={Shield}>
          <ConfigItem
            label="最小执行延迟"
            description="切换账号时的最短等待时间。设置太短容易被封号。"
          >
            <div className="flex items-center gap-3">
              <input type="range" min="1" max="10" value={formState.min_delay}
                onChange={(e) => setFormState({...formState, min_delay: e.target.value})}
                className="accent-primary" />
              <span className="text-xs font-mono text-primary">{formState.min_delay}s</span>
            </div>
          </ConfigItem>
          <ConfigItem
            label="最大执行延迟"
            description="切换账号时的最长等待时间。"
          >
            <div className="flex items-center gap-3">
              <input type="range" min="10" max="60" value={formState.max_delay}
                onChange={(e) => setFormState({...formState, max_delay: e.target.value})}
                className="accent-primary" />
              <span className="text-xs font-mono text-primary">{formState.max_delay}s</span>
            </div>
          </ConfigItem>
          <ConfigItem
            label="设备伪装"
            description="每次操作模拟不同的设备和浏览器，降低被识别的风险。"
          >
            <Switch checked={formState.ua_rotation} onCheckedChange={(checked) => setFormState({...formState, ua_rotation: checked})} />
          </ConfigItem>
        </ConfigSection>

        {/* Integration Settings */}
        <ConfigSection title="通知集成" icon={Bell}>
          <ConfigItem
            label="消息推送"
            description="任务失败或账号失效时，自动发送提醒到指定地址。"
          >
            <Input type="text" placeholder="https://..." value={formState.webhook_url}
              onChange={(e) => setFormState({...formState, webhook_url: e.target.value})}
              className="text-xs w-full" />
          </ConfigItem>
          <ConfigItem
            label="通知级别"
            description="选择哪些情况下发送提醒。"
          >
            <Select value={formState.notify_level} onValueChange={(value) => setFormState({...formState, notify_level: value})}>
              <SelectTrigger className="text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="error">仅失败时</SelectItem>
                <SelectItem value="warn">失败和异常时</SelectItem>
                <SelectItem value="info">所有情况</SelectItem>
              </SelectContent>
            </Select>
          </ConfigItem>
        </ConfigSection>

        {/* Data Management */}
        <ConfigSection title="数据与存储" icon={Database}>
          <ConfigItem
            label="自动清理日志"
            description="自动删除过期的执行日志以节省空间。"
          >
            <Switch checked={formState.auto_clean_logs} onCheckedChange={(checked) => setFormState({...formState, auto_clean_logs: checked})} />
          </ConfigItem>
          <ConfigItem
            label="日志保留天数"
            description="日志保留多少天后自动清理。"
          >
            <Input type="number" min={1} max={365} value={formState.log_retention_days}
              onChange={(e) => setFormState({...formState, log_retention_days: e.target.value})}
              className="text-xs w-20 text-center" />
          </ConfigItem>
        </ConfigSection>

        {/* System Info */}
        <Card className="card-elevated">
          <CardContent className="p-8 flex flex-col justify-between h-full">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-muted text-muted-foreground">
                  <Info size={20} />
                </div>
                <h3 className="text-lg font-bold">关于 Bili-Sentinel</h3>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">系统版本</span>
                  <span>{systemInfo?.version ?? '加载中...'}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">运行环境</span>
                  <span>{systemInfo ? `Python ${systemInfo.python} · ${systemInfo.platform}` : '加载中...'}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">在线账号</span>
                  <span>{systemInfo?.accounts ?? '-'}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">目标总数</span>
                  <span>{systemInfo?.targets ?? '-'}</span>
                </div>
              </div>
            </div>
            <div className="mt-8 flex gap-4">
              <Button variant="outline" asChild className="flex-1">
                <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                  <Github size={14} /> GitHub
                </a>
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => toast.info("文档正在建设中")}>
                <Eye size={14} /> 项目文档
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Toaster richColors />
    </div>
  );
}
