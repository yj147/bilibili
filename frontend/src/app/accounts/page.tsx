"use client";

import React, { useState, useEffect, useRef, useReducer } from "react";
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
} from "lucide-react";
import { api } from "@/lib/api";
import { useAccounts } from "@/lib/swr";
import { parseDateWithUtcFallback } from "@/lib/datetime";
import type { Account, AccountPublic } from "@/lib/types";
import QRLoginModal from "@/components/QRLoginModal";
import { toast, Toaster } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useConfirm } from "@/components/ConfirmDialog";

type LoadingState = {
  checking: Set<number>;
  refreshing: Set<number>;
  editing: Set<number>;
};

type LoadingAction =
  | { type: "ADD_CHECKING"; id: number }
  | { type: "REMOVE_CHECKING"; id: number }
  | { type: "ADD_REFRESHING"; id: number }
  | { type: "REMOVE_REFRESHING"; id: number }
  | { type: "ADD_EDITING"; id: number }
  | { type: "REMOVE_EDITING"; id: number };

function loadingReducer(state: LoadingState, action: LoadingAction): LoadingState {
  switch (action.type) {
    case "ADD_CHECKING":
      return { ...state, checking: new Set(state.checking).add(action.id) };
    case "REMOVE_CHECKING": {
      const newSet = new Set(state.checking);
      newSet.delete(action.id);
      return { ...state, checking: newSet };
    }
    case "ADD_REFRESHING":
      return { ...state, refreshing: new Set(state.refreshing).add(action.id) };
    case "REMOVE_REFRESHING": {
      const newSet = new Set(state.refreshing);
      newSet.delete(action.id);
      return { ...state, refreshing: newSet };
    }
    case "ADD_EDITING":
      return { ...state, editing: new Set(state.editing).add(action.id) };
    case "REMOVE_EDITING": {
      const newSet = new Set(state.editing);
      newSet.delete(action.id);
      return { ...state, editing: newSet };
    }
  }
}

