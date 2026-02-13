import { AnimatePresence, motion } from "framer-motion";
import { Pencil, Search, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import type { Target, CommentScanResult, AccountPublic } from "@/lib/types";

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

const userContentReasonMap: Record<number, string> = {
  1: "头像违规", 2: "昵称违规", 3: "签名违规",
};

const typeMap: Record<string, string> = {
  video: "视频", comment: "评论", user: "用户",
};

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

function identifierPlaceholder(type: string) {
  switch (type) {
    case "video": return "输入 BV 号";
    case "comment": return "输入 oid:rpid";
    case "user": return "输入用户 UID";
    default: return "";
  }
}

interface AddModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  formData: { type: string; identifier: string; reason_id: number; reason_content_id: number; reason_text: string };
  onFormChange: (data: Partial<AddModalProps["formData"]>) => void;
  onSubmit: () => void;
}

export function AddModal({ open, onOpenChange, formData, onFormChange, onSubmit }: AddModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>添加目标</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="mb-1">目标类型</Label>
            <Select value={formData.type} onValueChange={(v) => onFormChange({ type: v })}>
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
            <Input value={formData.identifier} onChange={(e) => onFormChange({ identifier: e.target.value })}
              placeholder={identifierPlaceholder(formData.type)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="mb-1">{formData.type === "user" ? "举报类别" : "举报理由"}</Label>
              <ReasonSelect type={formData.type} value={formData.reason_id} onChange={(v) => onFormChange({ reason_id: v })} />
            </div>
            <div>
              {formData.type === "user" ? (
                <>
                  <Label className="mb-1">内容理由</Label>
                  <Select value={formData.reason_content_id.toString()} onValueChange={(v) => onFormChange({ reason_content_id: parseInt(v) })}>
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
                  <Input value={formData.reason_text} onChange={(e) => onFormChange({ reason_text: e.target.value })}
                    placeholder="可选" />
                </>
              )}
            </div>
          </div>
          <Button onClick={onSubmit} className="w-full mt-2">确认添加</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface BatchModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  batchData: { type: string; identifiers: string; reason_id: number; reason_content_id: number; reason_text: string };
  onBatchChange: (data: Partial<BatchModalProps["batchData"]>) => void;
  onSubmit: () => void;
}

export function BatchModal({ open, onOpenChange, batchData, onBatchChange, onSubmit }: BatchModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>批量导入目标</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="mb-1">目标类型</Label>
            <Select value={batchData.type} onValueChange={(v) => onBatchChange({ type: v })}>
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
            <textarea value={batchData.identifiers} onChange={(e) => onBatchChange({ identifiers: e.target.value })}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring h-32 resize-none font-mono"
              placeholder={"BV1xx411c7xx\nBV1yy411c8yy\nBV1zz411c9zz"} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="mb-1">举报理由</Label>
              <ReasonSelect type={batchData.type} value={batchData.reason_id} onChange={(v) => onBatchChange({ reason_id: v })} />
            </div>
            <div>
              <Label className="mb-1">举报文本</Label>
              <Input value={batchData.reason_text} onChange={(e) => onBatchChange({ reason_text: e.target.value })}
                placeholder="可选" />
            </div>
          </div>
          <Button onClick={onSubmit} className="w-full mt-2">确认导入</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface EditModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  target: Target | null;
  editData: { reason_id: number; reason_content_id: number; reason_text: string; status: string };
  onEditChange: (data: Partial<EditModalProps["editData"]>) => void;
  onSubmit: () => void;
}

export function EditModal({ open, onOpenChange, target, editData, onEditChange, onSubmit }: EditModalProps) {
  return (
    <Dialog open={open && !!target} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Pencil size={18} className="text-orange-500" /> 编辑目标</DialogTitle>
        </DialogHeader>
        {target && (
          <>
            <div className="p-3 bg-muted rounded-lg">
              <span className="text-xs text-muted-foreground">目标: </span>
              <span className="text-sm font-mono">{target.identifier}</span>
              <Badge variant="secondary" className="ml-2 text-xs tracking-widest">{typeMap[target.type] ?? target.type}</Badge>
            </div>
            <div className="space-y-4">
              <div>
                <Label className="mb-1">举报理由</Label>
                <ReasonSelect type={target.type} value={editData.reason_id} onChange={(v) => onEditChange({ reason_id: v })} />
              </div>
              {target.type === "user" && (
                <div>
                  <Label className="mb-1">内容理由</Label>
                  <Select value={editData.reason_content_id.toString()} onValueChange={(v) => onEditChange({ reason_content_id: parseInt(v) })}>
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
                <Input value={editData.reason_text} onChange={(e) => onEditChange({ reason_text: e.target.value })} />
              </div>
              <div>
                <Label className="mb-1">状态</Label>
                <Select value={editData.status} onValueChange={(v) => onEditChange({ status: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">待处理</SelectItem>
                    <SelectItem value="processing">处理中</SelectItem>
                    <SelectItem value="completed">已完成</SelectItem>
                    <SelectItem value="failed">失败</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={onSubmit} className="w-full mt-2 bg-orange-600 hover:bg-orange-500">保存更改</Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

interface ScanModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scanData: { bvid: string; account_id: number; reason_id: number; reason_text: string; max_pages: number; auto_report: boolean };
  onScanChange: (data: Partial<ScanModalProps["scanData"]>) => void;
  accounts: AccountPublic[];
  scanning: boolean;
  scanResult: CommentScanResult | null;
  onSubmit: () => void;
}

export function ScanModal({ open, onOpenChange, scanData, onScanChange, accounts, scanning, scanResult, onSubmit }: ScanModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Search size={18} className="text-cyan-500" /> 评论扫描</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="mb-1">BV 号</Label>
            <Input value={scanData.bvid} onChange={(e) => onScanChange({ bvid: e.target.value })}
              className="font-mono" placeholder="BV1xxxxxxxxxx" />
          </div>
          <div>
            <Label className="mb-1">使用账号</Label>
            <Select value={scanData.account_id.toString()} onValueChange={(v) => onScanChange({ account_id: parseInt(v) })}>
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
              <ReasonSelect type="video" value={scanData.reason_id} onChange={(v) => onScanChange({ reason_id: v })} />
            </div>
            <div>
              <Label className="mb-1">最大页数</Label>
              <Input type="number" value={scanData.max_pages} onChange={(e) => onScanChange({ max_pages: parseInt(e.target.value) || 5 })} />
            </div>
          </div>
          <div>
            <Label className="mb-1">举报文本 (可选)</Label>
            <Input value={scanData.reason_text} onChange={(e) => onScanChange({ reason_text: e.target.value })}
              placeholder="可选补充说明" />
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={scanData.auto_report} onChange={(e) => onScanChange({ auto_report: e.target.checked })}
              className="w-4 h-4 rounded" />
            <span className="text-sm text-muted-foreground">自动举报扫描到的评论</span>
          </label>
          <Button onClick={onSubmit} disabled={scanning}
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
  );
}
