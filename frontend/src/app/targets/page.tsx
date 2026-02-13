"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Target, Plus, Upload, Trash2, Play, AlertTriangle,
  CheckCircle2, Filter, User, MessageCircle, Loader2, RefreshCw, Pencil,
  ChevronLeft, ChevronRight, Search
} from "lucide-react";
import { api } from "@/lib/api";
import { useTargets, useAccounts } from "@/lib/swr";
import { useLogStream } from "@/lib/websocket";
import type { Target as TargetType, CommentScanResult } from "@/lib/types";
import { toast, Toaster } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { useConfirm } from "@/components/ConfirmDialog";

const statusMap: Record<string, string> = {
  pending: "待处理",
  processing: "处理中",
  completed: "已完成",
  failed: "失败",
};

const typeMap: Record<string, string> = {
  video: "视频",
  comment: "评论",
  user: "用户",
};

const videoReasonMap: Record<number, string> = {
  1: "违法违禁",
  2: "色情",
  3: "低质量/刷屏",
  4: "赌博诈骗",
  5: "人身攻击",
  7: "人身攻击",
  8: "侵犯隐私",
  9: "引战",
  10: "青少年不良信息",
  11: "涉政或敏感信息",
};

// B站评论举报只支持 1-9，不支持 10、11
const commentReasonMap: Record<number, string> = {
  1: "违法违禁",
  2: "色情",
  3: "低质量/刷屏",
  4: "赌博诈骗",
  5: "人身攻击",
  7: "侵犯隐私",
  8: "内容不相关",
  9: "引战",
};

const userReasonMap: Record<number, string> = {
  1: "色情低俗",
  2: "不实信息",
  3: "违禁",
  4: "人身攻击",
  5: "赌博诈骗",
  6: "违规引流外链",
};

const userContentReasonMap: Record<number, string> = {
  1: "头像违规",
  2: "昵称违规",
  3: "签名违规",
};

function getReasonLabel(type: string, reasonId: number | null): string {
  if (reasonId == null) return "";
  const map = type === "user" ? userReasonMap : type === "comment" ? commentReasonMap : videoReasonMap;
  return map[reasonId] ?? `理由 #${reasonId}`;
}

