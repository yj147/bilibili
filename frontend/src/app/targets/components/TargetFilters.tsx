import { memo } from "react";
import { Search, CheckCircle2, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface TargetFiltersProps {
  searchKeyword: string;
  onSearchChange: (value: string) => void;
  statusFilter: string;
  onStatusChange: (value: string) => void;
  typeFilter: string;
  onTypeChange: (value: string) => void;
  pageSize: number;
  onPageSizeChange: (value: number) => void;
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
  onBulkDelete: (status: string) => void;
}

export const TargetFilters = memo(function TargetFilters({
  searchKeyword,
  onSearchChange,
  statusFilter,
  onStatusChange,
  typeFilter,
  onTypeChange,
  pageSize,
  onPageSizeChange,
  page,
  totalPages,
  total,
  onPageChange,
  onBulkDelete,
}: TargetFiltersProps) {
  return (
    <div className="flex flex-col gap-4 mb-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
        <Input
          value={searchKeyword}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索 BV号/rpid/uid/评论内容..."
          className="pl-10 h-9"
        />
      </div>
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex gap-3 flex-wrap items-center">
          <Select value={statusFilter || "all"} onValueChange={(v) => onStatusChange(v === "all" ? "" : v)}>
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
          <Select value={typeFilter || "all"} onValueChange={(v) => onTypeChange(v === "all" ? "" : v)}>
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
          <Select value={pageSize.toString()} onValueChange={(v) => onPageSizeChange(parseInt(v))}>
            <SelectTrigger className="w-[110px] h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10 条/页</SelectItem>
              <SelectItem value="20">20 条/页</SelectItem>
              <SelectItem value="50">50 条/页</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => onBulkDelete('completed')}>
            <CheckCircle2 size={14} /> 清除已完成
          </Button>
          <Button variant="outline" size="sm" onClick={() => onBulkDelete('failed')}>
            <AlertTriangle size={14} /> 清除失败
          </Button>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>第 {page}/{totalPages} 页 (共 {total} 条)</span>
          <Button variant="outline" size="sm" onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page <= 1}>
            <ChevronLeft size={14} />
          </Button>
          <Button variant="outline" size="sm" onClick={() => onPageChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages}>
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
});
