import React from "react";

interface StatItemProps {
  label: string;
  value: string | number;
  trend?: number;
  color?: string;
}

export default function StatItem({ label, value, trend, color = "text-blue-400" }: StatItemProps) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-white/50">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className={`text-2xl font-bold ${color} text-glow`}>{value}</span>
        {trend && <span className="text-[10px] text-green-400">+{trend}%</span>}
      </div>
    </div>
  );
}
