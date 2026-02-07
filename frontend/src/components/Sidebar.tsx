"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { 
  LayoutDashboard, 
  Users, 
  Target, 
  MessageSquare, 
  Calendar, 
  Settings,
  Shield,
  Zap
} from "lucide-react";

const navItems = [
  { name: "仪表盘", icon: LayoutDashboard, href: "/" },
  { name: "账号管理", icon: Users, href: "/accounts" },
  { name: "目标猎场", icon: Target, href: "/targets" },
  { name: "自动回复", icon: MessageSquare, href: "/autoreply" },
  { name: "任务调度", icon: Calendar, href: "/scheduler" },
  { name: "系统配置", icon: Settings, href: "/config" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen fixed left-0 top-0 z-50 p-4 hidden md:block">
      <div className="glass-card h-full rounded-3xl flex flex-col p-6 border-white/5">
        {/* Logo Section */}
        <div className="flex items-center gap-3 mb-10 px-2">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(37,99,235,0.3)]">
            <Shield className="text-white" size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight">Sentinel</h2>
            <div className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              <span className="text-[10px] text-white/40 uppercase tracking-widest">System Active</span>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href}>
                <div className={`
                  relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group
                  ${isActive ? 'bg-blue-600/10 text-blue-400' : 'text-white/50 hover:text-white hover:bg-white/5'}
                `}>
                  {isActive && (
                    <motion.div 
                      layoutId="activeNav"
                      className="absolute left-0 w-1 h-6 bg-blue-500 rounded-r-full"
                    />
                  )}
                  <item.icon size={20} className={isActive ? 'text-blue-400' : 'group-hover:text-blue-400 transition-colors'} />
                  <span className="text-sm font-medium">{item.name}</span>
                  {item.name === "自动回复" && (
                    <span className="ml-auto flex h-2 w-2 rounded-full bg-blue-500" />
                  )}
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Footer / User Profile */}
        <div className="mt-auto pt-6 border-t border-white/5">
          <div className="glass-card bg-white/5 p-3 rounded-2xl flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold truncate">ENI Enchanted</p>
              <p className="text-[10px] text-white/40">Master Admin</p>
            </div>
            <Zap size={14} className="text-yellow-400 animate-pulse" />
          </div>
        </div>
      </div>
    </aside>
  );
}
