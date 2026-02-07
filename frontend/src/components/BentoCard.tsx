"use client";

import React from "react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface BentoCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  icon?: LucideIcon;
}

export default function BentoCard({ children, className = "", title = "", icon: Icon }: BentoCardProps) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      className={`glass-card glass-card-hover p-6 rounded-2xl overflow-hidden relative group ${className}`}
    >
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        {Icon && <Icon size={80} />}
      </div>
      {title && (
        <div className="flex items-center gap-2 mb-4">
          {Icon && <Icon size={18} className="text-blue-400" />}
          <h3 className="text-sm font-medium text-white/70 uppercase tracking-wider">{title}</h3>
        </div>
      )}
      {children}
    </motion.div>
  );
}
