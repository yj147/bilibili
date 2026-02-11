"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Users,
  Target,
  MessageSquare,
  Calendar,
  Settings,
  Shield,
  Menu,
  X,
} from "lucide-react";

const navItems = [
  { name: "概览", icon: LayoutDashboard, href: "/" },
  { name: "账号", icon: Users, href: "/accounts" },
  { name: "举报目标", icon: Target, href: "/targets" },
  { name: "自动回复", icon: MessageSquare, href: "/autoreply" },
  { name: "定时任务", icon: Calendar, href: "/scheduler" },
  { name: "设置", icon: Settings, href: "/config" },
];

function SidebarContent({ onNavClick }: { onNavClick?: () => void }) {
  const pathname = usePathname();

  return (
    <div className="bg-gradient-sidebar h-full rounded-3xl flex flex-col p-6 border border-border card-static">
      {/* Logo Section */}
      <div className="flex items-center gap-3 mb-10 px-2">
        <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-pink-glow">
          <Shield className="text-primary-foreground" size={24} />
        </div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Bili-<span className="text-primary">Sentinel</span>
        </h2>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link key={item.href} href={item.href} onClick={onNavClick}>
              <div
                className={`
                  relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group
                  ${isActive ? "bg-primary/10 text-primary font-semibold" : "text-muted-foreground hover:text-foreground hover:bg-muted/60"}
                `}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute left-0 w-1 h-6 bg-primary rounded-r-full"
                  />
                )}
                <item.icon
                  size={20}
                  className={
                    isActive
                      ? "text-primary"
                      : "group-hover:text-primary transition-colors"
                  }
                />
                <span className="text-sm font-medium">{item.name}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="mt-auto pt-6 border-t border-border">
        <div className="bg-muted/60 p-3 rounded-2xl flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center">
            <Shield size={14} className="text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold truncate text-foreground">管理控制台</p>
            <p className="text-xs text-muted-foreground">管理员</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-[60] p-2 rounded-xl bg-card border border-border md:hidden"
        aria-label="打开菜单"
      >
        <Menu size={24} className="text-foreground" />
      </button>

      {/* Desktop sidebar */}
      <aside className="w-64 h-screen fixed left-0 top-0 z-50 p-4 hidden md:block">
        <SidebarContent />
      </aside>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="fixed inset-0 z-[70] bg-black/40 backdrop-blur-sm md:hidden"
            />
            {/* Sidebar panel */}
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed left-0 top-0 z-[80] w-64 h-screen p-4 md:hidden"
            >
              <button
                onClick={() => setMobileOpen(false)}
                className="absolute top-5 right-5 z-10 p-1 rounded-lg hover:bg-muted"
                aria-label="关闭菜单"
              >
                <X size={20} className="text-muted-foreground" />
              </button>
              <SidebarContent onNavClick={() => setMobileOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
