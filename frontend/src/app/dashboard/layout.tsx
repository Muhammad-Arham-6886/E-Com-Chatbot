"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import {
  Bot,
  LayoutDashboard,
  Globe,
  MessageSquare,
  BookOpen,
  BarChart3,
  Plug,
  Settings,
  LogOut,
  Shield,
} from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-950">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!user) {
    router.push("/login");
    return null;
  }

  const navItems = [
    { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { label: "Websites", href: "/dashboard/websites", icon: Globe },
    { label: "Knowledge Base", href: "/dashboard/knowledge", icon: BookOpen },
    { label: "AI Test Console", href: "/dashboard/chat", icon: MessageSquare },
    { label: "Conversations", href: "/dashboard/conversations", icon: MessageSquare },
    { label: "Security & Audit", href: "/dashboard/security", icon: Shield },
    { label: "Integrations", href: "/dashboard/integrations", icon: Plug },
    { label: "Analytics", href: "/dashboard/analytics", icon: BarChart3 },
    { label: "Settings", href: "/dashboard/settings", icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 antialiased">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-slate-800/80 bg-slate-900/50 backdrop-blur-xl">
        {/* Brand Header */}
        <div className="flex h-16 items-center gap-3 border-b border-slate-800/80 px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 shadow-md shadow-indigo-600/30">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-sm tracking-tight text-white">AI Assistant</span>
            <span className="block text-[10px] uppercase tracking-wider font-semibold text-indigo-400">
              E-Commerce Bot
            </span>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.label}
                href={item.href}
                className={`group flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"}`} />
                  <span>{item.label}</span>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* User Footer Card */}
        <div className="border-t border-slate-800/80 p-3">
          <div className="flex items-center justify-between rounded-xl bg-slate-950/60 p-2.5 border border-slate-800">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-800 text-indigo-400 font-semibold border border-slate-700">
                {user.full_name ? user.full_name.substring(0, 1).toUpperCase() : user.email.substring(0, 1).toUpperCase()}
              </div>
              <div className="truncate">
                <p className="truncate text-xs font-semibold text-white">{user.full_name || "User"}</p>
                <p className="truncate text-[10px] text-slate-400">{user.email}</p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-red-400 transition"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-800/80 bg-slate-900/30 px-8 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-white">
              {navItems.find((i) => i.href === pathname)?.label || "Dashboard"}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold text-emerald-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Active
            </div>
          </div>
        </header>

        {/* Page Content Viewport */}
        <main className="flex-1 overflow-y-auto p-8 bg-slate-950/50">{children}</main>
      </div>
    </div>
  );
}
