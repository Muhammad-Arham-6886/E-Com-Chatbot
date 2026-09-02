"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  Globe,
  MessageSquare,
  Users,
  ShieldCheck,
  ArrowUpRight,
  Plus,
  Sparkles,
  Layers,
} from "lucide-react";

export default function DashboardOverviewPage() {
  const { currentOrg, user } = useAuth();
  const [websiteCount, setWebsiteCount] = useState<number>(0);
  const [memberCount, setMemberCount] = useState<number>(1);

  useEffect(() => {
    if (currentOrg) {
      apiRequest(`/websites?org_id=${currentOrg.id}`)
        .then((res) => setWebsiteCount(res.length))
        .catch(() => setWebsiteCount(0));

      apiRequest(`/organizations/${currentOrg.id}/members`)
        .then((res) => setMemberCount(res.length))
        .catch(() => setMemberCount(1));
    }
  }, [currentOrg]);

  const stats = [
    {
      title: "Connected Websites",
      value: `${websiteCount}`,
      sub: websiteCount > 0 ? "Websites configured" : "Add your first website",
      icon: Globe,
      color: "from-blue-500/20 to-cyan-500/20",
      iconColor: "text-cyan-400",
      href: "/dashboard/websites",
    },
    {
      title: "Total Conversations",
      value: "0",
      sub: "Conversation Engine",
      icon: MessageSquare,
      color: "from-indigo-500/20 to-purple-500/20",
      iconColor: "text-indigo-400",
    },
    {
      title: "Team Members",
      value: `${memberCount}`,
      sub: "Manage roles & permissions",
      icon: Users,
      color: "from-emerald-500/20 to-teal-500/20",
      iconColor: "text-emerald-400",
      href: "/dashboard/team",
    },
    {
      title: "Tenant Isolation",
      value: "Enforced",
      sub: "Server-side RBAC active",
      icon: ShieldCheck,
      color: "from-amber-500/20 to-orange-500/20",
      iconColor: "text-amber-400",
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-r from-indigo-950/60 via-slate-900 to-slate-900 p-8 shadow-xl">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400 mb-3">
              <Sparkles className="h-3.5 w-3.5" />
              <span>AI Assistant Active</span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Welcome back, {user?.full_name || user?.email}
            </h1>
            <p className="mt-1 text-sm text-slate-400 max-w-2xl">
              Workspace: <span className="font-semibold text-slate-200">{currentOrg?.name}</span> ({currentOrg?.slug}) • Role: <span className="font-mono text-xs text-indigo-400 font-semibold">{currentOrg?.role}</span>
            </p>
          </div>

          <Link
            href="/dashboard/websites"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 self-start md:self-auto"
          >
            <Plus className="h-4 w-4" />
            <span>Connect Website</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          const card = (
            <div className="relative overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/50 p-6 transition-all hover:border-slate-700 hover:shadow-lg backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{stat.title}</span>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${stat.color} border border-slate-800`}>
                  <Icon className={`h-5 w-5 ${stat.iconColor}`} />
                </div>
              </div>
              <p className="mt-4 text-2xl font-bold text-white tracking-tight">{stat.value}</p>
              <p className="mt-1 text-xs text-slate-400">{stat.sub}</p>
            </div>
          );

          return stat.href ? (
            <Link key={stat.title} href={stat.href}>
              {card}
            </Link>
          ) : (
            <div key={stat.title}>{card}</div>
          );
        })}
      </div>

      {/* Phase Roadmap Card */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-6 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-base font-bold text-white">System Status</h3>
            <p className="text-xs text-slate-400">Core platform features</p>
          </div>
          <div className="flex items-center gap-2 rounded-xl bg-emerald-600/10 border border-emerald-500/20 px-3 py-1.5 text-xs font-semibold text-emerald-400">
            <Layers className="h-4 w-4" />
            <span>All Systems Operational</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
            <div className="flex items-center justify-between text-xs font-bold text-emerald-400 mb-1">
              <span>AUTH & MULTI-TENANCY</span>
              <span>Active</span>
            </div>
            <p className="text-sm font-semibold text-white">User & Organization Management</p>
            <p className="text-xs text-slate-400 mt-1">JWT auth, RBAC, team invitations, workspace isolation.</p>
          </div>

          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
            <div className="flex items-center justify-between text-xs font-bold text-emerald-400 mb-1">
              <span>CRAWLER & KNOWLEDGE BASE</span>
              <span>Active</span>
            </div>
            <p className="text-sm font-semibold text-white">Website Crawling & RAG</p>
            <p className="text-xs text-slate-400 mt-1">Robots.txt, sitemaps, HTML extraction, embeddings, similarity search.</p>
          </div>

          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
            <div className="flex items-center justify-between text-xs font-bold text-emerald-400 mb-1">
              <span>AI & WIDGET</span>
              <span>Active</span>
            </div>
            <p className="text-sm font-semibold text-white">Chat Widget & AI Engine</p>
            <p className="text-xs text-slate-400 mt-1">Embeddable widget, Ollama RAG, live chat, WhatsApp handoff.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