export default function AccountsPage() {
  const { data: accounts = [], error, mutate, isValidating } = useAccounts();
  const loading = isValidating;
  const { confirm, ConfirmDialog } = useConfirm();
  const [showAddModal, setShowAddModal] = useState(false);
  const [showQRModal, setShowQRModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isCheckingAll, setIsCheckingAll] = useState(false);
  const [loadingState, dispatch] = useReducer(loadingReducer, {
    checking: new Set<number>(),
    refreshing: new Set<number>(),
    editing: new Set<number>(),
  });
  const notifiedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    for (const acc of accounts) {
      if (acc.status === "valid") {
        notifiedRef.current.delete(`${acc.id}-invalid`);
        continue;
      }
      if (acc.status !== "expiring" && acc.status !== "invalid") {
        continue;
      }

      const notifyKey = `${acc.id}-${acc.status}`;
      if (notifiedRef.current.has(notifyKey)) {
        continue;
      }

      notifiedRef.current.add(notifyKey);
      if (acc.status === "expiring") {
        toast.warning("[" + acc.name + "] Cookie 即将过期，请刷新或重新扫码登录");
      } else if (acc.status === "invalid") {
        toast.error("[" + acc.name + "] Cookie 已失效，请重新扫码登录");
      }
    }
  }, [accounts]);

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
      toast.success("账号添加成功");
    } catch {
      toast.error("添加失败，请检查填写内容");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = async (acc: AccountPublic) => {
    dispatch({ type: "ADD_EDITING", id: acc.id });
    try {
      const detail = await api.accounts.get(acc.id);
      if (typeof detail.sessdata !== "string" || typeof detail.bili_jct !== "string") {
        toast.error("账号详情缺少凭据字段，无法编辑");
        return;
      }

      setEditingAccount(detail);
      setEditFormData({
        name: detail.name,
        sessdata: detail.sessdata,
        bili_jct: detail.bili_jct,
        buvid3: detail.buvid3 || "",
        buvid4: detail.buvid4 || "",
        group_tag: detail.group_tag || "default",
        is_active: detail.is_active,
      });
      setShowEditModal(true);
    } catch {
      toast.error("加载账号详情失败");
    } finally {
      dispatch({ type: "REMOVE_EDITING", id: acc.id });
    }
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
      toast.success("账号更新成功");
    } catch {
      toast.error("更新失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCheck = async (id: number) => {
    dispatch({ type: "ADD_CHECKING", id });
    try {
      await api.accounts.check(id);
      mutate();
      toast.success("检测完成");
    } catch (err) {
      console.error("Check failed", err);
      toast.error("检测失败");
    } finally {
      dispatch({ type: "REMOVE_CHECKING", id });
    }
  };

  const handleCheckAll = async () => {
    setIsCheckingAll(true);
    try {
      const result = await api.accounts.checkAll();
      mutate();
      toast.success(`批量检测完成（${result.checked} 个账号）`);
    } catch (err) {
      console.error("Batch check failed", err);
      toast.error("批量检测失败");
    } finally {
      setIsCheckingAll(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await mutate();
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRefreshCookie = async (id: number) => {
    dispatch({ type: "ADD_REFRESHING", id });
    try {
      const result = await api.auth.refreshCookies(id);
      if (result.success) {
        mutate();
        toast.success("Cookie 刷新成功");
      } else {
        toast.error(result.message || "Cookie 刷新失败");
      }
    } catch {
      toast.error("Cookie 刷新请求失败");
    } finally {
      dispatch({ type: "REMOVE_REFRESHING", id });
    }
  };

  const handleDelete = async (id: number) => {
    if (!await confirm({ description: "确定要移除此账号吗？", variant: "destructive", confirmText: "移除" })) return;
    try {
      await api.accounts.delete(id);
      mutate();
      toast.success("账号已移除");
    } catch (err) {
      console.error("Delete failed", err);
      toast.error("删除失败");
    }
  };

  const statusDisplay = (status: string) => {
    switch (status) {
      case "valid":
        return { label: "正常", className: "border-green-500/30 text-green-600" };
      case "expiring":
        return { label: "即将过期", className: "border-yellow-500/30 text-yellow-600" };
      case "invalid":
        return { label: "已失效", className: "border-red-500/30 text-red-600" };
      default:
        return { label: "未知", className: "border-muted text-muted-foreground" };
    }
  };

  const formatLastCheckAt = (lastCheckAt: string) => {
    const date = parseDateWithUtcFallback(lastCheckAt);
    return date.toLocaleString();
  };

  if (error) {
    return (
      <div className="error-state">
        <p>加载失败: {error.message}</p>
        <button onClick={() => mutate()}>重试</button>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Users className="text-blue-500" /> 账号管理
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            管理 B站 账号和登录信息
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleCheckAll} disabled={isCheckingAll}>
            {isCheckingAll ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />} 批量检测
          </Button>
          <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw size={16} className={isRefreshing || loading ? "animate-spin" : ""} /> 刷新列表
          </Button>
          <Button variant="secondary" onClick={() => setShowQRModal(true)}>
            <QrCode size={18} /> 扫码登录
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus size={18} /> 手动导入
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden min-h-[400px] card-elevated">
        {loading && accounts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground">
            <Loader2 className="animate-spin mb-4" size={40} />
            <p>加载中...</p>
          </div>
        ) : accounts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground">
            <Users className="mb-4 opacity-30" size={60} />
            <p>暂无账号</p>
            <Button variant="secondary" className="mt-4" onClick={() => setShowQRModal(true)}>
              <QrCode size={16} /> 扫码登录添加
            </Button>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground text-center">状态</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">账号信息</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground text-center">登录状态</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">最后检测</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {accounts.map((acc) => {
                const sd = statusDisplay(acc.status);
                return (
                  <tr key={acc.id} className="hover:bg-muted/30 transition-colors group">
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <div className={`w-2 h-2 rounded-full ${
                          acc.status === "valid" ? "bg-green-500" :
                          acc.status === "expiring" ? "bg-yellow-500" :
                          acc.status === "invalid" ? "bg-red-500" : "bg-zinc-400 animate-pulse"
                        }`} />
                        <span className="sr-only">{sd.label}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-medium text-sm text-foreground">{acc.name}</span>
                        <span className="text-xs text-muted-foreground tracking-tight">
                          UID: {acc.uid || "未同步"} · {acc.group_tag}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Badge variant="outline" className={sd.className}>
                        {acc.status === "expiring" && <AlertTriangle size={10} className="mr-1" />}
                        {sd.label}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-xs text-muted-foreground font-mono">
                      {acc.last_check_at ? formatLastCheckAt(acc.last_check_at) : "从不"}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(acc)}
                          disabled={loadingState.editing.has(acc.id)}
                          aria-label="编辑账号"
                        >
                          {loadingState.editing.has(acc.id) ? <Loader2 size={16} className="animate-spin" /> : <Pencil size={16} />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleCheck(acc.id)}
                          disabled={loadingState.checking.has(acc.id)}
                          aria-label="检测有效性"
                        >
                          {loadingState.checking.has(acc.id) ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRefreshCookie(acc.id)}
                          disabled={loadingState.refreshing.has(acc.id)}
                          aria-label="刷新 Cookie"
                        >
                          {loadingState.refreshing.has(acc.id) ? <Loader2 size={16} className="animate-spin" /> : <Cookie size={16} />}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(acc.id)}
                          title="移除账号"
                          className="hover:text-destructive"
                        >
                          <Trash2 size={16} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {/* Manual import modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <Key className="text-blue-500" /> 手动导入账号
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddAccount} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>账号别名</Label>
                <Input
                  required
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如：小号-01"
                />
              </div>
              <div className="space-y-2">
                <Label>账号分组</Label>
                <Select
                  value={formData.group_tag}
                  onValueChange={(val) => setFormData({ ...formData, group_tag: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">默认组</SelectItem>
                    <SelectItem value="report">举报组</SelectItem>
                    <SelectItem value="reply">回复组</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>SESSDATA</Label>
              <Textarea
                required
                value={formData.sessdata}
                onChange={(e) => setFormData({ ...formData, sessdata: e.target.value })}
                placeholder="粘贴 Cookie 中的 SESSDATA 值..."
                className="h-20 resize-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>bili_jct (CSRF)</Label>
                <Input
                  required
                  type="text"
                  value={formData.bili_jct}
                  onChange={(e) => setFormData({ ...formData, bili_jct: e.target.value })}
                  placeholder="粘贴 bili_jct 值..."
                />
              </div>
              <div className="space-y-2">
                <Label>buvid3 (可选)</Label>
                <Input
                  type="text"
                  value={formData.buvid3}
                  onChange={(e) => setFormData({ ...formData, buvid3: e.target.value })}
                  placeholder="粘贴 buvid3 值..."
                />
              </div>
            </div>
            <Button disabled={isSubmitting} className="w-full" size="lg">
              {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : "添加账号"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit account modal */}
      <Dialog open={showEditModal && !!editingAccount} onOpenChange={setShowEditModal}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <Pencil className="text-orange-500" /> 编辑账号
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>账号别名</Label>
                <Input
                  type="text"
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>账号分组</Label>
                <Select
                  value={editFormData.group_tag}
                  onValueChange={(val) => setEditFormData({ ...editFormData, group_tag: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">默认组</SelectItem>
                    <SelectItem value="report">举报组</SelectItem>
                    <SelectItem value="reply">回复组</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>SESSDATA</Label>
              <Textarea
                value={editFormData.sessdata}
                onChange={(e) => setEditFormData({ ...editFormData, sessdata: e.target.value })}
                className="h-20 resize-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>bili_jct (CSRF)</Label>
                <Input
                  type="text"
                  value={editFormData.bili_jct}
                  onChange={(e) => setEditFormData({ ...editFormData, bili_jct: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>buvid3</Label>
                <Input
                  type="text"
                  value={editFormData.buvid3}
                  onChange={(e) => setEditFormData({ ...editFormData, buvid3: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>buvid4</Label>
                <Input
                  type="text"
                  value={editFormData.buvid4}
                  onChange={(e) => setEditFormData({ ...editFormData, buvid4: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>状态</Label>
                <div className="flex items-center gap-3 h-9 px-3">
                  <Switch
                    checked={editFormData.is_active}
                    onCheckedChange={(checked) => setEditFormData({ ...editFormData, is_active: checked })}
                  />
                  <span className="text-sm text-muted-foreground">
                    {editFormData.is_active ? "启用中" : "已禁用"}
                  </span>
                </div>
              </div>
            </div>
            <Button disabled={isSubmitting} className="w-full" size="lg">
              {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : "保存更改"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* QR Login modal */}
      {showQRModal && (
        <QRLoginModal
          onClose={() => setShowQRModal(false)}
          onSuccess={() => mutate()}
        />
      )}
      <ConfirmDialog />
      <Toaster richColors />
    </div>
  );
}
