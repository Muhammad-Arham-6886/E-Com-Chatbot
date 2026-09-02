"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  Plug,
  ShoppingBag,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Key,
  ShieldCheck,
  Globe,
  Trash2,
  Layers,
  ArrowRight,
  Phone,
  Store,
  Sparkles,
} from "lucide-react";

interface Website {
  id: string;
  name: string;
  domain: string;
}

interface WooCommerceIntegration {
  id: string;
  website_id: string;
  organization_id: string;
  platform: string;
  api_url: string;
  consumer_key_masked: string;
  is_active: boolean;
  last_sync_at: string | null;
  metadata_json: string | null;
  created_at: string;
}

interface TestResult {
  success: boolean;
  status_code: number;
  message: string;
  currency: string;
  product_count: number;
  sample_products: Array<{
    id: string;
    name: string;
    price: number;
    currency: string;
    description: string;
    image_url: string | null;
    product_url: string;
    in_stock: boolean;
  }>;
}

export default function IntegrationsPage() {
  const { currentOrg } = useAuth();
  const canManage = currentOrg?.role === "OWNER" || currentOrg?.role === "ADMIN";

  const [websites, setWebsites] = useState<Website[]>([]);
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string>("");
  const [integration, setIntegration] = useState<WooCommerceIntegration | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Form State
  const [apiUrl, setApiUrl] = useState("");
  const [consumerKey, setConsumerKey] = useState("");
  const [consumerSecret, setConsumerSecret] = useState("");
  const [isConnecting, setIsConnecting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchWebsites = async () => {
    if (!currentOrg) return;
    try {
      const sites = await apiRequest<Website[]>(`/websites?org_id=${currentOrg.id}`);
      setWebsites(sites);
      if (sites.length > 0) {
        setSelectedWebsiteId(sites[0].id);
        fetchIntegration(sites[0].id);
      } else {
        setIsLoading(false);
      }
    } catch (err) {
      console.error(err);
      setIsLoading(false);
    }
  };

  const fetchIntegration = async (websiteId: string) => {
    if (!currentOrg || !websiteId) return;
    setIsLoading(true);
    setError(null);
    setTestResult(null);
    try {
      const data = await apiRequest<WooCommerceIntegration | null>(
        `/integrations/woocommerce/${websiteId}?org_id=${currentOrg.id}`
      );
      setIntegration(data);
      if (data) {
        setApiUrl(data.api_url);
      } else {
        const site = websites.find((w) => w.id === websiteId);
        setApiUrl(site ? `https://${site.domain}` : "");
        setConsumerKey("");
        setConsumerSecret("");
      }
    } catch (err) {
      console.error("Error fetching integration:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWebsites();
  }, [currentOrg]);

  const handleConnectWooCommerce = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !selectedWebsiteId || !canManage) return;

    setIsConnecting(true);
    setError(null);
    setSuccess(null);
    setTestResult(null);

    try {
      const res = await apiRequest<WooCommerceIntegration>(
        `/integrations/woocommerce/connect?org_id=${currentOrg.id}`,
        {
          method: "POST",
          body: JSON.stringify({
            website_id: selectedWebsiteId,
            api_url: apiUrl,
            consumer_key: consumerKey,
            consumer_secret: consumerSecret,
            is_active: true,
          }),
        }
      );

      setIntegration(res);
      setSuccess("WooCommerce REST API connected and verified successfully!");
      setConsumerSecret("");
      // Automatically test live product fetch
      handleTestConnection();
    } catch (err: any) {
      setError(err.message || "Failed to connect to WooCommerce REST API.");
    } finally {
      setIsConnecting(false);
    }
  };

  const handleTestConnection = async () => {
    if (!currentOrg || !selectedWebsiteId || !canManage) return;
    setIsTesting(true);
    setError(null);
    try {
      const res = await apiRequest<TestResult>(
        `/integrations/woocommerce/${selectedWebsiteId}/test?org_id=${currentOrg.id}`,
        { method: "POST" }
      );
      setTestResult(res);
    } catch (err: any) {
      setError(err.message || "Test connection failed.");
    } finally {
      setIsTesting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!currentOrg || !selectedWebsiteId || !canManage) return;
    if (!confirm("Are you sure you want to disconnect WooCommerce for this website?")) return;

    try {
      await apiRequest(
        `/integrations/woocommerce/${selectedWebsiteId}?org_id=${currentOrg.id}`,
        { method: "DELETE" }
      );
      setIntegration(null);
      setTestResult(null);
      setConsumerKey("");
      setConsumerSecret("");
      setSuccess("WooCommerce integration disconnected.");
    } catch (err: any) {
      setError(err.message || "Failed to disconnect integration.");
    }
  };

  const selectedSite = websites.find((w) => w.id === selectedWebsiteId);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">E-Commerce & Platform Integrations</h1>
          <p className="text-xs text-slate-400 mt-1">
            Connect live WooCommerce REST APIs to enable real-time product discovery, live catalog search, and direct checkout cart actions.
          </p>
        </div>

        {websites.length > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-400">Target Store:</span>
            <select
              value={selectedWebsiteId}
              onChange={(e) => {
                setSelectedWebsiteId(e.target.value);
                fetchIntegration(e.target.value);
              }}
              className="rounded-xl border border-slate-800 bg-slate-900 py-2 px-3 text-xs text-white focus:border-indigo-500 focus:outline-none"
            >
              {websites.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.domain})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Main Grid: WooCommerce Setup & Other Integrations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* WooCommerce Connection Panel (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/30 text-purple-400 shadow-md">
                  <Store className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span>WooCommerce REST API v3</span>
                    {integration ? (
                      <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="h-2.5 w-2.5" />
                        Connected
                      </span>
                    ) : (
                      <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                        Not Connected
                      </span>
                    )}
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Enables AI Assistant to query live product inventory, price, and generate add-to-cart URLs.
                  </p>
                </div>
              </div>

              {integration && canManage && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleTestConnection}
                    disabled={isTesting}
                    className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700 transition"
                  >
                    <RefreshCw className={`h-3 w-3 ${isTesting ? "animate-spin" : ""}`} />
                    <span>{isTesting ? "Testing..." : "Test Connection"}</span>
                  </button>
                  <button
                    onClick={handleDisconnect}
                    className="rounded-xl border border-rose-500/30 p-1.5 text-rose-400 hover:bg-rose-500/10 transition"
                    title="Disconnect"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Connection Form */}
            <form onSubmit={handleConnectWooCommerce} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Store Base URL
                </label>
                <input
                  type="url"
                  required
                  disabled={!canManage}
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  placeholder="https://yourstore.com"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    Consumer Key (ck_...)
                  </label>
                  <input
                    type="text"
                    required={!integration}
                    disabled={!canManage}
                    value={consumerKey}
                    onChange={(e) => setConsumerKey(e.target.value)}
                    placeholder={integration ? integration.consumer_key_masked : "ck_xxxxxxxxxxxxxxxxxxxx"}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs font-mono text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    Consumer Secret (cs_...)
                  </label>
                  <input
                    type="password"
                    required={!integration}
                    disabled={!canManage}
                    value={consumerSecret}
                    onChange={(e) => setConsumerSecret(e.target.value)}
                    placeholder={integration ? "••••••••••••••••••••" : "cs_xxxxxxxxxxxxxxxxxxxx"}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs font-mono text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="rounded-xl bg-slate-950/70 border border-slate-800/80 p-3 text-[11px] text-slate-400 space-y-1">
                <p className="font-semibold text-slate-300">How to generate WooCommerce API keys:</p>
                <p>1. In your WordPress Admin, navigate to <strong>WooCommerce</strong> ➔ <strong>Settings</strong> ➔ <strong>Advanced</strong> ➔ <strong>REST API</strong>.</p>
                <p>2. Click <strong>Add Key</strong>, set Permissions to <strong>Read</strong> (or Read/Write), and copy the keys above.</p>
              </div>

              {canManage && (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                  {selectedWebsiteId ? (
                    <a
                      href={`http://localhost:8000/api/v1/websites/${selectedWebsiteId}/download-plugin?org_id=${currentOrg?.id}`}
                      download
                      className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 transition"
                    >
                      <Plug className="h-3.5 w-3.5" />
                      <span>Download WordPress Plugin (.zip)</span>
                    </a>
                  ) : <div />}

                  <button
                    type="submit"
                    disabled={isConnecting}
                    className="flex items-center gap-2 rounded-xl bg-purple-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-purple-600/30 hover:bg-purple-500 disabled:opacity-50 transition"
                  >
                    <Plug className="h-4 w-4" />
                    <span>{isConnecting ? "Validating & Connecting..." : integration ? "Update Keys" : "Connect WooCommerce"}</span>
                  </button>
                </div>
              )}
            </form>
          </div>

          {/* Live Catalog Preview if tested */}
          {testResult && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h4 className="text-xs font-bold text-white flex items-center gap-2">
                  <ShoppingBag className="h-4 w-4 text-purple-400" />
                  <span>Live WooCommerce Catalog Verification</span>
                </h4>
                <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-mono text-emerald-400">
                  {testResult.product_count} Products Found
                </span>
              </div>

              <p className="text-xs text-slate-400">{testResult.message}</p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {testResult.sample_products.map((prod) => (
                  <div
                    key={prod.id}
                    className="rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2 flex flex-col justify-between"
                  >
                    {prod.image_url ? (
                      <img
                        src={prod.image_url}
                        alt={prod.name}
                        className="h-24 w-full rounded-lg object-cover bg-slate-900"
                      />
                    ) : (
                      <div className="h-24 w-full rounded-lg bg-slate-900 flex items-center justify-center text-slate-700">
                        <ShoppingBag className="h-8 w-8" />
                      </div>
                    )}
                    <div>
                      <p className="font-bold text-white text-xs truncate">{prod.name}</p>
                      <p className="text-emerald-400 font-mono text-xs font-bold mt-0.5">
                        ${prod.price.toFixed(2)} {prod.currency}
                      </p>
                    </div>
                    <a
                      href={prod.product_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-center gap-1 rounded-lg bg-slate-900 border border-slate-800 py-1 text-[10px] font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition"
                    >
                      <ExternalLink className="h-2.5 w-2.5" />
                      <span>View Storefront</span>
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar: Other Integrations */}
        <div className="space-y-5">
          {/* WhatsApp Card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600/20 border border-emerald-500/30 text-emerald-400">
                <Phone className="h-4 w-4" />
              </div>
              <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                Phase 9 Native
              </span>
            </div>
            <div>
              <h4 className="text-xs font-bold text-white">WhatsApp Escalation Bridge</h4>
              <p className="text-[11px] text-slate-400 mt-1">
                Direct WhatsApp click-to-chat button with pre-filled context and customer inquiry summary.
              </p>
            </div>
            <Link
              href={selectedWebsiteId ? `/dashboard/websites/${selectedWebsiteId}` : "/dashboard/websites"}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 hover:underline"
            >
              <span>Configure in Website Settings</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {/* Shopify Card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-sm space-y-3 opacity-80">
            <div className="flex items-center justify-between">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600/20 border border-emerald-500/30 text-emerald-400">
                <Store className="h-4 w-4" />
              </div>
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                Architecture Ready
              </span>
            </div>
            <div>
              <h4 className="text-xs font-bold text-white">Shopify Storefront API</h4>
              <p className="text-[11px] text-slate-400 mt-1">
                Connect Shopify Storefront GraphQL tokens to search collections and generate permalink checkouts.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
