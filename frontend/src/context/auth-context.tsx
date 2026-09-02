"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiRequest } from "@/lib/api-client";

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  role: "OWNER" | "ADMIN" | "MANAGER" | "AGENT" | "VIEWER";
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  organizations: Organization[];
  currentOrg: Organization | null;
  isLoading: boolean;
  login: (token: string, userData: User) => Promise<void>;
  logout: () => void;
  setCurrentOrg: (org: Organization) => void;
  refreshOrganizations: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const fetchUserProfile = async () => {
    try {
      const userData = await apiRequest<User>("/auth/me");
      setUser(userData);
      await fetchOrgs();
    } catch (err) {
      localStorage.removeItem("saas_token");
      setUser(null);
      setOrganizations([]);
      setCurrentOrg(null);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOrgs = async () => {
    try {
      const orgs = await apiRequest<Organization[]>("/organizations");
      setOrganizations(orgs);
      if (orgs.length > 0) {
        // preserve current or default to first
        setCurrentOrg((prev) => (prev ? orgs.find((o) => o.id === prev.id) || orgs[0] : orgs[0]));
      } else {
        setCurrentOrg(null);
      }
    } catch (err) {
      console.error("Failed to load organizations", err);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("saas_token");
    if (token) {
      fetchUserProfile();
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (token: string, userData: User) => {
    localStorage.setItem("saas_token", token);
    setUser(userData);
    await fetchOrgs();
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("saas_token");
    setUser(null);
    setOrganizations([]);
    setCurrentOrg(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        organizations,
        currentOrg,
        isLoading,
        login,
        logout,
        setCurrentOrg,
        refreshOrganizations: fetchOrgs,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
