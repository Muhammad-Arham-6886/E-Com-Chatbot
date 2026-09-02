"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/auth-context";
import { apiRequest } from "@/lib/api-client";
import { Building, Shield, CheckCircle2, AlertCircle, Save } from "lucide-react";

export default function OrganizationSettingsPage() {
  const { currentOrg, refreshOrganizations } = useAuth();
  const [orgName, setOrgName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canEdit = currentOrg?.role === "OWNER" || currentOrg?.role === "ADMIN";

  useEffect(() => {
    if (currentOrg) {
      setOrgName(currentOrg.name);
    }
  }, [currentOrg]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentOrg || !canEdit) return;

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      await apiRequest(`/organizations/${currentOrg.id}`, {
        method: "PUT",
        body: JSON.stringify({ name: orgName.trim() }),
      });
      setSuccess("Organization settings updated successfully");
      await refreshOrganizations();
    } catch (err: any) {
      setError(err.message || "Failed to update organization");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Organization Settings</h1>
        <p className="text-xs text-slate-400 mt-1">
          Configure your workspace details and tenant identifiers.
        </p>
      </div>

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

      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 backdrop-blur-sm">
        <form onSubmit={handleUpdate} className="space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Organization Name
              </label>
              <div className="relative">
                <Building className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  required
                  disabled={!canEdit}
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 py-2.5 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Tenant Slug (Unique)
              </label>
              <input
                type="text"
                disabled
                value={currentOrg?.slug || ""}
                className="w-full rounded-xl border border-slate-800 bg-slate-950/60 py-2.5 px-4 text-xs text-slate-400 font-mono focus:outline-none cursor-not-allowed"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Your Role in Organization
            </label>
            <div className="flex items-center gap-2">
              <span className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-bold text-indigo-300">
                {currentOrg?.role}
              </span>
              {!canEdit && (
                <span className="text-xs text-slate-500">
                  (You need ADMIN or OWNER permissions to edit organization details)
                </span>
              )}
            </div>
          </div>

          {canEdit && (
            <div className="flex justify-end border-t border-slate-800/80 pt-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
              >
                <Save className="h-4 w-4" />
                <span>{isSubmitting ? "Saving..." : "Save Changes"}</span>
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
