"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  BarChart3,
  TrendingUp,
  MessageSquare,
  ShoppingCart,
  Phone,
  ShieldCheck,
  Calendar,
  Globe,
  Filter,
  Sparkles,
  ArrowRight,
  Layers,
} from "lucide-react";

interface AnalyticsOverview {
  period: string;
  total_conversations: number;
  total_messages: number;
  user_messages: number;
  bot_messages: number;
  avg_messages_per_conversation: number;
  bot_containment_rate: number;
  human_escalation_rate: number;
  add_to_cart_conversions: number;
  product_recommendations_served: number;
  whatsapp_handoffs_triggered: number;
}

interface TimeseriesPoint {
  date: string;
  label: string;
  conversations: number;
  messages: number;
  conversions: number;
}

interface IntentItem {
  intent: string;
  count: number;
  percentage: number;
}

interface FunnelStage {
  stage: string;
  count: number;
  conversion_rate: number;
}

interface WebsiteOption {
  id: string;
  name: string;
  domain: string;
}

export default function AnalyticsDashboardPage() {
  const { currentOrg } = useAuth();
  const [period, setPeriod] = useState<"7d" | "30d" | "90d">("30d");
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string>("");
  const [websites, setWebsites] = useState<WebsiteOption[]>([]);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [intents, setIntents] = useState<IntentItem[]>([]);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (currentOrg) {
      apiRequest<WebsiteOption[]>(`/websites?org_id=${currentOrg.id}`)
        .then((res) => setWebsites(res))
        .catch(() => setWebsites([]));
    }
  }, [currentOrg]);

  const fetchAnalytics = async () => {
    if (!currentOrg) return;
    setIsLoading(true);
    try {
      let queryParams = `org_id=${currentOrg.id}&period=${period}`;
      if (selectedWebsiteId) queryParams += `&website_id=${selectedWebsiteId}`;

      const [ovData, tsData, inData, fnData] = await Promise.all([
        apiRequest<AnalyticsOverview>(`/analytics/overview?${queryParams}`),
        apiRequest<{ points: TimeseriesPoint[] }>(`/analytics/timeseries?${queryParams}`),
        apiRequest<{ intents: IntentItem[] }>(`/analytics/intents?${queryParams}`),
        apiRequest<{ stages: FunnelStage[] }>(`/analytics/conversions?${queryParams}`),
      ]);

      setOverview(ovData);
      setTimeseries(tsData.points);
      setIntents(inData.intents);
      setFunnel(fnData.stages);
    } catch (err) {
      console.error("Failed to load analytics", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [currentOrg, period, selectedWebsiteId]);

  const maxConv = Math.max(...timeseries.map((p) => p.conversations), 1);

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-indigo-400" />
            <span>Conversation Analytics &amp; Conversion Insights</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time customer engagement metrics, bot resolution rates, and commerce conversion tracking.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Website Filter */}
          <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300">
            <Globe className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={selectedWebsiteId}
              onChange={(e) => setSelectedWebsiteId(e.target.value)}
              className="bg-transparent text-xs text-white focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-white">All Connected Stores</option>
              {websites.map((w) => (
                <option key={w.id} value={w.id} className="bg-slate-900 text-white">
                  {w.name} ({w.domain})
                </option>
              ))}
            </select>
          </div>

          {/* Time Range Selector */}
          <div className="flex rounded-xl bg-slate-900 border border-slate-800 p-1 text-xs font-semibold text-slate-400">
            {(["7d", "30d", "90d"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded-lg px-3 py-1 transition ${
                  period === p ? "bg-indigo-600 text-white shadow-sm" : "hover:text-slate-200"
                }`}
              >
                {p === "7d" ? "7 Days" : p === "30d" ? "30 Days" : "90 Days"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Sessions */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>Conversations</span>
            <MessageSquare className="h-4 w-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-extrabold text-white">
            {overview?.total_conversations.toLocaleString() || 0}
          </p>
          <p className="text-[10px] text-slate-500 font-mono">
            {overview?.total_messages || 0} messages exchanged
          </p>
        </div>

        {/* Bot Containment */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>Resolution Rate</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-extrabold text-emerald-400">
            {overview?.bot_containment_rate || 100}%
          </p>
          <p className="text-[10px] text-emerald-500/80 font-mono">
            Resolved autonomously by AI
          </p>
        </div>

        {/* Add-to-Cart Conversions */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>Cart Additions</span>
            <ShoppingCart className="h-4 w-4 text-purple-400" />
          </div>
          <p className="text-2xl font-extrabold text-purple-300">
            {overview?.add_to_cart_conversions.toLocaleString() || 0}
          </p>
          <p className="text-[10px] text-purple-400/80 font-mono">
            Direct AI checkout conversions
          </p>
        </div>

        {/* WhatsApp Handoffs */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>WhatsApp Handoffs</span>
            <Phone className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-extrabold text-white">
            {overview?.whatsapp_handoffs_triggered.toLocaleString() || 0}
          </p>
          <p className="text-[10px] text-slate-500 font-mono">
            {overview?.human_escalation_rate || 0}% escalation rate
          </p>
        </div>

        {/* Avg Messages */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
            <span>Avg Session Depth</span>
            <TrendingUp className="h-4 w-4 text-amber-400" />
          </div>
          <p className="text-2xl font-extrabold text-amber-300">
            {overview?.avg_messages_per_conversation || 0}
          </p>
          <p className="text-[10px] text-slate-500 font-mono">
            Messages per visitor chat
          </p>
        </div>
      </div>

      {/* Main Charts & Breakdown Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Timeseries Trend Visualizer (8 cols) */}
        <div className="lg:col-span-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm shadow-xl space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-indigo-400" />
              <span>Daily Conversation Volume Trend</span>
            </h3>
            <span className="text-[10px] font-mono text-slate-500">
              {period === "7d" ? "Past 7 Days" : period === "30d" ? "Past 30 Days" : "Past 90 Days"}
            </span>
          </div>

          {/* Bar Chart Visualizer */}
          <div className="h-56 flex items-end gap-1 sm:gap-2 pt-6 pb-2 px-2 border-b border-slate-800/80">
            {timeseries.map((pt, idx) => {
              const heightPct = Math.max(8, Math.round((pt.conversations / maxConv) * 100));
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1 group relative h-full justify-end">
                  {/* Tooltip */}
                  <div className="absolute -top-8 bg-slate-950 border border-slate-700 text-white px-2 py-0.5 rounded text-[10px] font-mono opacity-0 group-hover:opacity-100 transition pointer-events-none whitespace-nowrap z-10">
                    {pt.label}: {pt.conversations} chats
                  </div>

                  <div
                    className="w-full rounded-t-md bg-indigo-500 hover:bg-indigo-400 transition-all duration-300"
                    style={{ height: `${heightPct}%` }}
                  />
                </div>
              );
            })}
          </div>

          <div className="flex justify-between text-[10px] font-mono text-slate-500 px-1">
            <span>{timeseries[0]?.label}</span>
            <span>{timeseries[Math.floor(timeseries.length / 2)]?.label}</span>
            <span>{timeseries[timeseries.length - 1]?.label}</span>
          </div>
        </div>

        {/* Customer Intent Heatmap (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm shadow-xl space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-400" />
              <span>Customer Inquiries by Topic</span>
            </h3>
          </div>

          <div className="space-y-3.5 pt-1">
            {intents.map((item, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-300 truncate">{item.intent}</span>
                  <span className="font-mono text-slate-400 text-[11px]">{item.percentage}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"
                    style={{ width: `${Math.min(100, item.percentage)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Commerce Conversion Funnel */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm shadow-xl space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <ShoppingCart className="h-4 w-4 text-emerald-400" />
            <span>Commerce Conversion Funnel</span>
          </h3>
          <span className="text-[10px] font-mono text-emerald-400">
            AI Sales Pipeline
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {funnel.map((stage, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2 relative"
            >
              <div className="text-[11px] font-semibold text-slate-400">
                Stage {idx + 1}
              </div>
              <p className="text-xs font-bold text-white leading-snug">
                {stage.stage}
              </p>
              <div className="flex items-baseline justify-between pt-1">
                <span className="text-xl font-extrabold text-indigo-400">
                  {stage.count.toLocaleString()}
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {stage.conversion_rate}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
