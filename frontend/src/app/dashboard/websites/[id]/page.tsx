"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  Globe,
  ArrowLeft,
  Settings,
  Paintbrush,
  Code2,
  Cpu,
  Layers,
  ExternalLink,
  Copy,
  Check,
  Play,
  AlertCircle,
  CheckCircle2,
  Save,
  MessageSquare,
  Sparkles,
  Shield,
  Trash2,
  FileText,
  RefreshCw,
  XCircle,
  Eye,
  CheckCircle,
  Phone,
  MessageCircle,
} from "lucide-react";

interface WebsiteSettings {
  id: string;
  website_id: string;
  chatbot_name: string;
  welcome_message: string;
  placeholder_text: string;
  primary_color: string;
  secondary_color: string;
  launcher_position: string;
  widget_size: string;
  border_radius: string;
  enable_whatsapp: boolean;
  whatsapp_number?: string | null;
  whatsapp_custom_message?: string | null;
  whatsapp_handoff_trigger?: string;
  custom_instructions?: string | null;
}

interface WebsiteDetail {
  id: string;
  organization_id: string;
  name: string;
  url: string;
  domain: string;
  public_site_id: string;
  platform: "WORDPRESS" | "WOOCOMMERCE" | "SHOPIFY" | "CUSTOM" | "UNKNOWN";
  status: "ACTIVE" | "INACTIVE" | "PENDING_VERIFICATION";
  created_at: string;
  settings?: WebsiteSettings;
}

interface CrawlJob {
  id: string;
  website_id: string;
  organization_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
  total_pages_discovered: number;
  total_pages_crawled: number;
  total_pages_failed: number;
  max_pages: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

interface CrawlPage {
  id: string;
  crawl_job_id: string;
  website_id: string;
  url: string;
  status: "DISCOVERED" | "CRAWLED" | "SKIPPED_ROBOTS" | "FAILED" | "DUPLICATE";
  status_code?: number | null;
  page_title?: string | null;
  content_hash?: string | null;
  error?: string | null;
  discovered_via: string;
  depth: number;
  created_at: string;
}

interface KnowledgeDocument {
  id: string;
  website_id: string;
  organization_id: string;
  crawl_page_id?: string | null;
  url: string;
  title: string;
  meta_description?: string | null;
  raw_content: string;
  content_hash: string;
  token_count: number;
  status: "RAW" | "PROCESSED" | "SYNCED";
  created_at: string;
}

export default function WebsiteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const websiteId = params.id as string;
  const { currentOrg } = useAuth();

