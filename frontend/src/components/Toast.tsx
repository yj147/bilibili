"use client";

import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

export interface ToastItem {
  id: string;
  type: "warning" | "success" | "info" | "error";
  message: string;
  duration?: number;
}

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

const icons = {
  warning: <AlertTriangle size={16} />,
  success: <CheckCircle2 size={16} />,
  info: <Info size={16} />,
  error: <AlertTriangle size={16} />,
};

const colors = {
  warning: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",
  success: "border-green-500/40 bg-green-500/10 text-green-300",
  info: "border-blue-500/40 bg-blue-500/10 text-blue-300",
  error: "border-red-500/40 bg-red-500/10 text-red-300",
};

function ToastMessage({ toast, onDismiss }: { toast: ToastItem; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, toast.duration ?? 6000);
    return () => clearTimeout(timer);
  }, [toast.duration, onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 60, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 60, scale: 0.95 }}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-lg text-sm shadow-lg ${colors[toast.type]}`}
    >
      {icons[toast.type]}
      <span className="flex-1">{toast.message}</span>
      <button onClick={onDismiss} className="p-0.5 hover:bg-white/10 rounded cursor-pointer">
        <X size={14} />
      </button>
    </motion.div>
  );
}

export default function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-[200] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <ToastMessage toast={t} onDismiss={() => onDismiss(t.id)} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
}

let _toastId = 0;
export function createToast(type: ToastItem["type"], message: string, duration?: number): ToastItem {
  return { id: `toast-${++_toastId}`, type, message, duration };
}
