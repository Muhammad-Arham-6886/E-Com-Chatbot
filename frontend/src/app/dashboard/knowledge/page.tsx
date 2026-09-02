"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  BookOpen,
  Globe,
  FileText,
  Search,
  Eye,
  ExternalLink,
  Layers,
  Sparkles,
  Cpu,
  Play,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sliders,
  Zap,
} from "lucide-react";

interface Website {
  id: string;
  name: string;
  domain: string;
}

interface KnowledgeDocument {
  id: string;
  website_id: string;
  organization_id: string;
  url: string;
  title: string;
  meta_description?: string | null;
  raw_content: string;
  content_hash: string;
  token_count: number;
  status: string;
  created_at: string;
}

interface SearchResultItem {
  chunk_id: string;
  document_id: string;
  website_id: string;
  url: string;
  title: string;
  content: string;
  similarity_score: number;
  chunk_index: number;
  token_count: number;
}

interface VectorStats {
  total_documents: number;
  total_chunks: number;
  total_tokens: number;
  embedded_documents_count: number;
}

export default function KnowledgeBasePage() {
  const { currentOrg } = useAuth();
  const [websites, setWebsites] = useState<Website[]>([]);
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string>("all");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [previewDoc, setPreviewDoc] = useState<KnowledgeDocument | null>(null);

  // Semantic Search Playground State
  const [playgroundQuery, setPlaygroundQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Vector Stats & Batch Embedding State
  const [stats, setStats] = useState<VectorStats | null>(null);
  const [isEmbeddingModalOpen, setIsEmbeddingModalOpen] = useState(false);
  const [embedWebsiteId, setEmbedWebsiteId] = useState<string>("");
  const [chunkSize, setChunkSize] = useState(800);
  const [chunkOverlap, setChunkOverlap] = useState(150);
  const [reEmbedAll, setReEmbedAll] = useState(false);
  const [isProcessingEmbeddings, setIsProcessingEmbeddings] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  const canManage = currentOrg?.role === "OWNER" || currentOrg?.role === "ADMIN";

  const fetchKnowledgeData = async () => {
    if (!currentOrg) return;
    setIsLoading(true);
    try {
      const [sites, vectorStats] = await Promise.all([
        apiRequest<Website[]>(`/websites?org_id=${currentOrg.id}`),
        apiRequest<VectorStats>(`/knowledge/stats?org_id=${currentOrg.id}`).catch(() => null),
      ]);
      setWebsites(sites);
      setStats(vectorStats);
      if (sites.length > 0 && !embedWebsiteId) {
        setEmbedWebsiteId(sites[0].id);
      }

      // Fetch documents across all websites
      const allDocs: KnowledgeDocument[] = [];
      for (const s of sites) {
        try {
          const docs = await apiRequest<KnowledgeDocument[]>(`/crawling/websites/${s.id}/documents?org_id=${currentOrg.id}`);
          allDocs.push(...docs);
        } catch (e) {
          // ignore
        }
      }
      setDocuments(allDocs);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKnowledgeData();
  }, [currentOrg]);

  const handleSemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !playgroundQuery.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const payload: any = {
        query: playgroundQuery.trim(),
        top_k: 5,
        min_similarity: 0.0,
      };
      if (selectedWebsiteId !== "all") {
        payload.website_id = selectedWebsiteId;
      }

      const res = await apiRequest<{ results: SearchResultItem[] }>(`/knowledge/search?org_id=${currentOrg.id}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSearchResults(res.results || []);
    } catch (err: any) {
      setSearchError(err.message || "Semantic search request failed");
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleProcessEmbeddings = async () => {
    if (!currentOrg || !embedWebsiteId) return;
    setIsProcessingEmbeddings(true);
    setFeedbackSuccess(null);
    setFeedbackError(null);

    try {
      const res = await apiRequest<any>(`/knowledge/websites/${embedWebsiteId}/process-embeddings?org_id=${currentOrg.id}`, {
        method: "POST",
        body: JSON.stringify({
          chunk_size: chunkSize,
          chunk_overlap: chunkOverlap,
          re_embed_all: reEmbedAll,
        }),
      });
      setFeedbackSuccess(
        `Successfully processed ${res.documents_processed} document(s), generated ${res.chunks_created} vector chunks (~${res.total_tokens} tokens)!`
      );
      setIsEmbeddingModalOpen(false);
      await fetchKnowledgeData();
    } catch (err: any) {
      setFeedbackError(err.message || "Failed to generate vector embeddings");
    } finally {
      setIsProcessingEmbeddings(false);
    }
  };

  const filteredDocs = documents.filter((doc) => {
    const matchesSite = selectedWebsiteId === "all" || doc.website_id === selectedWebsiteId;
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.raw_content.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSite && matchesSearch;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Organization Knowledge Base & Vector Index</h1>
          <p className="text-xs text-slate-400 mt-1">
            Clean documents indexed from your crawled websites, converted into semantic chunks with 768-d vector embeddings.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchKnowledgeData}
            className="rounded-xl border border-slate-800 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          {canManage && (
            <button
              onClick={() => setIsEmbeddingModalOpen(true)}
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 transition"
            >
              <Zap className="h-3.5 w-3.5" />
              <span>Process Vector Embeddings</span>
            </button>
          )}
        </div>
      </div>

      {/* Alerts */}
      {feedbackSuccess && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-xs text-emerald-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{feedbackSuccess}</span>
        </div>
      )}
      {feedbackError && (
        <div className="flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{feedbackError}</span>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Indexed Documents</span>
          <p className="mt-2 text-2xl font-bold text-white">{stats ? stats.total_documents : documents.length}</p>
          <p className="text-[11px] text-slate-500 mt-1">Raw HTML pages sanitized</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Vector Chunks</span>
          <p className="mt-2 text-2xl font-bold text-indigo-400 font-mono">{stats ? stats.total_chunks : 0}</p>
          <p className="text-[11px] text-slate-500 mt-1">Semantic sliding-window chunks</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Indexed Tokens</span>
          <p className="mt-2 text-2xl font-bold text-emerald-400 font-mono">
            ~{stats ? stats.total_tokens.toLocaleString() : 0}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">768-d nomic-embed-text vectors</p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Embedding Engine</span>
          <p className="mt-2 text-2xl font-bold text-slate-200 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-indigo-400" />
            <span>Local Ollama</span>
          </p>
          <p className="text-[11px] text-slate-500 mt-1">pgvector HNSW cosine index</p>
        </div>
      </div>

      {/* Semantic Search Playground */}
      <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/20 p-6 backdrop-blur-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              <span>Semantic Vector Search Playground</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Test natural language retrieval queries across your vector chunks in real-time.
            </p>
          </div>
          <span className="rounded-full bg-indigo-500/20 px-2.5 py-0.5 text-[10px] font-bold text-indigo-300">
            RAG Foundation
          </span>
        </div>

        <form onSubmit={handleSemanticSearch} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={playgroundQuery}
              onChange={(e) => setPlaygroundQuery(e.target.value)}
              placeholder="e.g. What is the return and refund policy? How do I track my order?"
              className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={isSearching || !playgroundQuery.trim()}
            className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50 transition whitespace-nowrap"
          >
            <Play className="h-3.5 w-3.5" />
            <span>{isSearching ? "Searching Vectors..." : "Run Search"}</span>
          </button>
        </form>

        {/* Search Results */}
        {searchError && <p className="text-xs text-red-400">{searchError}</p>}

        {hasSearched && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between text-xs text-slate-400 font-semibold border-t border-slate-800/80 pt-3">
              <span>Search Results ({searchResults.length} matched chunks)</span>
              <span>Query: &quot;{playgroundQuery}&quot;</span>
            </div>

            {searchResults.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">
                No vector matches found. Make sure you have crawled pages and processed vector embeddings.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {searchResults.map((item, idx) => (
                  <div
                    key={item.chunk_id}
                    className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 truncate">
                        <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[10px] font-bold text-indigo-300">
                          #{idx + 1}
                        </span>
                        <h4 className="text-xs font-bold text-white truncate">{item.title}</h4>
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[10px] text-slate-400 hover:text-indigo-400 truncate font-mono"
                        >
                          {item.url}
                        </a>
                      </div>

                      <span
                        className={`rounded-lg px-2 py-0.5 text-[10px] font-mono font-bold ${
                          item.similarity_score >= 0.7
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : item.similarity_score >= 0.4
                            ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {Math.round(item.similarity_score * 100)}% Match
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 whitespace-pre-wrap font-sans bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                      {item.content}
                    </p>

                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>Chunk #{item.chunk_index}</span>
                      <span>~{item.token_count} Tokens</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filter and Search Bar for Raw Documents */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search indexed documents by title, URL or keywords..."
            className="w-full rounded-xl border border-slate-800 bg-slate-900 py-2.5 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <select
          value={selectedWebsiteId}
          onChange={(e) => setSelectedWebsiteId(e.target.value)}
          className="rounded-xl border border-slate-800 bg-slate-900 py-2.5 px-3 text-xs text-white focus:border-indigo-500 focus:outline-none w-full sm:w-auto"
        >
          <option value="all">All Websites ({websites.length})</option>
          {websites.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} ({s.domain})
            </option>
          ))}
        </select>
      </div>

      {/* Documents Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50">
        {isLoading ? (
          <div className="p-16 text-center text-xs text-slate-500">Loading knowledge base...</div>
        ) : filteredDocs.length === 0 ? (
          <div className="p-16 text-center text-xs text-slate-500 space-y-3">
            <BookOpen className="h-8 w-8 text-slate-600 mx-auto" />
            <p>No documents found matching your search or website filter.</p>
            <p className="text-[11px] text-slate-600">
              Run a crawl on your connected websites to index documents automatically.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800/80 bg-slate-950/40 text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                <tr>
                  <th className="px-6 py-3.5">Document Title & URL</th>
                  <th className="px-6 py-3.5">Website</th>
                  <th className="px-6 py-3.5">Est. Tokens</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filteredDocs.map((doc) => {
                  const site = websites.find((w) => w.id === doc.website_id);
                  return (
                    <tr key={doc.id} className="hover:bg-slate-800/30 transition">
                      <td className="px-6 py-3.5 max-w-md">
                        <p className="font-semibold text-white truncate">{doc.title}</p>
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-slate-400 hover:text-indigo-400 truncate block font-mono"
                        >
                          {doc.url}
                        </a>
                      </td>
                      <td className="px-6 py-3.5 text-slate-300">{site ? site.name : "Website"}</td>
                      <td className="px-6 py-3.5 font-mono text-[11px] text-slate-300">~{doc.token_count}</td>
                      <td className="px-6 py-3.5">
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-semibold ${
                            doc.status === "PROCESSED"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                          }`}
                        >
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
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Process Embeddings Modal */}
      {isEmbeddingModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Zap className="h-4 w-4 text-indigo-400" />
                <span>Process Vector Embeddings</span>
              </h3>
              <button onClick={() => setIsEmbeddingModalOpen(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Target Website
                </label>
                <select
                  value={embedWebsiteId}
                  onChange={(e) => setEmbedWebsiteId(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3 text-white"
                >
                  {websites.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name} ({w.domain})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-400 mb-1">Chunk Size (chars)</label>
                  <input
                    type="number"
                    min={100}
                    max={4000}
                    value={chunkSize}
                    onChange={(e) => setChunkSize(parseInt(e.target.value) || 800)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2 px-3 text-white"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-400 mb-1">Overlap (chars)</label>
                  <input
                    type="number"
                    min={0}
                    max={1000}
                    value={chunkOverlap}
                    onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 150)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2 px-3 text-white"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="reembed"
                  checked={reEmbedAll}
                  onChange={(e) => setReEmbedAll(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-indigo-600"
                />
                <label htmlFor="reembed" className="text-slate-300">
                  Re-chunk and re-embed all documents (overwrite existing)
                </label>
              </div>

              <div className="rounded-xl bg-slate-950 p-3 border border-slate-800 text-[11px] text-slate-400">
                <p className="font-semibold text-slate-300 mb-1">RAG Pipeline Actions:</p>
                <ul className="list-disc list-inside space-y-0.5 text-[10px]">
                  <li>Cleans and normalizes markdown/text bodies.</li>
                  <li>Generates sliding-window semantic chunks.</li>
                  <li>Computes 768-d embeddings using nomic-embed-text.</li>
                  <li>Stores in pgvector with HNSW cosine similarity index.</li>
                </ul>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEmbeddingModalOpen(false)}
                  className="rounded-xl border border-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleProcessEmbeddings}
                  disabled={isProcessingEmbeddings}
                  className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                >
                  {isProcessingEmbeddings ? "Generating Vectors..." : "Start Vector Processing"}
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
              <span>SHA-256: {previewDoc.content_hash}</span>
              <span>~{previewDoc.token_count} Tokens</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
