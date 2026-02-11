"use client";

import React, { useState } from "react";
import {
  MessageSquare, Plus, Search, Trash2,
  Hash, CornerDownRight, Save, Zap, Loader2, Pencil, MessageCircle
} from "lucide-react";
import { toast, Toaster } from "sonner";
import { api } from "@/lib/api";
import { useAutoReplyConfigs, useAutoReplyStatus } from "@/lib/swr";
import type { AutoReplyConfig } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useConfirm } from "@/components/ConfirmDialog";

export default function AutoReplyPage() {
  const { data: configs = [], mutate: mutateConfigs, isLoading: configsLoading } = useAutoReplyConfigs();
  const { data: serviceStatus = { is_running: false, active_accounts: 0 }, mutate: mutateStatus } = useAutoReplyStatus();
  const loading = configsLoading;
  const { confirm, ConfirmDialog } = useConfirm();

  const defaultConfig = configs.find((c) => c.keyword === null);
  const rules = configs.filter((c) => c.keyword !== null);

  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingRule, setEditingRule] = useState<AutoReplyConfig | null>(null);
  const [formData, setFormData] = useState({ keyword: "", response: "", priority: 0 });
  const [editFormData, setEditFormData] = useState({ keyword: "", response: "", priority: 0 });
  const [defaultReply, setDefaultReply] = useState("抱歉，我现在有点忙，稍后会回复你哦~");
  const [defaultReplyInitialized, setDefaultReplyInitialized] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  if (defaultConfig && !defaultReplyInitialized) {
    setDefaultReply(defaultConfig.response);
    setDefaultReplyInitialized(true);
  }

  const handleAddRule = async () => {
    try {
      await api.autoreply.createConfig({ ...formData, is_active: true });
      setShowAddModal(false);
      setFormData({ keyword: "", response: "", priority: 0 });
      mutateConfigs();
      toast.success("规则添加成功");
    } catch { toast.error("添加失败"); }
  };

  const handleDeleteRule = async (id: number) => {
    if (!await confirm({ description: "确定删除此规则？", variant: "destructive", confirmText: "删除" })) return;
    try { await api.autoreply.deleteConfig(id); mutateConfigs(); toast.success("规则已删除"); }
    catch { toast.error("删除失败"); }
  };

  const handleToggleRule = async (rule: AutoReplyConfig) => {
    try {
      await api.autoreply.updateConfig(rule.id, { is_active: !rule.is_active });
      mutateConfigs();
    } catch { toast.error("操作失败"); }
  };

  const handleEditRule = (rule: AutoReplyConfig) => {
    setEditingRule(rule);
    setEditFormData({
      keyword: rule.keyword || "",
      response: rule.response,
      priority: rule.priority,
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async () => {
    if (!editingRule) return;
    try {
      await api.autoreply.updateConfig(editingRule.id, editFormData);
      setShowEditModal(false);
      setEditingRule(null);
      mutateConfigs();
      toast.success("规则更新成功");
    } catch { toast.error("更新失败"); }
  };

  const handleSaveDefault = async () => {
    try {
      const allConfigs = await api.autoreply.getConfigs();
      const existing = allConfigs.find((c) => c.keyword === null);
      if (existing) {
        await api.autoreply.updateConfig(existing.id, { response: defaultReply });
      } else {
        await api.autoreply.createConfig({ keyword: null, response: defaultReply, priority: -1, is_active: true });
      }
      toast.success("全局配置已保存");
    } catch { toast.error("保存失败"); }
  };

  const handleToggleService = async () => {
    try {
      if (serviceStatus.is_running) { await api.autoreply.stop(); }
      else { await api.autoreply.start(30); }
      mutateStatus();
    } catch { toast.error("操作失败"); }
  };

  const filteredRules = rules.filter(r =>
    !searchQuery || r.keyword?.includes(searchQuery) || r.response?.includes(searchQuery)
  );

  return (
    <div className="p-4 md:p-8 relative">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <MessageSquare className="text-primary" /> 自动回复
          </h1>
          <p className="text-muted-foreground text-sm mt-1">设置关键词匹配和自动回复规则</p>
        </div>
        <div className="flex gap-3">
          <Button
            onClick={handleToggleService}
            variant={serviceStatus.is_running ? "destructive" : "default"}
          >
            {serviceStatus.is_running ? '停止服务' : '启动服务'}
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus size={18} /> 新增规则
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="relative mb-6">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
            <Input
              type="text" placeholder="搜索关键词或回复内容..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-muted-foreground" size={32} /></div>
          ) : filteredRules.length === 0 ? (
            <div className="text-center text-muted-foreground py-20 text-sm italic">暂无回复规则</div>
          ) : filteredRules.map((rule) => (
            <Card key={rule.id} className="group relative overflow-hidden card-elevated">
              <CardContent className="p-5">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary"><Hash size={18} /></div>
                    <div>
                      <h3 className="font-semibold text-foreground">{rule.keyword}</h3>
                      <p className="text-xs text-muted-foreground uppercase tracking-widest">触发关键词 · 优先级 {rule.priority}</p>
                    </div>
                  </div>
                  <Switch checked={rule.is_active} onCheckedChange={() => handleToggleRule(rule)} />
                </div>
                <div className="flex gap-3 items-start bg-muted p-4 rounded-xl">
                  <CornerDownRight size={16} className="text-muted-foreground mt-1 shrink-0" />
                  <p className="text-sm text-muted-foreground leading-relaxed italic">&quot;{rule.response}&quot;</p>
                </div>
                <div className="mt-4 flex justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button variant="ghost" size="sm" onClick={() => handleEditRule(rule)}>
                    <Pencil size={14} /> 编辑
                  </Button>
                  <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleDeleteRule(rule.id)}>
                    <Trash2 size={14} /> 删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Zap size={16} className="text-yellow-500" /> 全局兜底回复
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground mb-4">当没有匹配到任何关键词时，将发送此回复：</p>
              <Textarea
                value={defaultReply} onChange={(e) => setDefaultReply(e.target.value)}
                className="h-32 resize-none"
              />
              <Button onClick={handleSaveDefault} variant="outline" className="w-full mt-4">
                <Save size={14} /> 保存全局配置
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <MessageCircle size={16} /> 服务状态
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge variant={serviceStatus.is_running ? "default" : "destructive"}>
                  {serviceStatus.is_running ? '运行中' : '已停止'}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground">活跃账号: {serviceStatus.active_accounts}</div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Add rule modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新增回复规则</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>触发关键词</Label>
              <Input value={formData.keyword} onChange={(e) => setFormData({...formData, keyword: e.target.value})}
                placeholder="例如：你好" className="mt-1" />
            </div>
            <div>
              <Label>回复内容</Label>
              <Textarea value={formData.response} onChange={(e) => setFormData({...formData, response: e.target.value})}
                placeholder="自动回复内容..." className="mt-1 h-24 resize-none" />
            </div>
            <div>
              <Label>优先级</Label>
              <Input type="number" value={formData.priority} onChange={(e) => setFormData({...formData, priority: parseInt(e.target.value) || 0})}
                className="mt-1" />
            </div>
            <Button onClick={handleAddRule} className="w-full">确认添加</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit rule modal */}
      <Dialog open={showEditModal && !!editingRule} onOpenChange={setShowEditModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Pencil size={18} /> 编辑规则</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>触发关键词</Label>
              <Input value={editFormData.keyword} onChange={(e) => setEditFormData({...editFormData, keyword: e.target.value})}
                className="mt-1" />
            </div>
            <div>
              <Label>回复内容</Label>
              <Textarea value={editFormData.response} onChange={(e) => setEditFormData({...editFormData, response: e.target.value})}
                className="mt-1 h-24 resize-none" />
            </div>
            <div>
              <Label>优先级</Label>
              <Input type="number" value={editFormData.priority} onChange={(e) => setEditFormData({...editFormData, priority: parseInt(e.target.value) || 0})}
                className="mt-1" />
            </div>
            <Button onClick={handleEditSubmit} className="w-full">保存更改</Button>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog />
      <Toaster richColors />
    </div>
  );
}
