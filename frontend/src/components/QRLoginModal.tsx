"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { QrCode, Loader2, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { api } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

type QRState = "loading" | "waiting" | "scanned" | "success" | "expired" | "error";

interface QRLoginModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export default function QRLoginModal({ onClose, onSuccess }: QRLoginModalProps) {
  const [state, setState] = useState<QRState>("loading");
  const [qrUrl, setQrUrl] = useState("");
  const [qrcodeKey, setQrcodeKey] = useState("");
  const [message, setMessage] = useState("");
  const [accountName, setAccountName] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onSuccessRef = useRef(onSuccess);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onSuccessRef.current = onSuccess;
    onCloseRef.current = onClose;
  });

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const fetchQR = useCallback(async () => {
    try {
      const data = await api.auth.qrGenerate();
      setQrUrl(data.url);
      setQrcodeKey(data.qrcode_key);
      setState("waiting");
    } catch {
      setState("error");
      setMessage("二维码生成失败，请重试");
    }
  }, []);

  const handleRefresh = useCallback(() => {
    stopPolling();
    setState("loading");
    setMessage("");
    fetchQR();
  }, [stopPolling, fetchQR]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async: setState only after await
    fetchQR();
    return () => stopPolling();
  }, [fetchQR, stopPolling]);

  useEffect(() => {
    if (!qrcodeKey || (state !== "waiting" && state !== "scanned")) return;

    pollRef.current = setInterval(async () => {
      try {
        const name = accountName.trim() || "QR_login";
        const result = await api.auth.qrLogin(qrcodeKey, name);
        const code = result.status_code;

        if (code === 0) {
          stopPolling();
          setState("success");
          setMessage(result.message || "登录成功");
          setTimeout(() => {
            onSuccessRef.current();
            onCloseRef.current();
          }, 1200);
        } else if (code === 86090) {
          setState("scanned");
          setMessage("已扫码，请在手机上确认");
        } else if (code === 86038) {
          stopPolling();
          setState("expired");
          setMessage("二维码已过期，请刷新");
        }
      } catch {
        // Network error during poll — skip
      }
    }, 2000);

    return () => stopPolling();
  }, [qrcodeKey, state, accountName, stopPolling]);

  const stateConfig: Record<QRState, { icon: React.ReactNode; label: string; color: string }> = {
    loading: { icon: <Loader2 size={20} className="animate-spin" />, label: "生成中...", color: "text-blue-500" },
    waiting: { icon: <QrCode size={20} />, label: "等待扫码", color: "text-blue-500" },
    scanned: { icon: <Loader2 size={20} className="animate-spin" />, label: "已扫码，待确认", color: "text-yellow-500" },
    success: { icon: <CheckCircle2 size={20} />, label: "登录成功", color: "text-green-500" },
    expired: { icon: <AlertCircle size={20} />, label: "已过期", color: "text-destructive" },
    error: { icon: <AlertCircle size={20} />, label: "错误", color: "text-destructive" },
  };

  const currentState = stateConfig[state];

  return (
    <Dialog open={true} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <QrCode className="text-blue-500" size={22} /> 扫码登录
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          <div className="space-y-2">
            <Label>账号别名（可选）</Label>
            <Input
              type="text"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              placeholder="例如：小号-01"
            />
          </div>

          <div className="flex flex-col items-center">
            <div className="relative w-52 h-52 bg-white rounded-2xl flex items-center justify-center mb-4 overflow-hidden">
              {state === "loading" ? (
                <Loader2 size={40} className="animate-spin text-zinc-400" />
              ) : qrUrl ? (
                <>
                  <QRCodeSVG value={qrUrl} size={192} level="M" />
                  {(state === "expired" || state === "success" || state === "error") && (
                    <div className="absolute inset-0 bg-white/90 flex flex-col items-center justify-center">
                      <div className={state === "success" ? "text-green-500" : "text-red-500"}>
                        {state === "success" ? <CheckCircle2 size={40} /> : <AlertCircle size={40} />}
                      </div>
                      <span className="text-zinc-700 text-sm mt-2 font-medium">{currentState.label}</span>
                    </div>
                  )}
                </>
              ) : (
                <QrCode size={40} className="text-zinc-300" />
              )}
            </div>

            <div className={`flex items-center gap-2 text-sm ${currentState.color} mb-3`}>
              {currentState.icon}
              <span>{message || currentState.label}</span>
            </div>

            {(state === "expired" || state === "error") && (
              <Button onClick={handleRefresh} size="sm">
                <RefreshCw size={14} /> 刷新二维码
              </Button>
            )}

            <p className="text-xs text-muted-foreground mt-4 text-center">
              请使用哔哩哔哩 App 扫描二维码登录
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
