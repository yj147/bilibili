"use client";

import { useState, useEffect, useRef, useMemo, useReducer } from "react";
import { Target, Plus, Upload, Search, Play, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { useTargets, useAccounts } from "@/lib/swr";
import { useLogStream } from "@/lib/websocket";
import type { Target as TargetType, CommentScanResult } from "@/lib/types";
import { toast, Toaster } from "sonner";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ConfirmDialog";
import { TargetStats } from "./components/TargetStats";
import { TargetFilters } from "./components/TargetFilters";
import { TargetList } from "./components/TargetList";
import { AddModal, BatchModal, EditModal, ScanModal } from "./components/TargetModals";
import { useTargetStats } from "./hooks/useTargetStats";

type ModalState = {
  showAdd: boolean;
  showBatch: boolean;
  showEdit: boolean;
  showScan: boolean;
  editingTarget: TargetType | null;
  scanning: boolean;
  scanResult: CommentScanResult | null;
};

type ModalAction =
  | { type: "OPEN_ADD" }
  | { type: "CLOSE_ADD" }
  | { type: "OPEN_BATCH" }
  | { type: "CLOSE_BATCH" }
  | { type: "OPEN_EDIT"; target: TargetType }
  | { type: "CLOSE_EDIT" }
  | { type: "OPEN_SCAN" }
  | { type: "CLOSE_SCAN" }
  | { type: "SET_SCANNING"; value: boolean }
  | { type: "SET_SCAN_RESULT"; result: CommentScanResult | null };

const initialModalState: ModalState = {
  showAdd: false, showBatch: false, showEdit: false, showScan: false,
  editingTarget: null, scanning: false, scanResult: null,
};

function modalReducer(state: ModalState, action: ModalAction): ModalState {
  switch (action.type) {
    case "OPEN_ADD": return { ...state, showAdd: true };
    case "CLOSE_ADD": return { ...state, showAdd: false };
    case "OPEN_BATCH": return { ...state, showBatch: true };
    case "CLOSE_BATCH": return { ...state, showBatch: false };
    case "OPEN_EDIT": return { ...state, showEdit: true, editingTarget: action.target };
    case "CLOSE_EDIT": return { ...state, showEdit: false, editingTarget: null };
    case "OPEN_SCAN": return { ...state, showScan: true, scanResult: null };
    case "CLOSE_SCAN": return { ...state, showScan: false };
    case "SET_SCANNING": return { ...state, scanning: action.value };
    case "SET_SCAN_RESULT": return { ...state, scanResult: action.result };
  }
}

export default function TargetsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [selectedTargets, setSelectedTargets] = useState<Set<number>>(new Set());

  const queryParams: Record<string, string> = { page: page.toString(), page_size: pageSize.toString() };
  if (statusFilter) queryParams.status = statusFilter;
  if (typeFilter) queryParams.type = typeFilter;

  const { data: targetData, mutate, isLoading } = useTargets(queryParams);
  const { data: accounts = [] } = useAccounts();
  const stats = useTargetStats();

  const targets = useMemo(() => {
    const allTargets = targetData?.items ?? [];
    if (!searchKeyword.trim()) return allTargets;
    const keyword = searchKeyword.toLowerCase();
    return allTargets.filter(t =>
      t.identifier.toLowerCase().includes(keyword) ||
      (t.display_text && t.display_text.toLowerCase().includes(keyword))
    );
  }, [targetData?.items, searchKeyword]);

  const total = targets.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const loading = isLoading;
  const { confirm, ConfirmDialog } = useConfirm();

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
  const [modal, dispatchModal] = useReducer(modalReducer, initialModalState);
  const [formData, setFormData] = useState({ type: "video" as string, identifier: "", reason_id: 1, reason_content_id: 1, reason_text: "" });
  const [batchData, setBatchData] = useState({ type: "video" as string, identifiers: "", reason_id: 1, reason_content_id: 1, reason_text: "" });
  const [editFormData, setEditFormData] = useState({ reason_id: 1, reason_content_id: 1, reason_text: "", status: "pending" as string });
  const [scanData, setScanData] = useState({ bvid: "", account_id: 0, reason_id: 9, reason_text: "", max_pages: 5, auto_report: false });

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
      dispatchModal({ type: "CLOSE_ADD" });
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
      dispatchModal({ type: "CLOSE_BATCH" });
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
    setEditFormData({
      reason_id: target.reason_id ?? 1,
      reason_content_id: target.reason_content_id ?? 1,
      reason_text: target.reason_text ?? "",
      status: target.status,
    });
    dispatchModal({ type: "OPEN_EDIT", target });
  };

  const handleEditSubmit = async () => {
    if (!modal.editingTarget) return;
    try {
      await api.targets.update(modal.editingTarget.id, editFormData);
      dispatchModal({ type: "CLOSE_EDIT" });
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
    dispatchModal({ type: "SET_SCANNING", value: true });
    dispatchModal({ type: "SET_SCAN_RESULT", result: null });
    try {
      const result = await api.reports.scanComments({
        bvid: scanData.bvid.trim(),
        account_id: scanData.account_id,
        reason_id: scanData.reason_id,
        reason_text: scanData.reason_text || undefined,
        max_pages: scanData.max_pages,
        auto_report: scanData.auto_report,
      });
      dispatchModal({ type: "SET_SCAN_RESULT", result });
      mutate();
      toast.success(`扫描完成: 发现 ${result.comments_found} 条评论, 创建 ${result.targets_created} 个目标`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "扫描失败");
    } finally {
      dispatchModal({ type: "SET_SCANNING", value: false });
    }
  };

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
          <Button variant="outline" size="sm" onClick={() => dispatchModal({ type: "OPEN_ADD" })}>
            <Plus size={16} /> 添加目标
          </Button>
          <Button variant="outline" size="sm" onClick={() => dispatchModal({ type: "OPEN_BATCH" })}>
            <Upload size={16} /> 批量导入
          </Button>
          <Button variant="outline" size="sm" onClick={() => dispatchModal({ type: "OPEN_SCAN" })}>
            <Search size={16} /> 评论扫描
          </Button>
          <Button onClick={handleExecuteAll} disabled={selectedTargets.size === 0}>
            <Play size={18} /> 批量执行 {selectedTargets.size > 0 && `(${selectedTargets.size})`}
          </Button>
        </div>
      </div>

      <TargetStats
        total={stats.total}
        pending={stats.pending}
        completed={stats.completed}
        failed={stats.failed}
      />

      <TargetFilters
        searchKeyword={searchKeyword}
        onSearchChange={(value) => { setSearchKeyword(value); setPage(1); }}
        statusFilter={statusFilter}
        onStatusChange={(value) => { setStatusFilter(value); setPage(1); }}
        typeFilter={typeFilter}
        onTypeChange={(value) => { setTypeFilter(value); setPage(1); }}
        pageSize={pageSize}
        onPageSizeChange={(value) => { setPageSize(value); setPage(1); }}
        page={page}
        totalPages={totalPages}
        total={total}
        onPageChange={setPage}
        onBulkDelete={handleBulkDelete}
      />

      <TargetList
        targets={targets}
        loading={loading}
        selectedTargets={selectedTargets}
        executingId={executingId}
        onToggleSelect={handleToggleSelect}
        onSelectAll={handleSelectAll}
        onEdit={handleEdit}
        onExecute={handleExecute}
        onDelete={handleDelete}
      />

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

      <AddModal
        open={modal.showAdd}
        onOpenChange={(open) => dispatchModal({ type: open ? "OPEN_ADD" : "CLOSE_ADD" })}
        formData={formData}
        onFormChange={(data) => setFormData({ ...formData, ...data })}
        onSubmit={handleAdd}
      />

      <BatchModal
        open={modal.showBatch}
        onOpenChange={(open) => dispatchModal({ type: open ? "OPEN_BATCH" : "CLOSE_BATCH" })}
        batchData={batchData}
        onBatchChange={(data) => setBatchData({ ...batchData, ...data })}
        onSubmit={handleBatchAdd}
      />

      <EditModal
        open={modal.showEdit}
        onOpenChange={(open) => { if (!open) dispatchModal({ type: "CLOSE_EDIT" }); }}
        target={modal.editingTarget}
        editData={editFormData}
        onEditChange={(data) => setEditFormData({ ...editFormData, ...data })}
        onSubmit={handleEditSubmit}
      />

      <ScanModal
        open={modal.showScan}
        onOpenChange={(open) => dispatchModal({ type: open ? "OPEN_SCAN" : "CLOSE_SCAN" })}
        scanData={scanData}
        onScanChange={(data) => setScanData({ ...scanData, ...data })}
        accounts={accounts}
        scanning={modal.scanning}
        scanResult={modal.scanResult}
        onSubmit={handleScanComments}
      />

      <ConfirmDialog />
      <Toaster richColors />
    </div>
  );
}
