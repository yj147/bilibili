"use client";

import React, { useState } from "react";
import {
  Calendar, Clock, RefreshCw, History,
  CheckCircle2, AlertCircle, Plus, Loader2, Trash2, Pencil
} from "lucide-react";
import { toast, Toaster } from "sonner";
import { api } from "@/lib/api";
import { parseDateWithUtcFallback } from "@/lib/datetime";
import { useSchedulerTasks, useSchedulerHistory } from "@/lib/swr";
import type { ScheduledTask } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useConfirm } from "@/components/ConfirmDialog";

export default function SchedulerPage() {
  const { data: tasks = [], mutate: mutateTasks, isLoading: tasksLoading } = useSchedulerTasks();
  const { data: history = [], mutate: mutateHistory } = useSchedulerHistory(20);
  const loading = tasksLoading;
  const { confirm, ConfirmDialog } = useConfirm();
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null);
  const [formData, setFormData] = useState({
    name: "", task_type: "report_batch" as string,
    cron_expression: "", interval_seconds: 300
  });
  const [editFormData, setEditFormData] = useState({
    name: "", cron_expression: "", interval_seconds: 300,
    config_json: ""
  });

  const handleCreate = async () => {
    try {
      const body: { name: string; task_type: string; cron_expression?: string; interval_seconds?: number } = {
        name: formData.name, task_type: formData.task_type
      };
      if (formData.cron_expression) body.cron_expression = formData.cron_expression;
      else body.interval_seconds = formData.interval_seconds;
      await api.scheduler.createTask(body);
      setShowAddModal(false);
      setFormData({ name: "", task_type: "report_batch", cron_expression: "", interval_seconds: 300 });
      mutateTasks();
      mutateHistory();
      toast.success("任务创建成功");
    } catch { toast.error("创建失败"); }
  };

  const handleToggle = async (id: number) => {
    try {
      await api.scheduler.toggleTask(id);
      mutateTasks();
    } catch { toast.error("操作失败"); }
  };

  const handleDelete = async (id: number) => {
    if (!await confirm({ description: "确定删除此任务？", variant: "destructive", confirmText: "删除" })) return;
    try {
      await api.scheduler.deleteTask(id);
      mutateTasks();
      mutateHistory();
      toast.success("任务已删除");
    } catch { toast.error("删除失败"); }
  };

  const handleEdit = (task: ScheduledTask) => {
    setEditingTask(task);
    setEditFormData({
      name: task.name,
      cron_expression: task.cron_expression || "",
      interval_seconds: task.interval_seconds || 300,
      config_json: task.config_json ? JSON.stringify(task.config_json, null, 2) : "",
    });
    setShowEditModal(true);
  };

  const handleEditSubmit = async () => {
    if (!editingTask) return;
    try {
      const data: Record<string, unknown> = {
        name: editFormData.name,
        cron_expression: editFormData.cron_expression || undefined,
        interval_seconds: editFormData.cron_expression ? undefined : editFormData.interval_seconds,
      };
      if (editFormData.config_json.trim()) {
        try { data.config_json = JSON.parse(editFormData.config_json); }
        catch { toast.error("高级参数格式无效，请检查 JSON 格式"); return; }
      }
      await api.scheduler.updateTask(editingTask.id, data as { name?: string; cron_expression?: string; interval_seconds?: number; config_json?: Record<string, unknown> });
      setShowEditModal(false);
      setEditingTask(null);
      mutateTasks();
      toast.success("任务更新成功");
    } catch { toast.error("更新失败"); }
  };

  return (
    <div className="p-4 md:p-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Calendar className="text-primary" /> 定时任务
          </h1>
          <p className="text-muted-foreground text-sm mt-1">管理自动执行的任务</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => { mutateTasks(); mutateHistory(); }}>
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 刷新
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus size={18} /> 新建任务
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest px-2">任务列表</h3>
          {loading && tasks.length === 0 ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-muted-foreground" size={32} /></div>
          ) : tasks.length === 0 ? (
            <div className="text-center text-muted-foreground py-20 text-sm italic">暂无任务</div>
          ) : tasks.map((task) => (
            <Card key={task.id} className="card-elevated">
              <CardContent className="flex items-center justify-between p-6">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl bg-muted ${task.is_active ? 'text-green-500' : 'text-muted-foreground'}`}>
                    {task.is_active ? <RefreshCw className="animate-spin" size={24} style={{ animationDuration: '4s' }} /> : <Clock size={24} />}
                  </div>
                  <div>
                    <h4 className="font-bold text-lg">{task.name}</h4>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><Clock size={12} /> {task.cron_expression || `${task.interval_seconds}s`}</span>
                      <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
                      <span>类型: {task.task_type === 'report_batch' ? '批量举报' : '自动回复检查'}</span>
                      {task.last_run_at && <>
                        <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
                        <span>上次: {parseDateWithUtcFallback(task.last_run_at).toLocaleString()}</span>
                      </>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={task.is_active ? "default" : "secondary"}>
                    {task.is_active ? '运行中' : '已暂停'}
                  </Badge>
                  <Button variant="ghost" size="icon" onClick={() => handleEdit(task)}>
                    <Pencil size={18} />
                  </Button>
                  <Switch checked={task.is_active} onCheckedChange={() => handleToggle(task.id)} />
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(task.id)} className="text-muted-foreground hover:text-destructive">
                    <Trash2 size={18} />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="space-y-4">
          <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest px-2 flex items-center gap-2">
            <History size={16} /> 执行历史
          </h3>
          <Card>
            <CardContent className="p-6 h-[500px] overflow-y-auto">
              {history.length === 0 ? (
                <div className="text-center text-muted-foreground py-10 text-sm italic">暂无执行记录</div>
              ) : history.map((log, i) => (
                <div key={log.id || i} className="flex items-center gap-3 py-3 border-b last:border-none">
                  {log.success ? <CheckCircle2 size={14} className="text-green-500" /> : <AlertCircle size={14} className="text-red-500" />}
                  <div className="flex-1">
                    <p className="text-xs font-medium">{log.action}</p>
                    <p className="text-xs text-muted-foreground">{parseDateWithUtcFallback(log.executed_at).toLocaleString()}</p>
                  </div>
                  <Badge variant={log.success ? "default" : "destructive"} className="text-xs">
                    {log.success ? '成功' : '失败'}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Create task modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建任务</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>任务名称</Label>
              <Input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})}
                placeholder="例如：每日清理" className="mt-1" />
            </div>
            <div>
              <Label>任务类型</Label>
              <Select value={formData.task_type} onValueChange={(value) => setFormData({...formData, task_type: value})}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="report_batch">批量举报</SelectItem>
                  <SelectItem value="autoreply_poll">自动回复检查</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>定时规则（可选，如 0 2 * * * 表示每天凌晨2点）</Label>
              <Input value={formData.cron_expression} onChange={(e) => setFormData({...formData, cron_expression: e.target.value})}
                placeholder="例如：0 2 * * *" className="mt-1" />
            </div>
            <div>
              <Label>执行间隔（秒）— 不填定时规则时按此间隔重复执行</Label>
              <Input type="number" value={formData.interval_seconds} onChange={(e) => setFormData({...formData, interval_seconds: parseInt(e.target.value) || 300})}
                className="mt-1" />
            </div>
            <Button onClick={handleCreate} className="w-full mt-2">确认创建</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit task modal */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Pencil size={18} /> 编辑任务
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>任务名称</Label>
              <Input value={editFormData.name} onChange={(e) => setEditFormData({...editFormData, name: e.target.value})}
                className="mt-1" />
            </div>
            <div>
              <Label>定时规则</Label>
              <Input value={editFormData.cron_expression} onChange={(e) => setEditFormData({...editFormData, cron_expression: e.target.value})}
                placeholder="留空则使用间隔秒数" className="mt-1" />
            </div>
            <div>
              <Label>间隔秒数</Label>
              <Input type="number" value={editFormData.interval_seconds} onChange={(e) => setEditFormData({...editFormData, interval_seconds: parseInt(e.target.value) || 300})}
                className="mt-1" />
            </div>
            <div>
              <Label>高级参数（可选）</Label>
              <Textarea value={editFormData.config_json} onChange={(e) => setEditFormData({...editFormData, config_json: e.target.value})}
                className="mt-1 h-24 font-mono" placeholder='{"key": "value"}' />
            </div>
            <Button onClick={handleEditSubmit} className="w-full mt-2">保存更改</Button>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog />
      <Toaster richColors />
    </div>
  );
}
