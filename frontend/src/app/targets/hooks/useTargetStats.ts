import { useTargetStats as useTargetStatsSWR } from "@/lib/swr";

const defaultStats = { total: 0, pending: 0, processing: 0, completed: 0, failed: 0 };

export function useTargetStats() {
  const { data } = useTargetStatsSWR();
  return data ?? defaultStats;
}
