"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  MessageSquare,
  Search,
  Filter,
  User,
  Bot,
  UserCheck,
  Clock,
  Globe,
  Send,
  CheckCircle2,
  AlertCircle,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Shield,
  Layers,
  Sparkles,
  Phone,
} from "lucide-react";

interface Website {
  id: string;
  name: string;
  domain: string;
}

interface ConversationSummary {
  id: string;
  website_id: string;
  website_name: string;
  website_domain: string;
  visitor_id: string;
  status: string;
  channel: string;
  message_count: number;
  last_message_preview: string | null;
  last_message_sender: string | null;
  last_message_at: string;
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  created_at: string;
}

interface ChatMessage {
  id: string;
  session_id: string;
  sender: "USER" | "BOT" | "AGENT" | "SYSTEM";
  content: string;
  sources: Array<{ title: string; url: string }>;
  suggested_actions: Array<{ type: string; label: string; value: string; payload?: any }>;
  tool_call?: { tool: string; parameters: any; confidence: number };
  token_count: number;
  created_at: string;
}

interface ConversationDetail {
  session: {
    id: string;
    website_id: string;
    organization_id: string;
    visitor_id: string;
    session_token: string;
    channel: string;
    status: string;
    assigned_user_id: string | null;
    last_message_at: string;
    created_at: string;
  };
  website_name: string;
  website_domain: string;
  assigned_user_name: string | null;
  messages: ChatMessage[];
}