  const [website, setWebsite] = useState<WebsiteDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "crawler" | "appearance" | "whatsapp" | "installation" | "settings">("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Crawler State
  const [crawlPages, setCrawlPages] = useState<CrawlPage[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [activeCrawlJob, setActiveCrawlJob] = useState<CrawlJob | null>(null);
  const [isStartingCrawl, setIsStartingCrawl] = useState(false);
  const [isStartModalOpen, setIsStartModalOpen] = useState(false);
  const [maxPagesLimit, setMaxPagesLimit] = useState(50);
  const [crawlerSubTab, setCrawlerSubTab] = useState<"pages" | "documents">("pages");
  const [previewDoc, setPreviewDoc] = useState<KnowledgeDocument | null>(null);

  // Appearance Form State
  const [chatbotName, setChatbotName] = useState("");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [placeholderText, setPlaceholderText] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#4F46E5");
  const [secondaryColor, setSecondaryColor] = useState("#1E1B4B");
  const [launcherPosition, setLauncherPosition] = useState("bottom-right");
  const [enableWhatsapp, setEnableWhatsapp] = useState(false);
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [whatsappCustomMessage, setWhatsappCustomMessage] = useState("");
  const [whatsappHandoffTrigger, setWhatsappHandoffTrigger] = useState("ON_ESCALATION");
  const [sampleInquiry, setSampleInquiry] = useState("Do you offer express international shipping?");
  const [isSavingWhatsapp, setIsSavingWhatsapp] = useState(false);
  const [customInstructions, setCustomInstructions] = useState("");

  // Settings Form State
  const [editName, setEditName] = useState("");
  const [editUrl, setEditUrl] = useState("");
  const [editStatus, setEditStatus] = useState<"ACTIVE" | "INACTIVE">("ACTIVE");
  const [isSavingBasic, setIsSavingBasic] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Platform Detection State
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionResult, setDetectionResult] = useState<any>(null);

  const canManage = currentOrg?.role === "OWNER" || currentOrg?.role === "ADMIN";

  const fetchWebsiteDetails = async () => {
    if (!currentOrg || !websiteId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiRequest<WebsiteDetail>(`/websites/${websiteId}?org_id=${currentOrg.id}`);
      setWebsite(data);

      if (data.settings) {
        setChatbotName(data.settings.chatbot_name || "AI Assistant");
        setWelcomeMessage(data.settings.welcome_message || "Hi there! How can I help you today?");
        setPlaceholderText(data.settings.placeholder_text || "Type your message here...");
        setPrimaryColor(data.settings.primary_color || "#4F46E5");
        setSecondaryColor(data.settings.secondary_color || "#1E1B4B");
        setLauncherPosition(data.settings.launcher_position || "bottom-right");
        setEnableWhatsapp(data.settings.enable_whatsapp || false);
        setWhatsappNumber(data.settings.whatsapp_number || "");
        setWhatsappCustomMessage(data.settings.whatsapp_custom_message || "");
        setWhatsappHandoffTrigger(data.settings.whatsapp_handoff_trigger || "ON_ESCALATION");
        setCustomInstructions(data.settings.custom_instructions || "");
      }

      setEditName(data.name);
      setEditUrl(data.url);
      setEditStatus(data.status === "INACTIVE" ? "INACTIVE" : "ACTIVE");

      await fetchCrawlerData();
    } catch (err: any) {
      setError(err.message || "Failed to load website details");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCrawlerData = async () => {
    if (!currentOrg || !websiteId) return;
    try {
      const [pages, docs] = await Promise.all([
        apiRequest<CrawlPage[]>(`/crawling/websites/${websiteId}/pages?org_id=${currentOrg.id}`).catch(() => []),
        apiRequest<KnowledgeDocument[]>(`/crawling/websites/${websiteId}/documents?org_id=${currentOrg.id}`).catch(() => []),
      ]);
      setCrawlPages(pages);
      setDocuments(docs);
    } catch (err) {
      console.error("Error fetching crawler data", err);
    }
  };

  useEffect(() => {
    fetchWebsiteDetails();
  }, [currentOrg, websiteId]);

  // Poll active crawl job status every 3 seconds so the UI updates in real-time
  useEffect(() => {
    if (!activeCrawlJob || !currentOrg) return;
    if (activeCrawlJob.status !== "PENDING" && activeCrawlJob.status !== "RUNNING") return;

    const interval = setInterval(async () => {
      try {
        const updated = await apiRequest<CrawlJob>(
          `/crawling/jobs/${activeCrawlJob.id}?org_id=${currentOrg.id}`
        );
        setActiveCrawlJob(updated);
        if (updated.status !== "PENDING" && updated.status !== "RUNNING") {
          fetchCrawlerData();
        }
      } catch {
        // ignore polling errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [activeCrawlJob?.id, activeCrawlJob?.status, currentOrg]);

  const copyPublicId = () => {
    if (!website) return;
    navigator.clipboard.writeText(website.public_site_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleStartCrawl = async () => {
    if (!currentOrg || !websiteId || !canManage) return;
    setIsStartingCrawl(true);
    setError(null);
    setSuccess(null);

    try {
      const job = await apiRequest<CrawlJob>(`/crawling/websites/${websiteId}/start?org_id=${currentOrg.id}`, {
        method: "POST",
        body: JSON.stringify({ max_pages: maxPagesLimit }),
      });
      setActiveCrawlJob(job);
      setIsStartModalOpen(false);
      setSuccess(`Crawl job started! Scraping up to ${maxPagesLimit} pages from ${website?.domain}.`);
      // Refresh crawler data
      setTimeout(() => fetchCrawlerData(), 2000);
    } catch (err: any) {
      setError(err.message || "Failed to start crawl job");
    } finally {
      setIsStartingCrawl(false);
    }
  };

  const handleCancelCrawl = async () => {
    if (!currentOrg || !activeCrawlJob || !canManage) return;
    try {
      const updated = await apiRequest<CrawlJob>(`/crawling/jobs/${activeCrawlJob.id}/cancel?org_id=${currentOrg.id}`, {
        method: "POST",
      });
      setActiveCrawlJob(updated);
      setSuccess("Crawl job cancelled.");
      await fetchCrawlerData();
    } catch (err: any) {
      setError(err.message || "Failed to cancel crawl job");
    }
  };

  const handleSaveAppearance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !websiteId || !canManage) return;
    setIsSavingSettings(true);
    setError(null);
    setSuccess(null);

    try {
      await apiRequest(`/websites/${websiteId}/settings?org_id=${currentOrg.id}`, {
        method: "PUT",
        body: JSON.stringify({
          chatbot_name: chatbotName,
          welcome_message: welcomeMessage,
          placeholder_text: placeholderText,
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          launcher_position: launcherPosition,
          enable_whatsapp: enableWhatsapp,
          whatsapp_number: whatsappNumber || null,
          custom_instructions: customInstructions || null,
        }),
      });
      setSuccess("Chatbot appearance settings saved successfully!");
      await fetchWebsiteDetails();
    } catch (err: any) {
      setError(err.message || "Failed to save settings");
    } finally {
      setIsSavingSettings(false);
    }
  };

  const handleSaveWhatsapp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !websiteId || !canManage) return;
    setIsSavingWhatsapp(true);
    setError(null);
    setSuccess(null);

    try {
      await apiRequest(`/websites/${websiteId}/settings?org_id=${currentOrg.id}`, {
        method: "PUT",
        body: JSON.stringify({
          enable_whatsapp: enableWhatsapp,
          whatsapp_number: whatsappNumber || null,
          whatsapp_custom_message: whatsappCustomMessage || null,
          whatsapp_handoff_trigger: whatsappHandoffTrigger,
        }),
      });
      setSuccess("WhatsApp Bridge settings saved successfully!");
      await fetchWebsiteDetails();
    } catch (err: any) {
      setError(err.message || "Failed to save WhatsApp settings");
    } finally {
      setIsSavingWhatsapp(false);
    }
  };

  const handleSaveBasic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !websiteId || !canManage) return;
    setIsSavingBasic(true);
    setError(null);
    setSuccess(null);

    try {
      await apiRequest(`/websites/${websiteId}?org_id=${currentOrg.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: editName,
          url: editUrl,
          status: editStatus,
        }),
      });
      setSuccess("Website updated successfully!");
      await fetchWebsiteDetails();
    } catch (err: any) {
      setError(err.message || "Failed to update website");
    } finally {
      setIsSavingBasic(false);
    }
  };

  const handleDetectPlatform = async () => {
    if (!currentOrg || !websiteId || !canManage) return;
    setIsDetecting(true);
    setError(null);
    setSuccess(null);
    setDetectionResult(null);

    try {
      const res = await apiRequest(`/websites/${websiteId}/detect-platform?org_id=${currentOrg.id}`, {
        method: "POST",
      });
      setDetectionResult(res);
      setSuccess(`Detection finished: Detected ${res.detected_platform} (${Math.round(res.confidence * 100)}% confidence)`);
      await fetchWebsiteDetails();
    } catch (err: any) {
      setError(err.message || "Platform detection scan failed");
    } finally {
      setIsDetecting(false);
    }
  };

  const handleDeleteWebsite = async () => {
    if (!currentOrg || !website || !canManage) return;
    if (!confirm(`Are you sure you want to permanently delete '${website.name}'?`)) return;

    try {
      await apiRequest(`/websites/${website.id}?org_id=${currentOrg.id}`, {
        method: "DELETE",
      });
      router.push("/dashboard/websites");
    } catch (err: any) {
      setError(err.message || "Failed to delete website");
    }
  };

  if (isLoading) {
    return <div className="p-16 text-center text-xs text-slate-500">Loading website console...</div>;
  }

  if (!website) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm text-red-400">Website not found</p>
        <Link href="/dashboard/websites" className="mt-4 inline-block text-xs text-indigo-400">
          ← Back to Websites
        </Link>
      </div>
    );
  }

  const widgetScriptTag = `<script\n  src="http://localhost:3000/widget.js"\n  data-site-id="${website.public_site_id}"\n  async>\n</script>`;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/websites"
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">{website.name}</h1>
              <span className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-400">
                {website.platform}
              </span>
            </div>
            <a
              href={website.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-indigo-400 transition"
            >
              <span>{website.domain}</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        {/* Public Site ID Pill */}
        <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-1.5 px-3">
          <div className="text-[11px] text-slate-400">Public Site ID:</div>
          <code className="font-mono text-xs font-semibold text-indigo-300">{website.public_site_id}</code>
          <button
            onClick={copyPublicId}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition"
            title="Copy Public ID"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
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

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-6 text-xs font-semibold overflow-x-auto">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-2 pb-3 border-b-2 transition whitespace-nowrap ${
            activeTab === "overview"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Globe className="h-4 w-4" />
          <span>Overview</span>
        </button>

        <button
          onClick={() => setActiveTab("crawler")}
          className={`flex items-center gap-2 pb-3 border-b-2 transition whitespace-nowrap ${
            activeTab === "crawler"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>Crawler & Knowledge</span>
          {documents.length > 0 && (
            <span className="rounded-full bg-indigo-500/20 px-1.5 py-0.2 text-[10px] text-indigo-300 font-mono">
              {documents.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("appearance")}
          className={`flex items-center gap-2 pb-3 border-b-2 transition whitespace-nowrap ${
            activeTab === "appearance"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Paintbrush className="h-4 w-4" />
          <span>Chatbot Appearance</span>
        </button>

        <button
          onClick={() => setActiveTab("whatsapp")}
          className={`flex items-center gap-2 pb-3 border-b-2 transition whitespace-nowrap ${
            activeTab === "whatsapp"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Phone className="h-4 w-4" />
          <span>WhatsApp Bridge</span>
          {website.settings?.enable_whatsapp && (
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          )}
        </button>

        <button
          onClick={() => setActiveTab("installation")}
          className={`flex items-center gap-2 pb-3 border-b-2 transition whitespace-nowrap ${
            activeTab === "installation"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Code2 className="h-4 w-4" />
          <span>Installation & Embed</span>
        </button>

        <button
          onClick={() => setActiveTab("settings")}
          className={`flex items-center gap-2 pb-3 border-b-2 transition whitespace-nowrap ${
            activeTab === "settings"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Settings className="h-4 w-4" />
          <span>Settings</span>
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Platform Profile</span>
                <Cpu className="h-4 w-4 text-indigo-400" />
              </div>
              <p className="mt-2 text-lg font-bold text-white">{website.platform}</p>
              <p className="text-[11px] text-slate-500 mt-1">E-Commerce & CMS integration architecture</p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Indexed Documents</span>
                <FileText className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="mt-2 text-lg font-bold text-emerald-400">{documents.length}</p>
              <p className="text-[11px] text-slate-500 mt-1">Ready for vector embeddings in Phase 4</p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Discovered Pages</span>
                <Layers className="h-4 w-4 text-blue-400" />
              </div>
              <p className="mt-2 text-lg font-bold text-white">{crawlPages.length}</p>
              <p className="text-[11px] text-slate-500 mt-1">Robots.txt & Sitemap URL tree</p>
            </div>
          </div>

          {/* Platform Detection Scanner Card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h3 className="text-sm font-bold text-white">Platform Detection Scanner</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Probes {website.url} headers, meta tags, and endpoints to detect WordPress, WooCommerce, or Shopify.
                </p>
              </div>
              {canManage && (
                <button
                  onClick={handleDetectPlatform}
                  disabled={isDetecting}
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                >
                  <Play className="h-3.5 w-3.5" />
                  <span>{isDetecting ? "Scanning URL..." : "Run Detection Scan"}</span>
                </button>
              )}
            </div>

            {detectionResult && (
              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-300">
                    Result: <span className="text-indigo-400 font-bold">{detectionResult.detected_platform}</span>
                  </span>
                  <span className="text-emerald-400">{Math.round(detectionResult.confidence * 100)}% Confidence</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  <p className="font-semibold text-slate-300 mb-1">Discovered Signals:</p>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-400 font-mono text-[10px]">
                    {detectionResult.detection_signals.map((sig: string, idx: number) => (
                      <li key={idx}>{sig}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Crawler & Knowledge */}
      {activeTab === "crawler" && (
        <div className="space-y-6">
          {/* Crawler Action Bar & Active Job Card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>Website Crawling & Content Discovery Engine</span>
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Discovers robots.txt, recursively parses sitemaps, extracts clean content, and populates knowledge base documents.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={fetchCrawlerData}
                  className="rounded-xl border border-slate-800 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
                  title="Refresh Data"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
                {canManage && (
                  <button
                    onClick={() => setIsStartModalOpen(true)}
                    className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 transition"
                  >
                    <Play className="h-3.5 w-3.5" />
                    <span>Start New Crawl</span>
                  </button>
                )}
              </div>
            </div>

            {/* Active Job Progress Card if running */}
            {activeCrawlJob && (
              <div className="mt-5 rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-4 space-y-3">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
                    <span className="text-indigo-300">Crawl Job #{activeCrawlJob.id.substring(0, 8)}</span>
                    <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] text-indigo-300">
                      {activeCrawlJob.status}
                    </span>
                  </div>
                  {activeCrawlJob.status === "RUNNING" && canManage && (
                    <button
                      onClick={handleCancelCrawl}
                      className="flex items-center gap-1 text-[11px] text-red-400 hover:underline"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      <span>Cancel Job</span>
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-lg bg-slate-950/60 p-2 border border-slate-800">
                    <span className="text-[10px] text-slate-400">Discovered</span>
                    <p className="font-bold text-white">{activeCrawlJob.total_pages_discovered}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/60 p-2 border border-slate-800">
                    <span className="text-[10px] text-slate-400">Crawled</span>
                    <p className="font-bold text-emerald-400">{activeCrawlJob.total_pages_crawled}</p>
                  </div>
                  <div className="rounded-lg bg-slate-950/60 p-2 border border-slate-800">
                    <span className="text-[10px] text-slate-400">Failed</span>
                    <p className="font-bold text-red-400">{activeCrawlJob.total_pages_failed}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sub Tabs: Crawled Pages vs Clean Documents */}
          <div className="flex border-b border-slate-800 space-x-4 text-xs font-semibold">
            <button
              onClick={() => setCrawlerSubTab("pages")}
              className={`pb-2.5 border-b-2 transition ${
                crawlerSubTab === "pages"
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Crawled Pages ({crawlPages.length})
            </button>
            <button
              onClick={() => setCrawlerSubTab("documents")}
              className={`pb-2.5 border-b-2 transition ${
                crawlerSubTab === "documents"
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              Extracted Knowledge Documents ({documents.length})
            </button>
          </div>

          {/* Sub Tab View 1: Pages Table */}
          {crawlerSubTab === "pages" && (
            <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50">
              {crawlPages.length === 0 ? (
                <div className="p-12 text-center text-xs text-slate-500">
                  No crawl pages recorded yet. Click &quot;Start New Crawl&quot; to begin indexing this website.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-slate-800/80 bg-slate-950/40 text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                      <tr>
                        <th className="px-6 py-3.5">Page Title & URL</th>
                        <th className="px-6 py-3.5">Status</th>
                        <th className="px-6 py-3.5">HTTP Code</th>
                        <th className="px-6 py-3.5">Discovered Via</th>
                        <th className="px-6 py-3.5">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {crawlPages.map((page) => (
                        <tr key={page.id} className="hover:bg-slate-800/30 transition">
                          <td className="px-6 py-3.5 max-w-md">
                            <p className="font-semibold text-white truncate">{page.page_title || "Untitled"}</p>
                            <a
                              href={page.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[11px] text-slate-400 hover:text-indigo-400 truncate block font-mono"
                            >
                              {page.url}
                            </a>
                            {page.error && <p className="text-[10px] text-red-400 mt-0.5">{page.error}</p>}
                          </td>
                          <td className="px-6 py-3.5">
                            <span
                              className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                                page.status === "CRAWLED"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : page.status === "FAILED"
                                  ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                  : "bg-slate-800 text-slate-400"
                              }`}
                            >
                              {page.status}
                            </span>
                          </td>
                          <td className="px-6 py-3.5 font-mono text-[11px]">
                            {page.status_code ? (
                              <span className={page.status_code < 400 ? "text-emerald-400" : "text-red-400"}>
                                {page.status_code}
                              </span>
                            ) : (
                              "-"
                            )}
                          </td>
                          <td className="px-6 py-3.5 text-slate-400 text-[11px] font-mono">
                            {page.discovered_via} (depth {page.depth})
                          </td>
                          <td className="px-6 py-3.5 text-slate-500 text-[11px] font-mono">
                            {new Date(page.created_at).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Sub Tab View 2: Knowledge Documents */}
          {crawlerSubTab === "documents" && (
            <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50">
              {documents.length === 0 ? (
                <div className="p-12 text-center text-xs text-slate-500">
                  No knowledge documents created yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-slate-800/80 bg-slate-950/40 text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                      <tr>
                        <th className="px-6 py-3.5">Document Title & URL</th>
                        <th className="px-6 py-3.5">Est. Tokens</th>
                        <th className="px-6 py-3.5">Status</th>
                        <th className="px-6 py-3.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-slate-800/30 transition">
                          <td className="px-6 py-3.5 max-w-md">
                            <p className="font-semibold text-white truncate">{doc.title}</p>
                            <span className="text-[11px] text-slate-400 truncate block font-mono">{doc.url}</span>
                          </td>
                          <td className="px-6 py-3.5 font-mono text-[11px] text-slate-300">
                            ~{doc.token_count} tokens
                          </td>
                          <td className="px-6 py-3.5">
                            <span className="rounded bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[10px] font-semibold text-indigo-400">
                              {doc.status}
                            </span>
                          </td>
                          <td className="px-6 py-3.5 text-right">
                            <button
                              onClick={() => setPreviewDoc(doc)}
                              className="inline-flex items-center gap-1 rounded-lg bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition"
                            >
                              <Eye className="h-3.5 w-3.5" />
                              <span>View Content</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Appearance */}
      {activeTab === "appearance" && (
        <form onSubmit={handleSaveAppearance} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-sm font-bold text-white">Chatbot Branding & Content</h3>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Chatbot Assistant Name
              </label>
              <input
                type="text"
                required
                disabled={!canManage}
                value={chatbotName}
                onChange={(e) => setChatbotName(e.target.value)}
                placeholder="e.g. Store Concierge"
                className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Welcome Greeting Message
              </label>
              <textarea
                rows={2}
                disabled={!canManage}
                value={welcomeMessage}
                onChange={(e) => setWelcomeMessage(e.target.value)}
                placeholder="Hi there! How can I help you today?"
                className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Input Placeholder Text
              </label>
              <input
                type="text"
                disabled={!canManage}
                value={placeholderText}
                onChange={(e) => setPlaceholderText(e.target.value)}
                placeholder="Ask about products, orders, or support..."
                className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Primary Theme Color
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    disabled={!canManage}
                    value={primaryColor}
                    onChange={(e) => setPrimaryColor(e.target.value)}
                    className="h-9 w-9 cursor-pointer rounded-lg border border-slate-800 bg-transparent p-0.5"
                  />
                  <input
                    type="text"
                    disabled={!canManage}
                    value={primaryColor}
                    onChange={(e) => setPrimaryColor(e.target.value)}
                    className="flex-1 rounded-xl border border-slate-800 bg-slate-950 py-2 px-3 text-xs font-mono text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Launcher Position
                </label>
                <select
                  disabled={!canManage}
                  value={launcherPosition}
                  onChange={(e) => setLauncherPosition(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3 text-xs text-white"
                >
                  <option value="bottom-right">Bottom Right</option>
                  <option value="bottom-left">Bottom Left</option>
                </select>
              </div>
            </div>

            <div className="border-t border-slate-800/80 pt-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-white">WhatsApp Escalation Handoff</h4>
                  <p className="text-[11px] text-slate-400">Offer direct human handoff via WhatsApp</p>
                </div>
                <input
                  type="checkbox"
                  disabled={!canManage}
                  checked={enableWhatsapp}
                  onChange={(e) => setEnableWhatsapp(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
                />
              </div>

              {enableWhatsapp && (
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                    WhatsApp Phone Number (with country code)
                  </label>
                  <input
                    type="text"
                    disabled={!canManage}
                    value={whatsappNumber}
                    onChange={(e) => setWhatsappNumber(e.target.value)}
                    placeholder="+15551234567"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2 px-3 text-xs font-mono text-white"
                  />
                </div>
              )}
            </div>

            {canManage && (
              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isSavingSettings}
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  <span>{isSavingSettings ? "Saving..." : "Save Appearance"}</span>
                </button>
              </div>
            )}
          </div>

          {/* Interactive Live Preview */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 flex flex-col items-center justify-between min-h-[420px]">
            <div className="w-full text-center border-b border-slate-800/80 pb-3">
              <span className="text-[11px] uppercase font-bold tracking-wider text-slate-400">
                Live Widget Preview
              </span>
            </div>

            {/* Mock Chat Box */}
            <div className="w-full max-w-xs rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl overflow-hidden my-4">
              <div
                className="p-3.5 text-white flex items-center gap-2"
                style={{ backgroundColor: primaryColor }}
              >
                <div className="h-6 w-6 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold">
                  AI
                </div>
                <div className="truncate">
                  <p className="text-xs font-bold leading-tight">{chatbotName || "Assistant"}</p>
                  <p className="text-[9px] opacity-80">Online & Ready</p>
                </div>
              </div>

              <div className="p-3 space-y-2.5 bg-slate-900/90 text-xs min-h-[140px]">
                <div className="rounded-xl bg-slate-800 p-2.5 text-slate-200 text-[11px] shadow-sm max-w-[85%]">
                  {welcomeMessage || "Hello! How can I assist you?"}
                </div>
              </div>

              <div className="p-2 border-t border-slate-800 bg-slate-950 flex items-center gap-2">
                <input
                  type="text"
                  disabled
                  placeholder={placeholderText || "Type message..."}
                  className="w-full bg-slate-900 text-[11px] rounded-lg px-2.5 py-1.5 text-slate-400 border border-slate-800"
                />
                <button
                  disabled
                  className="p-1.5 rounded-lg text-white text-xs font-bold"
                  style={{ backgroundColor: primaryColor }}
                >
                  ➤
                </button>
              </div>
            </div>

            <div className="text-[10px] text-slate-500 text-center">
              Launcher Position: <span className="font-mono text-slate-400">{launcherPosition}</span>
            </div>
          </div>
        </form>
      )}

      {/* Tab: WhatsApp Bridge */}
      {activeTab === "whatsapp" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* WhatsApp Settings Form */}
          <form onSubmit={handleSaveWhatsapp} className="lg:col-span-7 space-y-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 border border-emerald-500/30 text-emerald-400">
                    <Phone className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">WhatsApp Human Handoff Bridge</h3>
                    <p className="text-[11px] text-slate-400">
                      Seamlessly transfer website visitors from automated AI bot to human support staff on WhatsApp.
                    </p>
                  </div>
                </div>

                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    disabled={!canManage}
                    checked={enableWhatsapp}
                    onChange={(e) => setEnableWhatsapp(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                </label>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  WhatsApp Support Phone Number
                </label>
                <input
                  type="text"
                  disabled={!canManage}
                  value={whatsappNumber}
                  onChange={(e) => setWhatsappNumber(e.target.value)}
                  placeholder="+1 (555) 123-4567 or +92 300 1234567"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs font-mono text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Include country code (e.g. +1 for US/Canada, +44 for UK). Spaces, hyphens, and parentheses will be automatically sanitized.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Handoff Button Visibility &amp; Trigger
                </label>
                <select
                  disabled={!canManage}
                  value={whatsappHandoffTrigger}
                  onChange={(e) => setWhatsappHandoffTrigger(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3 text-xs text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="ON_ESCALATION">On Escalation Only (When customer requests human or low AI confidence)</option>
                  <option value="ALWAYS_VISIBLE">Always Visible (Persistent WhatsApp action icon in widget header + on escalation)</option>
                  <option value="DISABLED">Disabled</option>
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Pre-filled Message Template
                  </label>
                  <span className="text-[10px] text-slate-500 font-mono">Template tags supported</span>
                </div>
                <textarea
                  rows={3}
                  disabled={!canManage}
                  value={whatsappCustomMessage}
                  onChange={(e) => setWhatsappCustomMessage(e.target.value)}
                  placeholder="Hello {store_name}, I was chatting with your AI assistant (Visitor: {visitor_id}) regarding: &quot;{last_inquiry}&quot;. Could a human support agent please assist me?"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white placeholder-slate-600 focus:border-emerald-500 focus:outline-none leading-relaxed"
                />

                {/* Variable insertion tags */}
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] text-slate-500 font-semibold mr-1">Insert Variable:</span>
                  {[
                    { tag: "{store_name}", label: "Store Name" },
                    { tag: "{visitor_id}", label: "Visitor ID" },
                    { tag: "{last_inquiry}", label: "Last Question" },
                    { tag: "{session_id}", label: "Session Code" },
                  ].map((v) => (
                    <button
                      key={v.tag}
                      type="button"
                      onClick={() => setWhatsappCustomMessage((prev) => prev + " " + v.tag)}
                      className="rounded-lg border border-slate-800 bg-slate-950 px-2 py-0.5 text-[10px] font-mono text-emerald-400 hover:bg-slate-800 transition"
                    >
                      {v.tag}
                    </button>
                  ))}
                </div>
              </div>

              {canManage && (
                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={isSavingWhatsapp}
                    className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-emerald-600/30 hover:bg-emerald-500 disabled:opacity-50 transition"
                  >
                    <Save className="h-4 w-4" />
                    <span>{isSavingWhatsapp ? "Saving..." : "Save WhatsApp Settings"}</span>
                  </button>
                </div>
              )}
            </div>
          </form>

          {/* Interactive Live Simulator */}
          <div className="lg:col-span-5 space-y-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h4 className="text-xs font-bold text-white flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-emerald-400" />
                  <span>Live WhatsApp Link Simulator</span>
                </h4>
                <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-mono text-emerald-400">
                  Real-time Preview
                </span>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                  Simulated Customer Inquiry
                </label>
                <input
                  type="text"
                  value={sampleInquiry}
                  onChange={(e) => setSampleInquiry(e.target.value)}
                  placeholder="Type a sample customer question..."
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2 px-3 text-xs text-white"
                />
              </div>

              {/* Formatted Message Bubble Preview */}
              <div className="space-y-1.5">
                <label className="block text-[11px] font-semibold text-slate-400">
                  Pre-filled WhatsApp Message
                </label>
                <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-3.5 text-xs text-emerald-100 font-sans leading-relaxed">
                  {(whatsappCustomMessage.trim() ||
                    "Hello {store_name}, I was chatting with your AI assistant (Visitor: {visitor_id}) regarding: \"{last_inquiry}\". Could a human support agent please assist me?")
                    .replace("{store_name}", website?.name || "Store")
                    .replace("{website_name}", website?.name || "Store")
                    .replace("{visitor_id}", "vis_customer_901")
                    .replace("{session_id}", "89a1c4")
                    .replace("{last_inquiry}", sampleInquiry)}
                </div>
              </div>

              {/* Direct Link & Action Button */}
              {whatsappNumber ? (
                <div className="pt-2">
                  <a
                    href={`https://wa.me/${whatsappNumber.replace(/\D/g, "")}?text=${encodeURIComponent(
                      (whatsappCustomMessage.trim() ||
                        "Hello {store_name}, I was chatting with your AI assistant (Visitor: {visitor_id}) regarding: \"{last_inquiry}\". Could a human support agent please assist me?")
                        .replace("{store_name}", website?.name || "Store")
                        .replace("{website_name}", website?.name || "Store")
                        .replace("{visitor_id}", "vis_customer_901")
                        .replace("{session_id}", "89a1c4")
                        .replace("{last_inquiry}", sampleInquiry)
                    )}`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-600 py-3 px-4 text-xs font-bold text-white shadow-lg shadow-emerald-600/30 hover:bg-emerald-500 transition"
                  >
                    <Phone className="h-4 w-4" />
                    <span>Test Click-to-Chat on WhatsApp</span>
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </a>
                </div>
              ) : (
                <div className="rounded-xl bg-slate-950 p-3 text-center text-[11px] text-slate-500">
                  Enter a phone number on the left to test the live click-to-chat deep link.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Installation */}
      {activeTab === "installation" && (
        <div className="space-y-6 max-w-4xl">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white">JavaScript Widget Embed Code</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Add this single script tag right before the closing <code className="text-indigo-400">&lt;/body&gt;</code> tag on your website.
                </p>
              </div>

              <a
                href={`/widget-demo.html?site_id=${website?.public_site_id}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 rounded-xl bg-indigo-600/20 border border-indigo-500/30 px-3 py-1.5 text-xs font-semibold text-indigo-300 hover:bg-indigo-600/30 transition"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                <span>Open Demo Store</span>
              </a>
            </div>

            <div className="mt-4 relative rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-indigo-300">
              <pre className="overflow-x-auto">{widgetScriptTag}</pre>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(widgetScriptTag);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/30 px-2.5 py-1 text-[11px] font-semibold text-indigo-300 hover:bg-indigo-600/30 transition"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                <span>{copied ? "Copied" : "Copy Code"}</span>
              </button>
            </div>
          </div>

          {/* WordPress Plugin Download Card */}
          <div className="rounded-2xl border border-purple-500/30 bg-purple-950/20 p-6 backdrop-blur-sm shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-600/30 border border-purple-500/40 text-purple-300 font-bold text-sm">
                  WP
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span>Official WordPress &amp; WooCommerce Plugin</span>
                    <span className="rounded-full bg-purple-500/20 border border-purple-500/30 px-2 py-0.5 text-[10px] font-bold text-purple-300">
                      Pre-Configured .zip
                    </span>
                  </h3>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Download ready-to-install plugin with your Public Site ID (<code className="font-mono text-purple-300">{website.public_site_id}</code>) pre-configured.
                  </p>
                </div>
              </div>

              <a
                href={`http://localhost:8000/api/v1/websites/${website.id}/download-plugin?org_id=${currentOrg?.id}`}
                download
                className="flex items-center justify-center gap-2 rounded-xl bg-purple-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-purple-600/30 hover:bg-purple-500 transition shrink-0"
              >
                <Code2 className="h-4 w-4" />
                <span>Download Plugin (.zip)</span>
              </a>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="space-y-1">
                <span className="font-bold text-purple-400 font-mono text-[11px]">Step 1: Download</span>
                <p className="text-slate-400 text-[11px]">Click the download button above to get the pre-configured plugin zip.</p>
              </div>
              <div className="space-y-1">
                <span className="font-bold text-purple-400 font-mono text-[11px]">Step 2: Upload in WP</span>
                <p className="text-slate-400 text-[11px]">In WordPress Admin, go to <strong>Plugins ➔ Add New ➔ Upload Plugin</strong>.</p>
              </div>
              <div className="space-y-1">
                <span className="font-bold text-purple-400 font-mono text-[11px]">Step 3: Activate</span>
                <p className="text-slate-400 text-[11px]">Click <strong>Activate Plugin</strong> — your AI assistant immediately goes live!</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-5">
              <h4 className="text-xs font-bold text-white flex items-center gap-2">
                <span>Manual Script Injection</span>
              </h4>
              <p className="text-[11px] text-slate-400 mt-1">
                Install via WP Header &amp; Footer Scripts plugin, or add the snippet into your active theme&apos;s <code className="text-slate-300 font-mono">footer.php</code>.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-5">
              <h4 className="text-xs font-bold text-white flex items-center gap-2">
                <span>Shopify / Next.js / Custom</span>
              </h4>
              <p className="text-[11px] text-slate-400 mt-1">
                In Shopify, paste into <code className="text-slate-300 font-mono">theme.liquid</code> before &lt;/body&gt;. In Next.js, use the <code className="text-slate-300 font-mono">next/script</code> component with <code className="text-slate-300 font-mono">strategy=&quot;lazyOnload&quot;</code>.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Settings */}
      {activeTab === "settings" && (
        <div className="space-y-6 max-w-3xl">
          <form onSubmit={handleSaveBasic} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4">
            <h3 className="text-sm font-bold text-white">General Website Settings</h3>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Website Name
              </label>
              <input
                type="text"
                required
                disabled={!canManage}
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Website URL
              </label>
              <input
                type="text"
                required
                disabled={!canManage}
                value={editUrl}
                onChange={(e) => setEditUrl(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Website Status
              </label>
              <select
                disabled={!canManage}
                value={editStatus}
                onChange={(e: any) => setEditStatus(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3 text-xs text-white"
              >
                <option value="ACTIVE">ACTIVE (Widget Online)</option>
                <option value="INACTIVE">INACTIVE (Widget Disabled)</option>
              </select>
            </div>

            {canManage && (
              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isSavingBasic}
                  className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  <span>{isSavingBasic ? "Saving..." : "Save Settings"}</span>
                </button>
              </div>
            )}
          </form>

          {/* Danger Zone */}
          {canManage && (
            <div className="rounded-2xl border border-red-500/20 bg-red-950/10 p-6">
              <h3 className="text-sm font-bold text-red-400">Danger Zone</h3>
              <p className="text-xs text-slate-400 mt-1">
                Permanently delete this website and all associated appearance settings and public configurations.
              </p>
              <div className="mt-4 flex justify-end">
                <button
                  onClick={handleDeleteWebsite}
                  className="flex items-center gap-2 rounded-xl bg-red-600/20 border border-red-500/30 px-4 py-2 text-xs font-semibold text-red-300 hover:bg-red-600/30 transition"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Delete Website</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Start Crawl Modal */}
      {isStartModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
              <h3 className="text-base font-bold text-white">Start Web Crawl for {website.name}</h3>
              <button onClick={() => setIsStartModalOpen(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Maximum Pages to Crawl
                </label>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={maxPagesLimit}
                  onChange={(e) => setMaxPagesLimit(parseInt(e.target.value) || 50)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3 text-xs text-white"
                />
                <p className="mt-1 text-[11px] text-slate-500">
                  Target Domain: <span className="font-mono text-indigo-300">{website.domain}</span>
                </p>
              </div>

              <div className="rounded-xl bg-slate-950 p-3 border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <p className="font-semibold text-slate-300">Crawler Protocol Pipeline:</p>
                <ul className="list-disc list-inside space-y-0.5 text-[10px]">
                  <li>Checks SSRF security boundaries & DNS resolution.</li>
                  <li>Fetches & parses /robots.txt rules.</li>
                  <li>Discovers sitemaps & recursive index sitemaps.</li>
                  <li>Cleans HTML noise & stores documents for AI indexing.</li>
                </ul>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsStartModalOpen(false)}
                  className="rounded-xl border border-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleStartCrawl}
                  disabled={isStartingCrawl}
                  className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                >
                  {isStartingCrawl ? "Starting..." : "Start Crawling"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Document Content Viewer Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
              <div>
                <h3 className="text-base font-bold text-white truncate max-w-xl">{previewDoc.title}</h3>
                <p className="text-[11px] font-mono text-slate-400 truncate max-w-xl">{previewDoc.url}</p>
              </div>
              <button onClick={() => setPreviewDoc(null)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto rounded-xl bg-slate-950 p-4 border border-slate-800 text-xs text-slate-300 whitespace-pre-wrap font-sans">
              {previewDoc.raw_content}
            </div>

            <div className="flex items-center justify-between border-t border-slate-800 pt-4 mt-4 text-[11px] text-slate-500 font-mono">
              <span>SHA-256: {previewDoc.content_hash.substring(0, 16)}...</span>
              <span>~{previewDoc.token_count} Tokens</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
