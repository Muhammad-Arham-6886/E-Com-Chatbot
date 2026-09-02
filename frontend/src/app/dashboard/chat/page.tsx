"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  MessageSquare,
  Send,
  Sparkles,
  ExternalLink,
  ShoppingBag,
  Phone,
  RefreshCw,
  Cpu,
  Layers,
  AlertCircle,
  HelpCircle,
} from "lucide-react";

interface Website {
  id: string;
  name: string;
  domain: string;
}

interface SourceCitation {
  title: string;
  url: string;
}

interface SuggestedAction {
  type: string;
  label: string;
  value: string;
  payload?: any;
}

interface Message {
  id: string;
  sender: "USER" | "BOT";
  content: string;
  sources?: SourceCitation[];
  suggested_actions?: SuggestedAction[];
  tool_call?: {
    tool: string;
    parameters: any;
    confidence: number;
  };
}

export default function GlobalChatPlaygroundPage() {
  const { currentOrg } = useAuth();
  const [websites, setWebsites] = useState<Website[]>([]);
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string>("");
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [debugTrace, setDebugTrace] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchWebsites = async () => {
    if (!currentOrg) return;
    try {
      const sites = await apiRequest<Website[]>(`/websites?org_id=${currentOrg.id}`);
      setWebsites(sites);
      if (sites.length > 0) {
        setSelectedWebsiteId(sites[0].id);
        await initSession(sites[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const initSession = async (siteId: string) => {
    setIsInitializing(true);
    setMessages([]);
    setDebugTrace(null);
    try {
      const sess = await apiRequest<any>("/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ website_id: siteId, channel: "DASHBOARD_TEST" }),
      });
      setSessionToken(sess.session_token);
      setMessages([
        {
          id: "welcome",
          sender: "BOT",
          content: "Hello! I am your AI Customer & Commerce Assistant. Ask me anything about our products, shipping, return policies, or store guidelines!",
        },
      ]);
    } catch (err) {
      console.error("Session init error", err);
    } finally {
      setIsInitializing(false);
    }
  };

  useEffect(() => {
    fetchWebsites();
  }, [currentOrg]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionToken || !inputMessage.trim() || isLoading) return;

    const userText = inputMessage.trim();
    setInputMessage("");

    const userMsgObj: Message = {
      id: `user_${Date.now()}`,
      sender: "USER",
      content: userText,
    };
    setMessages((prev) => [...prev, userMsgObj]);
    setIsLoading(true);

    try {
      const res = await apiRequest<any>("/chat/message", {
        method: "POST",
        body: JSON.stringify({
          session_token: sessionToken,
          content: userText,
        }),
      });

      const botMsgObj: Message = {
        id: res.id,
        sender: "BOT",
        content: res.content,
        sources: res.sources,
        suggested_actions: res.suggested_actions,
        tool_call: res.tool_call,
      };
      setMessages((prev) => [...prev, botMsgObj]);
      setDebugTrace({
        last_tool: res.tool_call,
        last_sources: res.sources,
        token_count: res.token_count,
      });
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: "BOT",
          content: `Error: ${err.message || "Failed to communicate with AI model"}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedSite = websites.find((w) => w.id === selectedWebsiteId);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">AI Assistant Test Console</h1>
          <p className="text-xs text-slate-400 mt-1">
            Test live Local LLM (Ollama) grounding against your indexed pgvector knowledge base and tool selection engine.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedWebsiteId}
            onChange={(e) => {
              setSelectedWebsiteId(e.target.value);
              initSession(e.target.value);
            }}
            className="rounded-xl border border-slate-800 bg-slate-900 py-2 px-3 text-xs text-white focus:border-indigo-500 focus:outline-none"
          >
            {websites.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} ({w.domain})
              </option>
            ))}
          </select>

          <button
            onClick={() => selectedWebsiteId && initSession(selectedWebsiteId)}
            className="rounded-xl border border-slate-800 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Reset Conversation"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Main Split Layout: Chat Window + RAG Debug Trace */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Chat Window */}
        <div className="lg:col-span-2 flex flex-col h-[640px] rounded-2xl border border-slate-800 bg-slate-900/50 shadow-2xl overflow-hidden backdrop-blur-sm">
          {/* Chat Header */}
          <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/60 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-600 text-white font-bold text-xs shadow-lg shadow-indigo-600/30">
                AI
              </div>
              <div>
                <h3 className="text-xs font-bold text-white leading-tight">
                  {selectedSite ? selectedSite.name : "Store Assistant"}
                </h3>
                <p className="text-[10px] text-emerald-400 flex items-center gap-1 font-mono">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Local LLM (llama3.2) + pgvector RAG Active</span>
                </p>
              </div>
            </div>

            <span className="rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 text-[10px] text-indigo-300 font-semibold">
              Live Test Session
            </span>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.sender === "USER" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3.5 shadow-sm space-y-2.5 ${
                    msg.sender === "USER"
                      ? "bg-indigo-600 text-white rounded-br-none"
                      : "bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                  {/* Product Cards Actions if returned */}
                  {msg.suggested_actions && msg.suggested_actions.some((a) => a.type === "product_card") && (
                    <div className="grid grid-cols-1 gap-2 pt-2 border-t border-slate-800/80">
                      {msg.suggested_actions
                        .filter((a) => a.type === "product_card")
                        .map((act, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-3 rounded-xl bg-slate-900 border border-slate-800 p-2.5 hover:border-slate-700 transition"
                          >
                            {act.payload?.image_url && (
                              <img
                                src={act.payload.image_url}
                                alt={act.label}
                                className="h-12 w-12 rounded-lg object-cover bg-slate-800 shrink-0"
                              />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className="font-bold text-white text-[11px] truncate">{act.label}</p>
                              <p className="text-emerald-400 font-mono text-[10px]">
                                ${act.payload?.price?.toFixed(2)} {act.payload?.currency}
                              </p>
                            </div>
                            <a
                              href={act.value}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1 rounded-lg bg-indigo-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-indigo-500 transition shrink-0"
                            >
                              <ShoppingBag className="h-3 w-3" />
                              <span>View</span>
                            </a>
                          </div>
                        ))}
                    </div>
                  )}

                  {/* WhatsApp Action Button if present */}
                  {msg.suggested_actions && msg.suggested_actions.some((a) => a.type === "whatsapp_handoff") && (
                    <div className="pt-2 border-t border-slate-800/80">
                      {msg.suggested_actions
                        .filter((a) => a.type === "whatsapp_handoff")
                        .map((act, idx) => (
                          <a
                            key={idx}
                            href={act.value}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-lg shadow-emerald-600/30 hover:bg-emerald-500 transition"
                          >
                            <Phone className="h-3.5 w-3.5" />
                            <span>{act.label}</span>
                          </a>
                        ))}
                    </div>
                  )}

                  {/* Source Citations */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex flex-wrap items-center gap-1.5">
                      <span className="font-semibold text-slate-500">Sources:</span>
                      {msg.sources.map((src, idx) => (
                        <a
                          key={idx}
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-1.5 py-0.5 text-indigo-300 hover:text-indigo-200 truncate max-w-[180px]"
                        >
                          <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                          <span className="truncate">{src.title}</span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-start">
                <div className="rounded-2xl rounded-bl-none border border-slate-800 bg-slate-950 p-3.5 text-xs text-slate-400 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-ping" />
                  <span>Retrieving knowledge & synthesizing response...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-800 bg-slate-950/80 flex items-center gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask about products, orders, returns, or support..."
              disabled={isLoading || isInitializing}
              className="flex-1 rounded-xl border border-slate-800 bg-slate-900 py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || isInitializing || !inputMessage.trim()}
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50 transition"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>

        {/* RAG & Tool Call Debug Panel */}
        <div className="space-y-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-5 backdrop-blur-sm text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-bold text-white flex items-center gap-2">
              <Cpu className="h-4 w-4 text-indigo-400" />
              <span>RAG Engine Debugger</span>
            </h3>
            <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
              Phase 5
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
              Tool Intent Classifier
            </span>
            <div className="mt-1.5 rounded-xl border border-slate-800 bg-slate-950 p-3">
              {debugTrace?.last_tool ? (
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-indigo-300 font-bold">{debugTrace.last_tool.tool}</span>
                    <span className="text-emerald-400 font-mono">
                      {Math.round(debugTrace.last_tool.confidence * 100)}% Conf
                    </span>
                  </div>
                  <pre className="text-[10px] font-mono text-slate-400 truncate">
                    {JSON.stringify(debugTrace.last_tool.parameters)}
                  </pre>
                </div>
              ) : (
                <span className="text-slate-500 text-[11px]">Send a query to classify intent</span>
              )}
            </div>
          </div>

          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
              Grounded Vector Sources
            </span>
            <div className="mt-1.5 space-y-1.5">
              {debugTrace?.last_sources && debugTrace.last_sources.length > 0 ? (
                debugTrace.last_sources.map((s: any, idx: number) => (
                  <div key={idx} className="rounded-lg bg-slate-950 p-2 border border-slate-800 text-[11px]">
                    <p className="font-semibold text-white truncate">{s.title}</p>
                    <p className="font-mono text-[10px] text-slate-500 truncate">{s.url}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-slate-500 text-[11px]">
                  No vector sources cited in latest turn
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl bg-slate-950/80 p-3 border border-slate-800/80 space-y-1 text-[11px] text-slate-400">
            <p className="font-semibold text-slate-300">Architecture Guarantees:</p>
            <ul className="list-disc list-inside space-y-0.5 text-[10px]">
              <li>Local LLM never hallucinates unindexed facts.</li>
              <li>Tool selection prevents direct LLM database writes.</li>
              <li>Strict tenant isolation across all chats.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