export default function AgentInboxPage() {
  const { currentOrg, user } = useAuth();
  const [websites, setWebsites] = useState<Website[]>([]);
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoadingList, setIsLoadingList] = useState(true);
  
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  
  const [agentMessage, setAgentMessage] = useState("");
  const [isSendingReply, setIsSendingReply] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch Websites
  const fetchWebsites = async () => {
    if (!currentOrg) return;
    try {
      const sites = await apiRequest<Website[]>(`/websites?org_id=${currentOrg.id}`);
      setWebsites(sites);
    } catch (err) {
      console.error(err);
    }
  };

  // Fetch Conversation List
  const fetchConversations = async () => {
    if (!currentOrg) return;
    setIsLoadingList(true);
    try {
      let url = `/conversations?org_id=${currentOrg.id}&limit=50`;
      if (selectedWebsiteId) url += `&website_id=${selectedWebsiteId}`;
      if (statusFilter !== "ALL") url += `&status=${statusFilter}`;
      if (searchQuery.trim()) url += `&search=${encodeURIComponent(searchQuery.trim())}`;

      const res = await apiRequest<{ items: ConversationSummary[]; total: number }>(url);
      setConversations(res.items);
      setTotalCount(res.total);

      // Auto-select first if none selected
      if (!activeSessionId && res.items.length > 0) {
        setActiveSessionId(res.items[0].id);
      }
    } catch (err) {
      console.error("Error fetching conversations:", err);
    } finally {
      setIsLoadingList(false);
    }
  };

  // Fetch Conversation Transcript Detail
  const fetchConversationDetail = async (sessionId: string) => {
    if (!currentOrg || !sessionId) return;
    setIsLoadingDetail(true);
    try {
      const detail = await apiRequest<ConversationDetail>(
        `/conversations/${sessionId}?org_id=${currentOrg.id}`
      );
      setActiveConversation(detail);
    } catch (err) {
      console.error("Error loading conversation detail:", err);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchWebsites();
  }, [currentOrg]);

  useEffect(() => {
    fetchConversations();
  }, [currentOrg, selectedWebsiteId, statusFilter]);

  useEffect(() => {
    if (activeSessionId) {
      fetchConversationDetail(activeSessionId);
    }
  }, [activeSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeConversation?.messages]);

  // Send Human Agent Message
  const handleSendAgentReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !activeSessionId || !agentMessage.trim() || isSendingReply) return;

    const replyText = agentMessage.trim();
    setAgentMessage("");
    setIsSendingReply(true);

    try {
      const newMsg = await apiRequest<ChatMessage>(
        `/conversations/${activeSessionId}/agent-reply?org_id=${currentOrg.id}`,
        {
          method: "POST",
          body: JSON.stringify({ content: replyText }),
        }
      );

      // Append to active thread
      if (activeConversation) {
        setActiveConversation({
          ...activeConversation,
          session: {
            ...activeConversation.session,
            status: "HUMAN_TAKEOVER",
            assigned_user_id: user?.id || null,
          },
          assigned_user_name: user?.full_name || "Agent",
          messages: [...activeConversation.messages, newMsg],
        });
      }

      // Update list preview
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeSessionId
            ? {
                ...c,
                status: "HUMAN_TAKEOVER",
                last_message_preview: replyText,
                last_message_sender: "AGENT",
                message_count: c.message_count + 1,
              }
            : c
        )
      );
    } catch (err) {
      console.error("Failed to send agent reply:", err);
    } finally {
      setIsSendingReply(false);
    }
  };

  // Change Conversation Status
  const handleUpdateStatus = async (newStatus: string) => {
    if (!currentOrg || !activeSessionId || isUpdatingStatus) return;
    setIsUpdatingStatus(true);
    try {
      const updatedSess = await apiRequest<any>(
        `/conversations/${activeSessionId}/status?org_id=${currentOrg.id}`,
        {
          method: "PUT",
          body: JSON.stringify({ status: newStatus }),
        }
      );

      if (activeConversation) {
        setActiveConversation({
          ...activeConversation,
          session: { ...activeConversation.session, status: newStatus },
        });
      }

      setConversations((prev) =>
        prev.map((c) => (c.id === activeSessionId ? { ...c, status: newStatus } : c))
      );
    } catch (err) {
      console.error("Failed to update status:", err);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "WAITING_HUMAN":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            Waiting Human
          </span>
        );
      case "HUMAN_TAKEOVER":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-[10px] font-bold text-purple-300">
            <UserCheck className="h-2.5 w-2.5" />
            Agent Takeover
          </span>
        );
      case "CLOSED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
            <CheckCircle2 className="h-2.5 w-2.5" />
            Closed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
            <Bot className="h-2.5 w-2.5" />
            Bot Active
          </span>
        );
    }
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto h-[calc(100vh-100px)] flex flex-col">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between shrink-0">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Agent Inbox & Live Conversations</h1>
          <p className="text-xs text-slate-400">
            Monitor real-time visitor sessions, review RAG tool executions, and step in with live human agent takeover.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedWebsiteId}
            onChange={(e) => setSelectedWebsiteId(e.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-900 py-1.5 px-3 text-xs text-white focus:border-indigo-500 focus:outline-none"
          >
            <option value="">All Websites</option>
            {websites.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              fetchConversations();
              if (activeSessionId) fetchConversationDetail(activeSessionId);
            }}
            className="rounded-xl border border-slate-800 p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Refresh Inbox"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Main Two-Pane Inbox */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0 overflow-hidden">
        {/* Left Pane: Conversation List */}
        <div className="lg:col-span-5 flex flex-col rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm overflow-hidden">
          {/* Filters & Search Header */}
          <div className="p-3 border-b border-slate-800 space-y-2.5 bg-slate-950/60">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search visitor ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && fetchConversations()}
                className="w-full rounded-xl border border-slate-800 bg-slate-900 py-2 pl-9 pr-3 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            {/* Status Filter Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto text-[11px] no-scrollbar">
              {[
                { id: "ALL", label: "All" },
                { id: "WAITING_HUMAN", label: "Escalated" },
                { id: "HUMAN_TAKEOVER", label: "Agent" },
                { id: "BOT_ACTIVE", label: "Bot" },
                { id: "CLOSED", label: "Closed" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setStatusFilter(tab.id)}
                  className={`rounded-lg px-2.5 py-1 font-semibold whitespace-nowrap transition ${
                    statusFilter === tab.id
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Conversation Cards List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60">
            {isLoadingList ? (
              <div className="flex h-48 items-center justify-center text-xs text-slate-500">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent mr-2" />
                <span>Loading conversations...</span>
              </div>
            ) : conversations.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 space-y-1">
                <MessageSquare className="h-8 w-8 mx-auto text-slate-600 opacity-40 mb-2" />
                <p className="font-semibold text-slate-400">No conversations found</p>
                <p className="text-[11px]">Chats initiated on your websites will appear here in real-time.</p>
              </div>
            ) : (
              conversations.map((conv) => {
                const isSelected = conv.id === activeSessionId;
                return (
                  <div
                    key={conv.id}
                    onClick={() => setActiveSessionId(conv.id)}
                    className={`p-3.5 cursor-pointer transition ${
                      isSelected
                        ? "bg-indigo-600/10 border-l-4 border-indigo-500"
                        : "hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="h-6 w-6 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 text-[10px] font-mono shrink-0">
                          <User className="h-3 w-3" />
                        </div>
                        <span className="font-bold text-xs text-white truncate">{conv.visitor_id}</span>
                      </div>
                      {getStatusBadge(conv.status)}
                    </div>

                    <p className="text-xs text-slate-300 line-clamp-1 mb-2 font-normal">
                      {conv.last_message_preview || "No messages yet"}
                    </p>

                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <span className="flex items-center gap-1 truncate max-w-[140px]">
                        <Globe className="h-3 w-3 text-slate-600 shrink-0" />
                        <span className="truncate">{conv.website_name}</span>
                      </span>
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="h-2.5 w-2.5" />
                        <span>{new Date(conv.last_message_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Pane: Conversation Transcript & Agent Control */}
        <div className="lg:col-span-7 flex flex-col rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm overflow-hidden">
          {activeConversation ? (
            <>
              {/* Active Conversation Header */}
              <div className="p-3.5 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between gap-3 shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="h-9 w-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-xs shrink-0">
                    <User className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-xs text-white truncate">{activeConversation.session.visitor_id}</h3>
                      {getStatusBadge(activeConversation.session.status)}
                    </div>
                    <p className="text-[10px] text-slate-400 flex items-center gap-1.5 truncate mt-0.5">
                      <span>{activeConversation.website_name}</span>
                      <span>•</span>
                      <span className="font-mono text-slate-500">{activeConversation.session.channel}</span>
                    </p>
                  </div>
                </div>

                {/* Status Action Controls */}
                <div className="flex items-center gap-1.5 shrink-0">
                  {activeConversation.session.status === "HUMAN_TAKEOVER" ? (
                    <button
                      onClick={() => handleUpdateStatus("BOT_ACTIVE")}
                      disabled={isUpdatingStatus}
                      className="flex items-center gap-1.5 rounded-xl bg-emerald-600/20 border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-600/30 transition disabled:opacity-50"
                    >
                      <PlayCircle className="h-3.5 w-3.5" />
                      <span>Resume AI Bot</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => handleUpdateStatus("HUMAN_TAKEOVER")}
                      disabled={isUpdatingStatus}
                      className="flex items-center gap-1.5 rounded-xl bg-purple-600/20 border border-purple-500/30 px-3 py-1.5 text-xs font-semibold text-purple-300 hover:bg-purple-600/30 transition disabled:opacity-50"
                    >
                      <PauseCircle className="h-3.5 w-3.5" />
                      <span>Take Over</span>
                    </button>
                  )}

                  {activeConversation.session.status !== "CLOSED" ? (
                    <button
                      onClick={() => handleUpdateStatus("CLOSED")}
                      disabled={isUpdatingStatus}
                      className="rounded-xl border border-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition disabled:opacity-50"
                    >
                      Close
                    </button>
                  ) : (
                    <button
                      onClick={() => handleUpdateStatus("BOT_ACTIVE")}
                      disabled={isUpdatingStatus}
                      className="rounded-xl border border-slate-800 px-3 py-1.5 text-xs font-semibold text-indigo-400 hover:bg-slate-800 transition disabled:opacity-50"
                    >
                      Reopen
                    </button>
                  )}
                </div>
              </div>

              {/* Message Transcript Stream */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs bg-slate-950/40">
                {activeConversation.messages.map((msg) => {
                  const isUser = msg.sender === "USER";
                  const isAgent = msg.sender === "AGENT";
                  const isSystem = msg.sender === "SYSTEM";

                  if (isSystem) {
                    return (
                      <div key={msg.id} className="flex justify-center my-2">
                        <span className="rounded-full bg-slate-800/80 border border-slate-700 px-3 py-1 text-[10px] text-slate-400 font-mono">
                          {msg.content}
                        </span>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${
                        isUser ? "items-start" : "items-end"
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-1 px-1 text-[10px] text-slate-500">
                        {isUser ? (
                          <>
                            <User className="h-3 w-3" />
                            <span className="font-semibold text-slate-400">Visitor</span>
                          </>
                        ) : isAgent ? (
                          <>
                            <span className="font-semibold text-purple-300">Agent ({activeConversation.assigned_user_name || "Staff"})</span>
                            <UserCheck className="h-3 w-3 text-purple-400" />
                          </>
                        ) : (
                          <>
                            <span className="font-semibold text-emerald-400">AI Assistant</span>
                            <Bot className="h-3 w-3 text-emerald-400" />
                          </>
                        )}
                        <span>•</span>
                        <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                      </div>

                      <div
                        className={`max-w-[85%] rounded-2xl p-3.5 shadow-sm space-y-2.5 ${
                          isUser
                            ? "bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none"
                            : isAgent
                            ? "bg-purple-950/70 border border-purple-800/80 text-purple-100 rounded-tr-none shadow-purple-950/30"
                            : "bg-indigo-950/60 border border-indigo-800/60 text-indigo-100 rounded-tr-none"
                        }`}
                      >
                        <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                        {/* RAG Tool Indicator if present */}
                        {msg.tool_call && (
                          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                            <span className="text-indigo-400">Tool: {msg.tool_call.tool}</span>
                            <span>{Math.round(msg.tool_call.confidence * 100)}% Conf</span>
                          </div>
                        )}

                        {/* Source Citations */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex flex-wrap items-center gap-1.5">
                            <span className="font-semibold text-slate-500">Grounded:</span>
                            {msg.sources.map((src, idx) => (
                              <a
                                key={idx}
                                href={src.url}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center gap-1 rounded bg-slate-950 border border-slate-800 px-1.5 py-0.5 text-indigo-300 hover:text-indigo-200 truncate max-w-[160px]"
                              >
                                <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                                <span className="truncate">{src.title}</span>
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Agent Reply Composer */}
              <form
                onSubmit={handleSendAgentReply}
                className="p-3 border-t border-slate-800 bg-slate-950/80 flex items-center gap-2 shrink-0"
              >
                <input
                  type="text"
                  value={agentMessage}
                  onChange={(e) => setAgentMessage(e.target.value)}
                  placeholder={
                    activeConversation.session.status === "CLOSED"
                      ? "Conversation closed. Type to reopen and reply..."
                      : "Type message to reply as human agent..."
                  }
                  disabled={isSendingReply}
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-900 py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={isSendingReply || !agentMessage.trim()}
                  className="flex items-center gap-1.5 rounded-xl bg-purple-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-purple-600/30 hover:bg-purple-500 disabled:opacity-50 transition"
                >
                  <Send className="h-3.5 w-3.5" />
                  <span>Send</span>
                </button>
              </form>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-xs text-slate-500">
              <MessageSquare className="h-10 w-10 text-slate-700 opacity-40 mb-3" />
              <p className="font-semibold text-slate-400">Select a conversation</p>
              <p className="text-[11px] mt-1">Choose a conversation from the left to view the live transcript and take action.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
