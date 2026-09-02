"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  Globe,
  Plus,
  ExternalLink,
  Settings,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Code,
  Shield,
  Layers,
  Sparkles,
} from "lucide-react";

export interface Website {
  id: string;
  organization_id: string;
  name: string;
  url: string;
  domain: string;
  public_site_id: string;
  platform: "WORDPRESS" | "WOOCOMMERCE" | "SHOPIFY" | "CUSTOM" | "UNKNOWN";
  status: "ACTIVE" | "INACTIVE" | "PENDING_VERIFICATION";
  created_at: string;
  updated_at: string;
}

export default function WebsitesListPage() {
  const { currentOrg } = useAuth();
  const [websites, setWebsites] = useState<Website[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Add Website Modal
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [siteName, setSiteName] = useState("");
  const [siteUrl, setSiteUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canManage = currentOrg?.role === "OWNER" || currentOrg?.role === "ADMIN";

  const fetchWebsites = async () => {
    if (!currentOrg) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiRequest<Website[]>(`/websites?org_id=${currentOrg.id}`);
      setWebsites(data);
    } catch (err: any) {
      setError(err.message || "Failed to load organization websites");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWebsites();
  }, [currentOrg]);

  const handleAddWebsite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg) return;
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      await apiRequest(`/websites?org_id=${currentOrg.id}`, {
        method: "POST",
        body: JSON.stringify({
          name: siteName.trim(),
          url: siteUrl.trim(),
        }),
      });

      setSuccess(`Website '${siteName}' created successfully!`);
      setSiteName("");
      setSiteUrl("");
      setIsAddOpen(false);
      await fetchWebsites();
    } catch (err: any) {
      setError(err.message || "Failed to add website");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteWebsite = async (websiteId: string, name: string) => {
    if (!currentOrg || !canManage) return;
    if (!confirm(`Are you sure you want to delete website '${name}' and all its settings?`)) return;

    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/websites/${websiteId}?org_id=${currentOrg.id}`, {
        method: "DELETE",
      });
      setSuccess("Website deleted successfully");
      await fetchWebsites();
    } catch (err: any) {
      setError(err.message || "Failed to delete website");
    }
  };

  const platformBadgeColor: Record<string, string> = {
    WORDPRESS: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    WOOCOMMERCE: "bg-purple-500/10 text-purple-400 border-purple-500/30",
    SHOPIFY: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    CUSTOM: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
    UNKNOWN: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Connected Websites</h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage websites, configure chat appearance, and grab embed codes for your channels.
          </p>
        </div>
        {canManage && (
          <button
            onClick={() => setIsAddOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500"
          >
            <Plus className="h-4 w-4" />
            <span>Add Website</span>
          </button>
        )}
      </div>

      {/* Alerts */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-xs text-emerald-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Website Cards Grid */}
      {isLoading ? (
        <div className="p-16 text-center text-xs text-slate-500">Loading websites...</div>
      ) : websites.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-800 bg-slate-900/30 p-12 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 mb-4">
            <Globe className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-white">No websites connected yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 mb-6">
            Add your company website or e-commerce store to enable intelligent AI customer service and product recommendations.
          </p>
          {canManage && (
            <button
              onClick={() => setIsAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500"
            >
              <Plus className="h-4 w-4" />
              <span>Connect Your First Website</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {websites.map((site) => (
            <div
              key={site.id}
              className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-900/50 p-6 transition-all hover:border-slate-700 hover:shadow-xl backdrop-blur-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 font-bold">
                      <Globe className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white truncate max-w-[180px]">{site.name}</h3>
                      <a
                        href={site.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-indigo-400 transition truncate"
                      >
                        <span>{site.domain}</span>
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    </div>
                  </div>

                  <span
                    className={`rounded-lg border px-2 py-0.5 text-[10px] font-bold ${
                      platformBadgeColor[site.platform] || platformBadgeColor.UNKNOWN
                    }`}
                  >
                    {site.platform}
                  </span>
                </div>

                <div className="mt-4 rounded-xl bg-slate-950/60 p-3 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Public Site ID:</span>
                    <span className="font-mono text-indigo-300 truncate max-w-[140px] text-[10px]">
                      {site.public_site_id}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Status:</span>
                    <span className="inline-flex items-center gap-1 text-emerald-400 font-medium text-[10px]">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      {site.status}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between border-t border-slate-800/80 pt-4">
                <Link
                  href={`/dashboard/websites/${site.id}`}
                  className="flex items-center gap-1.5 rounded-xl bg-indigo-600/10 border border-indigo-500/30 px-3 py-1.5 text-xs font-semibold text-indigo-300 hover:bg-indigo-600/20 transition"
                >
                  <Settings className="h-3.5 w-3.5" />
                  <span>Configure & Install</span>
                </Link>

                {canManage && (
                  <button
                    onClick={() => handleDeleteWebsite(site.id, site.name)}
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition"
                    title="Delete Website"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Website Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
              <h3 className="text-base font-bold text-white">Add Website to Workspace</h3>
              <button onClick={() => setIsAddOpen(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleAddWebsite} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Website / Store Name
                </label>
                <input
                  type="text"
                  required
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  placeholder="e.g. My Online Store"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Website URL
                </label>
                <div className="relative">
                  <Globe className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={siteUrl}
                    onChange={(e) => setSiteUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  Domain will be normalized automatically (e.g. https://example.com).
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="rounded-xl border border-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                >
                  {isSubmitting ? "Creating..." : "Add Website"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
