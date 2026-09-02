"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
  currentOrg: Organization | null;
  isLoading: boolean;
  login: (token: string, userData: User) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const fetchUserProfile = async () => {
    try {
      const userData = await apiRequest<User>("/auth/me");
      setUser(userData);
      await fetchOrg();
    } catch (err) {
      localStorage.removeItem("saas_token");
      setUser(null);
      setCurrentOrg(null);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOrg = async () => {
    try {
      const orgs = await apiRequest<Organization[]>("/organizations");
      if (orgs.length > 0) {
        setCurrentOrg(orgs[0]);
      } else {
        setCurrentOrg(null);
      }
    } catch (err) {
      console.error("Failed to load organization", err);
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
    await fetchOrg();
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("saas_token");
    setUser(null);
    setCurrentOrg(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        currentOrg,
        isLoading,
        login,
        logout,
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
