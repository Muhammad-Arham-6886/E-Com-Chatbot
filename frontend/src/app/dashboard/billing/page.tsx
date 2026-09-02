"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  CreditCard,
  CheckCircle2,
  Sparkles,
  Zap,
  Globe,
  MessageSquare,
  Layers,
  AlertTriangle,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";

interface UsageMetric {
  used: number;
  limit: number;
  percentage: number;
}

interface UsageBreakdown {
  tier: string;
  tier_name: string;
  price_monthly: number;
  status: string;
  billing_period: string;
  period_end?: string | null;
  websites: UsageMetric;
  chat_messages: UsageMetric;
  vector_chunks: UsageMetric;
  tokens_consumed: number;
}

interface PlanTier {
  tier: string;
  name: string;
  price_monthly: number;
  max_websites: number;
  max_pages_per_crawl: number;
  max_chunks: number;
  max_monthly_messages: number;
  rate_limit_rpm: number;
  features: string[];
}

export default function BillingPage() {
  const { currentOrg } = useAuth();
  const [usage, setUsage] = useState<UsageBreakdown | null>(null);
  const [tiers, setTiers] = useState<PlanTier[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canManageBilling = currentOrg?.role === "OWNER" || currentOrg?.role === "ADMIN";

  const fetchBillingData = async () => {
    if (!currentOrg) return;
    setIsLoading(true);
    setError(null);
    try {
      const [usageData, tiersData] = await Promise.all([
        apiRequest<UsageBreakdown>(`/billing/usage?org_id=${currentOrg.id}`),
        apiRequest<PlanTier[]>("/billing/tiers"),
      ]);
      setUsage(usageData);
      setTiers(tiersData);
    } catch (err: any) {
      setError(err.message || "Failed to load billing and usage data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBillingData();
  }, [currentOrg]);

  const handleTierChange = async (targetTier: string) => {
    if (!currentOrg || !canManageBilling) return;
    setIsUpdating(true);
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/billing/change-tier?org_id=${currentOrg.id}`, {
        method: "POST",
        body: JSON.stringify({ tier: targetTier }),
      });
      setSuccess(`Successfully updated subscription to ${targetTier} plan!`);
      await fetchBillingData();
    } catch (err: any) {
      setError(err.message || "Failed to update subscription tier");
    } finally {
      setIsUpdating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
      </div>
    );
  }

  const isNearLimit =
    (usage?.websites.percentage || 0) >= 80 ||
    (usage?.chat_messages.percentage || 0) >= 80 ||
    (usage?.vector_chunks.percentage || 0) >= 80;

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-indigo-400" />
          <span>Plans, Quotas &amp; Usage Metering</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Monitor your organization&apos;s real-time resource utilization, vector indexing limits, and active subscription plan.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-400 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {isNearLimit && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
            <span>
              Your organization is approaching or has exceeded 80% of its resource quotas for the current billing cycle.
            </span>
          </div>
          <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">Quota Alert</span>
        </div>
      )}

      {/* Usage Meter Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Websites */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Globe className="h-4 w-4 text-indigo-400" />
              Connected Websites
            </span>
            <span className="text-xs font-mono font-bold text-white">
              {usage?.websites.used} / {usage && usage.websites.limit >= 999999 ? "∞" : usage?.websites.limit}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                (usage?.websites.percentage || 0) >= 90
                  ? "bg-rose-500"
                  : (usage?.websites.percentage || 0) >= 75
                  ? "bg-amber-500"
                  : "bg-indigo-500"
              }`}
              style={{ width: `${Math.min(100, usage?.websites.percentage || 0)}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-500 flex justify-between font-mono">
            <span>{usage?.websites.percentage}% capacity</span>
            <span>Max {usage && usage.websites.limit >= 999999 ? "Unlimited" : usage?.websites.limit}</span>
          </div>
        </div>

        {/* Monthly Messages */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <MessageSquare className="h-4 w-4 text-emerald-400" />
              Monthly Messages
            </span>
            <span className="text-xs font-mono font-bold text-white">
              {usage?.chat_messages.used} / {usage && usage.chat_messages.limit >= 999999 ? "∞" : usage?.chat_messages.limit}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                (usage?.chat_messages.percentage || 0) >= 90
                  ? "bg-rose-500"
                  : (usage?.chat_messages.percentage || 0) >= 75
                  ? "bg-amber-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(100, usage?.chat_messages.percentage || 0)}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-500 flex justify-between font-mono">
            <span>{usage?.chat_messages.percentage}% utilized</span>
            <span>Period: {usage?.billing_period}</span>
          </div>
        </div>

        {/* Vector Chunks */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Layers className="h-4 w-4 text-purple-400" />
              Vector Chunks
            </span>
            <span className="text-xs font-mono font-bold text-white">
              {usage?.vector_chunks.used} / {usage && usage.vector_chunks.limit >= 999999 ? "∞" : usage?.vector_chunks.limit}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                (usage?.vector_chunks.percentage || 0) >= 90
                  ? "bg-rose-500"
                  : (usage?.vector_chunks.percentage || 0) >= 75
                  ? "bg-amber-500"
                  : "bg-purple-500"
              }`}
              style={{ width: `${Math.min(100, usage?.vector_chunks.percentage || 0)}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-500 flex justify-between font-mono">
            <span>{usage?.vector_chunks.percentage}% indexed</span>
            <span>pgvector 768-d</span>
          </div>
        </div>

        {/* Tokens & LLM */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-amber-400" />
              Tokens Consumed
            </span>
            <span className="text-xs font-mono font-bold text-amber-300">
              {usage?.tokens_consumed.toLocaleString()}
            </span>
          </div>
          <div className="text-[11px] text-slate-300">
            Powered by local Ollama &amp; pgvector RAG pipeline.
          </div>
          <div className="text-[10px] text-slate-500 flex justify-between font-mono">
            <span>Current Tier</span>
            <span className="text-indigo-400 font-bold">{usage?.tier_name}</span>
          </div>
        </div>
      </div>

      {/* Subscription Plans Grid */}
      <div className="space-y-4">
        <div>
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Zap className="h-4 w-4 text-indigo-400" />
            <span>Available Subscription Tiers</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Upgrade your plan to unlock higher crawl quotas, additional website connections, and unlimited RAG indexing.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {tiers.map((plan) => {
            const isCurrentPlan = usage?.tier === plan.tier;
            return (
              <div
                key={plan.tier}
                className={`rounded-2xl border p-6 flex flex-col justify-between transition relative ${
                  isCurrentPlan
                    ? "border-indigo-500/60 bg-indigo-950/20 shadow-xl shadow-indigo-500/10 ring-1 ring-indigo-500/50"
                    : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
                }`}
              >
                {isCurrentPlan && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-indigo-600 border border-indigo-400/30 px-3 py-0.5 text-[10px] font-bold text-white tracking-wide uppercase">
                    Active Plan
                  </span>
                )}

                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-bold text-white">{plan.name}</h3>
                    <div className="mt-2 flex items-baseline gap-1">
                      <span className="text-2xl font-extrabold text-white">
                        ${plan.price_monthly}
                      </span>
                      <span className="text-xs text-slate-400">/ month</span>
                    </div>
                  </div>

                  <ul className="space-y-2 text-[11px] text-slate-300 border-t border-slate-800/80 pt-4">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <CheckCircle2 className="h-3.5 w-3.5 text-indigo-400 shrink-0 mt-0.5" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-6">
                  {isCurrentPlan ? (
                    <div className="w-full text-center py-2.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 text-xs font-bold text-indigo-300 flex items-center justify-center gap-1.5">
                      <ShieldCheck className="h-4 w-4" />
                      <span>Current Plan</span>
                    </div>
                  ) : (
                    <button
                      disabled={!canManageBilling || isUpdating}
                      onClick={() => handleTierChange(plan.tier)}
                      className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 transition"
                    >
                      <span>{isUpdating ? "Switching..." : `Select ${plan.name.split(" ")[0]}`}</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
