import { memo } from "react";
import { Target, Play, User, MessageCircle, Loader2, Trash2, Pencil, CheckCircle2, AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Target as TargetType } from "@/lib/types";

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
  1: "违法违禁", 2: "色情", 3: "低质量/刷屏", 4: "赌博诈骗",
  5: "人身攻击", 7: "人身攻击", 8: "侵犯隐私", 9: "引战",
  10: "青少年不良信息", 11: "涉政或敏感信息",
};

const commentReasonMap: Record<number, string> = {
  1: "违法违禁", 2: "色情", 3: "低质量/刷屏", 4: "赌博诈骗",
  5: "人身攻击", 7: "侵犯隐私", 8: "内容不相关", 9: "引战",
};

const userReasonMap: Record<number, string> = {
  1: "色情低俗", 2: "不实信息", 3: "违禁",
  4: "人身攻击", 5: "赌博诈骗", 6: "违规引流外链",
};

function getReasonLabel(type: string, reasonId: number | null): string {
  if (reasonId == null) return "";
  const map = type === "user" ? userReasonMap : type === "comment" ? commentReasonMap : videoReasonMap;
  return map[reasonId] ?? `理由 #${reasonId}`;
}

interface TargetListItemProps {
  target: TargetType;
  isSelected: boolean;
  isExecuting: boolean;
  onToggleSelect: () => void;
  onEdit: () => void;
  onExecute: () => void;
  onDelete: () => void;
}

const TargetListItem = memo(function TargetListItem({
  target,
  isSelected,
  isExecuting,
  onToggleSelect,
  onEdit,
  onExecute,
  onDelete,
}: TargetListItemProps) {
  return (
    <div className="flex items-center justify-between p-4 px-6 hover:bg-muted/50 transition-colors group">
      <div className="flex items-center gap-4">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
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
          <Button variant="ghost" size="icon" onClick={onEdit} className="h-8 w-8" aria-label="编辑目标">
            <Pencil size={16} />
          </Button>
          <Button variant="ghost" size="icon" onClick={onExecute} disabled={isExecuting || target.status === 'processing'} className="h-8 w-8" aria-label="执行举报">
            {isExecuting ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onDelete} className="h-8 w-8 hover:text-red-500" aria-label="删除目标">
            <Trash2 size={16} />
          </Button>
        </div>
      </div>
    </div>
  );
});

interface TargetListProps {
  targets: TargetType[];
  loading: boolean;
  selectedTargets: Set<number>;
  executingId: number | null;
  onToggleSelect: (id: number) => void;
  onSelectAll: () => void;
  onEdit: (target: TargetType) => void;
  onExecute: (id: number) => void;
  onDelete: (id: number) => void;
}

export const TargetList = memo(function TargetList({
  targets,
  loading,
  selectedTargets,
  executingId,
  onToggleSelect,
  onSelectAll,
  onEdit,
  onExecute,
  onDelete,
}: TargetListProps) {
  return (
    <Card className="overflow-hidden min-h-[300px] card-static">
      <div className="p-6 border-b flex items-center justify-between bg-muted/50">
        <div className="flex items-center gap-3">
          {targets.length > 0 && (
            <input
              type="checkbox"
              checked={selectedTargets.size === targets.length && targets.length > 0}
              onChange={onSelectAll}
              className="w-4 h-4 rounded cursor-pointer"
            />
          )}
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">目标列表</h3>
        </div>
      </div>
      {loading && targets.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
          <Loader2 className="animate-spin mb-4" size={32} />
          <p className="text-sm">正在加载数据...</p>
        </div>
      ) : targets.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
          <Target className="mb-4 opacity-20" size={48} />
          <p className="text-sm">暂无举报目标</p>
        </div>
      ) : (
        <div className="divide-y">
          {targets.map((target) => (
            <TargetListItem
              key={target.id}
              target={target}
              isSelected={selectedTargets.has(target.id)}
              isExecuting={executingId === target.id}
              onToggleSelect={() => onToggleSelect(target.id)}
              onEdit={() => onEdit(target)}
              onExecute={() => onExecute(target.id)}
              onDelete={() => onDelete(target.id)}
            />
          ))}
        </div>
      )}
    </Card>
  );
});
