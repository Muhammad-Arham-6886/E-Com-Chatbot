"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import {
  Users,
  UserPlus,
  Shield,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Mail,
  ShieldAlert,
} from "lucide-react";

interface Member {
  id: string;
  organization_id: string;
  user_id: string;
  role: "OWNER" | "ADMIN" | "MANAGER" | "AGENT" | "VIEWER";
  status: "ACTIVE" | "INVITED" | "SUSPENDED";
  created_at: string;
  user?: {
    id: string;
    email: string;
    full_name?: string | null;
  };
}

export default function TeamManagementPage() {
  const { currentOrg, user } = useAuth();
  const [members, setMembers] = useState<Member[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Invite Modal
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<string>("VIEWER");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canManageMembers = currentOrg?.role === "OWNER" || currentOrg?.role === "ADMIN";

  const fetchMembers = async () => {
    if (!currentOrg) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiRequest<Member[]>(`/organizations/${currentOrg.id}/members`);
      setMembers(data);
    } catch (err: any) {
      setError(err.message || "Failed to load organization members");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, [currentOrg]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg) return;
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      await apiRequest(`/organizations/${currentOrg.id}/members`, {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail,
          role: inviteRole,
        }),
      });

      setSuccess(`User ${inviteEmail} added to organization successfully!`);
      setInviteEmail("");
      setIsInviteOpen(false);
      await fetchMembers();
    } catch (err: any) {
      setError(err.message || "Failed to add member.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRoleChange = async (targetUserId: string, newRole: string) => {
    if (!currentOrg) return;
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/organizations/${currentOrg.id}/members/${targetUserId}`, {
        method: "PUT",
        body: JSON.stringify({ role: newRole }),
      });
      setSuccess("Member role updated successfully");
      await fetchMembers();
    } catch (err: any) {
      setError(err.message || "Failed to update role");
    }
  };

  const handleRemoveMember = async (targetUserId: string, targetName: string) => {
    if (!currentOrg) return;
    if (!confirm(`Are you sure you want to remove ${targetName} from this organization?`)) return;

    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/organizations/${currentOrg.id}/members/${targetUserId}`, {
        method: "DELETE",
      });
      setSuccess("Member removed successfully");
      await fetchMembers();
    } catch (err: any) {
      setError(err.message || "Failed to remove member");
    }
  };

  const roleColors: Record<string, string> = {
    OWNER: "bg-purple-500/10 text-purple-400 border-purple-500/30",
    ADMIN: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
    MANAGER: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    AGENT: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    VIEWER: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Team & Access Control</h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage organization members, assign roles, and control permissions.
          </p>
        </div>
        {canManageMembers && (
          <button
            onClick={() => setIsInviteOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500"
          >
            <UserPlus className="h-4 w-4" />
            <span>Add Member</span>
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

      {/* Members Table Card */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm">
        <div className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Users className="h-4 w-4 text-indigo-400" />
            <span>Members ({members.length})</span>
          </div>
          {!canManageMembers && (
            <span className="text-[11px] text-slate-500">Read-only permissions (Requires ADMIN or OWNER to modify)</span>
          )}
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500 text-xs">Loading members...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800/80 bg-slate-950/40 text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                <tr>
                  <th className="px-6 py-3.5">User</th>
                  <th className="px-6 py-3.5">Role</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Joined</th>
                  {canManageMembers && <th className="px-6 py-3.5 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {members.map((m) => {
                  const isSelf = m.user_id === user?.id;
                  const isSoleOwner = m.role === "OWNER" && members.filter((x) => x.role === "OWNER").length === 1;

                  return (
                    <tr key={m.id} className="hover:bg-slate-800/30 transition">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 font-bold text-indigo-400 border border-slate-700">
                            {m.user?.full_name?.substring(0, 1) || m.user?.email.substring(0, 1).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-semibold text-white">
                              {m.user?.full_name || "User"} {isSelf && <span className="text-[10px] text-indigo-400 font-mono">(You)</span>}
                            </p>
                            <p className="text-[11px] text-slate-400">{m.user?.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {canManageMembers && !isSoleOwner ? (
                          <select
                            value={m.role}
                            onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                            className={`rounded-lg border px-2.5 py-1 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500/20 bg-slate-950 ${
                              roleColors[m.role] || "border-slate-800 text-slate-300"
                            }`}
                          >
                            <option value="OWNER">OWNER</option>
                            <option value="ADMIN">ADMIN</option>
                            <option value="MANAGER">MANAGER</option>
                            <option value="AGENT">AGENT</option>
                            <option value="VIEWER">VIEWER</option>
                          </select>
                        ) : (
                          <span className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-[11px] font-semibold ${roleColors[m.role]}`}>
                            {m.role}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          {m.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-[11px] font-mono">
                        {new Date(m.created_at).toLocaleDateString()}
                      </td>
                      {canManageMembers && (
                        <td className="px-6 py-4 text-right">
                          {!isSoleOwner && (
                            <button
                              onClick={() => handleRemoveMember(m.user_id, m.user?.email || "user")}
                              className="rounded-lg p-1.5 text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition"
                              title="Remove Member"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Invite Member Modal */}
      {isInviteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
              <h3 className="text-base font-bold text-white">Add Member to {currentOrg?.name}</h3>
              <button
                onClick={() => setIsInviteOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  User Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input
                    type="email"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@company.com"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  Note: The user should already have registered an account on the platform.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Role & Permissions
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 px-3 text-xs text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="VIEWER">VIEWER (Read-only access)</option>
                  <option value="AGENT">AGENT (Chat & product operations)</option>
                  <option value="MANAGER">MANAGER (Manage knowledge & analytics)</option>
                  <option value="ADMIN">ADMIN (Full management excluding org deletion)</option>
                  <option value="OWNER">OWNER (Full ownership)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsInviteOpen(false)}
                  className="rounded-xl border border-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                >
                  {isSubmitting ? "Adding..." : "Add Member"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
