import { memo } from "react";
import { Target, Filter, CheckCircle2, AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/card";

interface TargetStatsProps {
  total: number;
  pending: number;
  completed: number;
  failed: number;
}

const statsConfig = [
  { label: "总目标数", key: "total" as const, icon: Target, color: "text-blue-500" },
  { label: "待处理", key: "pending" as const, icon: Filter, color: "text-yellow-500" },
  { label: "已清理", key: "completed" as const, icon: CheckCircle2, color: "text-green-500" },
  { label: "处理失败", key: "failed" as const, icon: AlertTriangle, color: "text-red-500" },
];

export const TargetStats = memo(function TargetStats({ total, pending, completed, failed }: TargetStatsProps) {
  const stats = { total, pending, completed, failed };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      {statsConfig.map((stat) => (
        <Card key={stat.key} className="p-4 flex items-center gap-4 card-elevated cursor-default">
          <div className={`p-3 rounded-xl bg-muted ${stat.color}`}>
            <stat.icon size={20} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">{stat.label}</p>
            <p className="text-xl font-bold">{stats[stat.key]}</p>
          </div>
        </Card>
      ))}
    </div>
  );
});