function ReasonSelect({ type, value, onChange }: { type: string; value: number; onChange: (v: number) => void }) {
  const map = type === "user" ? userReasonMap : type === "comment" ? commentReasonMap : videoReasonMap;
  return (
    <Select value={value.toString()} onValueChange={(v) => onChange(parseInt(v))}>
      <SelectTrigger><SelectValue /></SelectTrigger>
      <SelectContent>
        {Object.entries(map).map(([k, v]) => (
          <SelectItem key={k} value={k}>{v}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export default function TargetsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [stats, setStats] = useState({ total: 0, pending: 0, processing: 0, completed: 0, failed: 0 });
  const [selectedTargets, setSelectedTargets] = useState<Set<number>>(new Set());

  const queryParams: Record<string, string> = { page: page.toString(), page_size: pageSize.toString() };
  if (statusFilter) queryParams.status = statusFilter;
  if (typeFilter) queryParams.type = typeFilter;

  const { data: targetData, mutate, isLoading } = useTargets(queryParams);
  const { data: accounts = [] } = useAccounts();
  const allTargets = targetData?.items ?? [];

  const targets = useMemo(() => {
    if (!searchKeyword.trim()) return allTargets;
    const keyword = searchKeyword.toLowerCase();
    return allTargets.filter(t =>
      t.identifier.toLowerCase().includes(keyword) ||
      (t.display_text && t.display_text.toLowerCase().includes(keyword))
    );
  }, [allTargets, searchKeyword]);

  const total = targets.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const loading = isLoading;
  const { confirm, ConfirmDialog } = useConfirm();

  // Fetch global statistics
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.targets.stats();
        setStats(data);
      } catch (error) {
        console.error("Failed to fetch stats:", error);
      }
    };
    fetchStats();
  }, []);

  // WebSocket: auto-refresh when a report event arrives
  const { logs: wsLogs } = useLogStream(10);
  const lastWsCountRef = useRef(0);
  useEffect(() => {
    if (wsLogs.length > 0 && wsLogs.length !== lastWsCountRef.current) {
      const latest = wsLogs[0];
      if (latest.type === "report") {
        mutate();
      }
      lastWsCountRef.current = wsLogs.length;
    }
  }, [wsLogs, mutate]);

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

  const handleExecute = async (id: number) => {
    setExecutingId(id);
    try {
      await api.reports.execute(id);
      mutate();
      toast.success("举报已提交，后台执行中");
    } catch { toast.error("执行失败，请检查账号状态"); }
    finally { setExecutingId(null); }
  };

  const handleDelete = async (id: number) => {
    if (!await confirm({ description: "确定删除此目标？", variant: "destructive", confirmText: "删除" })) return;
    try { await api.targets.delete(id); mutate(); toast.success("目标已删除"); }
    catch { toast.error("删除失败"); }
  };

  const handleAdd = async () => {
    try {
      await api.targets.create(formData);
      setShowAddModal(false);
      setFormData({ type: "video", identifier: "", reason_id: 1, reason_content_id: 1, reason_text: "" });
      mutate();
      toast.success("目标添加成功");
    } catch { toast.error("添加失败"); }
  };

  const handleBatchAdd = async () => {
    const identifiers = batchData.identifiers.split("\n").map(s => s.trim()).filter(Boolean);
    if (identifiers.length === 0) { toast.warning("请输入至少一个目标"); return; }
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
      toast.success(`已导入 ${identifiers.length} 个目标`);
    } catch { toast.error("批量添加失败"); }
  };

  const handleToggleSelect = (id: number) => {
    setSelectedTargets(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedTargets.size === targets.length) {
      setSelectedTargets(new Set());
    } else {
      setSelectedTargets(new Set(targets.map(t => t.id)));
    }
  };

  const handleExecuteAll = async () => {
    const selectedIds = Array.from(selectedTargets);
    if (selectedIds.length === 0) { toast.warning("请先选择目标"); return; }
    try {
      await api.reports.executeBatch(selectedIds);
      mutate();
      setSelectedTargets(new Set());
      toast.success("批量执行已启动");
    }
    catch { toast.error("批量执行失败"); }
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
      toast.success("目标更新成功");
    } catch { toast.error("更新失败"); }
  };

  const handleBulkDelete = async (status: string) => {
    const label = status === 'completed' ? '已完成' : '失败';
    if (!await confirm({ description: `确定清除所有${label}的目标？`, variant: "destructive", confirmText: "清除" })) return;
    try {
      await api.targets.deleteByStatus(status);
      mutate();
      toast.success(`已清除${label}目标`);
    } catch { toast.error("清除失败"); }
  };

  const handleScanComments = async () => {
    if (!scanData.bvid.trim()) { toast.warning("请输入BV号"); return; }
    if (!scanData.account_id) { toast.warning("请选择账号"); return; }
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
      toast.success(`扫描完成: 发现 ${result.comments_found} 条评论, 创建 ${result.targets_created} 个目标`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "扫描失败");
    } finally {
      setScanning(false);
    }
  };

  const identifierPlaceholder = (type: string) => {
    switch (type) {
      case "video": return "输入 BV 号";
      case "comment": return "输入 oid:rpid";
      case "user": return "输入用户 UID";
      default: return "";
    }
  };

  const statsCards = [
    { label: "总目标数", value: stats.total.toString(), icon: Target, color: "text-blue-500" },
    { label: "待处理", value: stats.pending.toString(), icon: Filter, color: "text-yellow-500" },
    { label: "已清理", value: stats.completed.toString(), icon: CheckCircle2, color: "text-green-500" },
    { label: "处理失败", value: stats.failed.toString(), icon: AlertTriangle, color: "text-red-500" },
  ];

  return (
    <div className="p-4 md:p-8 relative">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Target className="text-purple-500" /> 举报目标
          </h1>
          <p className="text-muted-foreground text-sm mt-1">管理待举报的视频、评论和用户</p>
        </div>
        <div className="flex gap-3 flex-wrap">
          <Button variant="outline" size="sm" onClick={() => mutate()}>
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> 刷新
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowAddModal(true)}>
            <Plus size={16} /> 添加目标
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowBatchModal(true)}>
            <Upload size={16} /> 批量导入
          </Button>
          <Button variant="outline" size="sm" onClick={() => { setScanResult(null); setShowScanModal(true); }}>
            <Search size={16} /> 评论扫描
          </Button>
          <Button onClick={handleExecuteAll} disabled={selectedTargets.size === 0}>
            <Play size={18} /> 批量执行 {selectedTargets.size > 0 && `(${selectedTargets.size})`}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {statsCards.map((stat, i) => (
          <Card key={i} className="p-4 flex items-center gap-4 card-elevated cursor-default">
            <div className={`p-3 rounded-xl bg-muted ${stat.color}`}><stat.icon size={20} /></div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">{stat.label}</p>
              <p className="text-xl font-bold">{stat.value}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col gap-4 mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
          <Input
            value={searchKeyword}
            onChange={(e) => { setSearchKeyword(e.target.value); setPage(1); }}
            placeholder="搜索 BV号/rpid/uid/评论内容..."
            className="pl-10 h-9"
          />
        </div>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex gap-3 flex-wrap items-center">
            <Select value={statusFilter || "all"} onValueChange={(v) => { setStatusFilter(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-[130px] h-9 text-xs">
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="pending">待处理</SelectItem>
              <SelectItem value="processing">处理中</SelectItem>
              <SelectItem value="completed">已完成</SelectItem>
              <SelectItem value="failed">失败</SelectItem>
            </SelectContent>
          </Select>
          <Select value={typeFilter || "all"} onValueChange={(v) => { setTypeFilter(v === "all" ? "" : v); setPage(1); }}>
            <SelectTrigger className="w-[130px] h-9 text-xs">
              <SelectValue placeholder="全部类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="video">视频</SelectItem>
              <SelectItem value="comment">评论</SelectItem>
              <SelectItem value="user">用户</SelectItem>
            </SelectContent>
          </Select>
          <Select value={pageSize.toString()} onValueChange={(v) => { setPageSize(parseInt(v)); setPage(1); }}>
            <SelectTrigger className="w-[110px] h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10 条/页</SelectItem>
              <SelectItem value="20">20 条/页</SelectItem>
              <SelectItem value="50">50 条/页</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => handleBulkDelete('completed')}>
            <CheckCircle2 size={14} /> 清除已完成
          </Button>
          <Button variant="outline" size="sm" onClick={() => handleBulkDelete('failed')}>
            <AlertTriangle size={14} /> 清除失败
          </Button>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>第 {page}/{totalPages} 页 (共 {total} 条)</span>
          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>
            <ChevronLeft size={14} />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
            <ChevronRight size={14} />
          </Button>
        </div>
        </div>
      </div>

      {/* Target list */}
      <Card className="overflow-hidden min-h-[300px] card-static">
        <div className="p-6 border-b flex items-center justify-between bg-muted/50">
          <div className="flex items-center gap-3">
            {targets.length > 0 && (
              <input
                type="checkbox"
                checked={selectedTargets.size === targets.length && targets.length > 0}
                onChange={handleSelectAll}
                className="w-4 h-4 rounded cursor-pointer"
              />
            )}
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">目标列表</h3>
          </div>
        </div>
        {loading && targets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
            <Loader2 className="animate-spin mb-4" size={32} /><p className="text-sm">正在加载数据...</p>
          </div>
        ) : targets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
            <Target className="mb-4 opacity-20" size={48} /><p className="text-sm">暂无举报目标</p>
          </div>
        ) : (
          <div className="divide-y">
            {targets.map((target) => (
              <div key={target.id} className="flex items-center justify-between p-4 px-6 hover:bg-muted/50 transition-colors group">
                <div className="flex items-center gap-4">
                  <input
                    type="checkbox"
                    checked={selectedTargets.has(target.id)}
                    onChange={() => handleToggleSelect(target.id)}
                    className="w-4 h-4 rounded cursor-pointer"
                  />
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-muted text-muted-foreground">
                    {target.type === 'video' ? <Play size={18} /> : target.type === 'user' ? <User size={18} /> : <MessageCircle size={18} />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">
                        {target.type === 'comment' && target.display_text ? target.display_text : target.identifier}
                      </span>
                      <Badge variant={target.status === 'failed' ? 'destructive' : 'secondary'} className="text-xs tracking-widest">
                        {typeMap[target.type] ?? target.type}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                      <span>举报理由: {getReasonLabel(target.type, target.reason_id)}</span>
                      {target.reason_text && <>
                        <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
                        <span className="truncate max-w-[200px]">{target.reason_text}</span>
                      </>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="flex flex-col items-end">
                    <span className={`text-xs flex items-center gap-1 font-medium ${
                      target.status === 'completed' ? 'text-green-500' : target.status === 'failed' ? 'text-red-500' : 'text-yellow-500'}`}>
                      {target.status === 'completed' && <CheckCircle2 size={10} />}
                      {target.status === 'failed' && <AlertTriangle size={10} />}
                      {target.status === 'processing' && <Loader2 size={10} className="animate-spin" />}
                      {statusMap[target.status] ?? target.status}
                    </span>
                    <span className="text-xs text-muted-foreground">已尝试: {target.retry_count} 次</span>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="icon" onClick={() => handleEdit(target)} className="h-8 w-8" aria-label="编辑目标">
                      <Pencil size={16} />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleExecute(target.id)} disabled={executingId === target.id || target.status === 'processing'} className="h-8 w-8" aria-label="执行举报">
                      {executingId === target.id ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(target.id)} className="h-8 w-8 hover:text-red-500" aria-label="删除目标">
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Bottom pagination */}
      {total > pageSize && (
        <div className="flex justify-center items-center gap-3 mt-4 text-xs text-muted-foreground">
          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>
            <ChevronLeft size={12} /> 上一页
          </Button>
          <span>第 {page} / {totalPages} 页</span>
          <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
            下一页 <ChevronRight size={12} />
          </Button>
        </div>
      )}

      {/* Add single target modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>添加目标</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="mb-1">目标类型</Label>
              <Select value={formData.type} onValueChange={(v) => setFormData({...formData, type: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="video">视频</SelectItem>
                  <SelectItem value="comment">评论</SelectItem>
                  <SelectItem value="user">用户</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1">目标标识</Label>
              <Input value={formData.identifier} onChange={(e) => setFormData({...formData, identifier: e.target.value})}
                placeholder={identifierPlaceholder(formData.type)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">{formData.type === "user" ? "举报类别" : "举报理由"}</Label>
                <ReasonSelect type={formData.type} value={formData.reason_id} onChange={(v) => setFormData({...formData, reason_id: v})} />
              </div>
              <div>
                {formData.type === "user" ? (
                  <>
                    <Label className="mb-1">内容理由</Label>
                    <Select value={formData.reason_content_id.toString()} onValueChange={(v) => setFormData({...formData, reason_content_id: parseInt(v)})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(userContentReasonMap).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </>
                ) : (
                  <>
                    <Label className="mb-1">举报文本</Label>
                    <Input value={formData.reason_text} onChange={(e) => setFormData({...formData, reason_text: e.target.value})}
                      placeholder="可选" />
                  </>
                )}
              </div>
            </div>
            <Button onClick={handleAdd} className="w-full mt-2">确认添加</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Batch import modal */}
      <Dialog open={showBatchModal} onOpenChange={setShowBatchModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>批量导入目标</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="mb-1">目标类型</Label>
              <Select value={batchData.type} onValueChange={(v) => setBatchData({...batchData, type: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="video">视频</SelectItem>
                  <SelectItem value="comment">评论</SelectItem>
                  <SelectItem value="user">用户</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1">目标列表（每行一个）</Label>
              <textarea value={batchData.identifiers} onChange={(e) => setBatchData({...batchData, identifiers: e.target.value})}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring h-32 resize-none font-mono"
                placeholder={"BV1xx411c7xx\nBV1yy411c8yy\nBV1zz411c9zz"} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">举报理由</Label>
                <ReasonSelect type={batchData.type} value={batchData.reason_id} onChange={(v) => setBatchData({...batchData, reason_id: v})} />
              </div>
              <div>
                <Label className="mb-1">举报文本</Label>
                <Input value={batchData.reason_text} onChange={(e) => setBatchData({...batchData, reason_text: e.target.value})}
                  placeholder="可选" />
              </div>
            </div>
            <Button onClick={handleBatchAdd} className="w-full mt-2">确认导入</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit target modal */}
      <Dialog open={showEditModal && !!editingTarget} onOpenChange={setShowEditModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Pencil size={18} className="text-orange-500" /> 编辑目标</DialogTitle>
          </DialogHeader>
          {editingTarget && (
            <>
              <div className="p-3 bg-muted rounded-lg">
                <span className="text-xs text-muted-foreground">目标: </span>
                <span className="text-sm font-mono">{editingTarget.identifier}</span>
                <Badge variant="secondary" className="ml-2 text-xs tracking-widest">{typeMap[editingTarget.type] ?? editingTarget.type}</Badge>
              </div>
              <div className="space-y-4">
                <div>
                  <Label className="mb-1">举报理由</Label>
                  <ReasonSelect type={editingTarget.type} value={editFormData.reason_id} onChange={(v) => setEditFormData({...editFormData, reason_id: v})} />
                </div>
                {editingTarget.type === "user" && (
                  <div>
                    <Label className="mb-1">内容理由</Label>
                    <Select value={editFormData.reason_content_id.toString()} onValueChange={(v) => setEditFormData({...editFormData, reason_content_id: parseInt(v)})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(userContentReasonMap).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div>
                  <Label className="mb-1">举报文本</Label>
                  <Input value={editFormData.reason_text} onChange={(e) => setEditFormData({...editFormData, reason_text: e.target.value})} />
                </div>
                <div>
                  <Label className="mb-1">状态</Label>
                  <Select value={editFormData.status} onValueChange={(v) => setEditFormData({...editFormData, status: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">待处理</SelectItem>
                      <SelectItem value="processing">处理中</SelectItem>
                      <SelectItem value="completed">已完成</SelectItem>
                      <SelectItem value="failed">失败</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleEditSubmit} className="w-full mt-2 bg-orange-600 hover:bg-orange-500">保存更改</Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Comment Scan modal */}
      <Dialog open={showScanModal} onOpenChange={setShowScanModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Search size={18} className="text-cyan-500" /> 评论扫描</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="mb-1">BV 号</Label>
              <Input value={scanData.bvid} onChange={(e) => setScanData({...scanData, bvid: e.target.value})}
                className="font-mono" placeholder="BV1xxxxxxxxxx" />
            </div>
            <div>
              <Label className="mb-1">使用账号</Label>
              <Select value={scanData.account_id.toString()} onValueChange={(v) => setScanData({...scanData, account_id: parseInt(v)})}>
                <SelectTrigger><SelectValue placeholder="-- 选择账号 --" /></SelectTrigger>
                <SelectContent>
                  {accounts.filter(a => a.status === 'valid').map(a => (
                    <SelectItem key={a.id} value={a.id.toString()}>{a.name} (UID: {a.uid || '---'})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-1">举报理由</Label>
                <ReasonSelect type="video" value={scanData.reason_id} onChange={(v) => setScanData({...scanData, reason_id: v})} />
              </div>
              <div>
                <Label className="mb-1">最大页数</Label>
                <Input type="number" value={scanData.max_pages} onChange={(e) => setScanData({...scanData, max_pages: parseInt(e.target.value) || 5})} />
              </div>
            </div>
            <div>
              <Label className="mb-1">举报文本 (可选)</Label>
              <Input value={scanData.reason_text} onChange={(e) => setScanData({...scanData, reason_text: e.target.value})}
                placeholder="可选补充说明" />
            </div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={scanData.auto_report} onChange={(e) => setScanData({...scanData, auto_report: e.target.checked})}
                className="w-4 h-4 rounded" />
              <span className="text-sm text-muted-foreground">自动举报扫描到的评论</span>
            </label>
            <Button onClick={handleScanComments} disabled={scanning}
              className="w-full mt-2 bg-cyan-600 hover:bg-cyan-500">
              {scanning ? <><Loader2 size={16} className="animate-spin" /> 扫描中...</> : <><Search size={16} /> 开始扫描</>}
            </Button>
            <AnimatePresence>
              {scanResult && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="bg-muted rounded-lg p-4 space-y-2">
                  <h3 className="text-xs text-muted-foreground uppercase tracking-wider mb-2">扫描结果</h3>
                  <div className="flex justify-between text-sm"><span className="text-muted-foreground">发现评论</span><span className="font-bold text-cyan-500">{scanResult.comments_found}</span></div>
                  <div className="flex justify-between text-sm"><span className="text-muted-foreground">创建目标</span><span className="font-bold text-purple-500">{scanResult.targets_created}</span></div>
                  {scanResult.reports_executed !== undefined && (
                    <div className="flex justify-between text-sm"><span className="text-muted-foreground">已执行举报</span><span className="font-bold text-green-500">{scanResult.reports_executed}</span></div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog />
      <Toaster richColors />
    </div>
  );
}
