import { createContext, useEffect, useState, useCallback } from "react";
import type { ReactNode } from "react";
import { authService } from "../services/authService";
import type { User } from "../types";

export interface AuthContextType {
  user: User | null;
  isInitializing: boolean;
  isLoggingIn: boolean;
  isAuthenticated: boolean;
  login: (
    username: string,
    password: string
  ) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  initializeAuth: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [initializationAttempted, setInitializationAttempted] = useState(false);

  const isAuthenticated = !!user && !!authService.getAccessToken();

  const initializeAuth = useCallback(async () => {
    if (initializationAttempted) {
      return;
    }

    try {
      setIsInitializing(true);
      console.log("Initializing authentication...");

      // First check if we have tokens stored
      const hasTokens =
        authService.getAccessToken() && authService.getRefreshToken();

      if (!hasTokens) {
        console.log("No tokens found, user not authenticated");
        setUser(null);
        return;
      }

      // Check if current token is valid
      const isTokenValid = authService.isAuthenticated();

      if (!isTokenValid) {
        console.log("Token is expired, attempting refresh");
        const refreshed = await authService.refreshToken();

        if (!refreshed) {
          console.log("Token refresh failed, clearing auth state");
          setUser(null);
          return;
        }
      }

      // Try to get current user info
      const currentUser = await authService.getCurrentUser();

      if (currentUser) {
        console.log(
          "Authentication initialized successfully with user:",
          currentUser.username
        );
        setUser(currentUser);
      } else {
        console.log("Failed to get current user info");
        if (authService.isAuthenticated()) {
          console.log(
            "Valid token exists, but API call failed - this could be temporary"
          );
          setUser(null);
        } else {
          console.log("No valid tokens, user not authenticated");
          setUser(null);
        }
      }
    } catch (error) {
      console.error("Failed to initialize auth:", error);

      // Don't clear tokens on network errors, only on definitive auth failures
      if (authService.isAuthenticated()) {
        console.log("Keeping user authenticated despite initialization error");
      } else {
        console.log("Clearing auth state due to invalid tokens");
        authService.clearTokens();
        setUser(null);
      }
    } finally {
      setIsInitializing(false);
      setInitializationAttempted(true);
    }
  }, [initializationAttempted]);

  // Initialize auth on mount
  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  // Set up periodic token refresh
  useEffect(() => {
    if (!user) return;

    const interval = setInterval(async () => {
      try {
        // Check if token needs refresh (within 5 minutes of expiry)
        const accessToken = authService.getAccessToken();
        if (!accessToken) return;

        const payload = JSON.parse(atob(accessToken.split(".")[1]));
        const currentTime = Date.now() / 1000;
        const fiveMinutesFromNow = currentTime + 300;

        if (payload.exp < fiveMinutesFromNow) {
          console.log("Token expiring soon, refreshing...");
          const success = await refreshToken();
          if (!success) {
            console.log("Periodic token refresh failed");
          }
        }
      } catch (error) {
        console.error("Error in periodic token check:", error);
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [user]);

  const login = async (username: string, password: string) => {
    try {
      setIsLoggingIn(true);
      const result = await authService.login(username, password);

      if (result.success && result.user) {
        setUser(result.user);
        setInitializationAttempted(true);
        return { success: true };
      }

      return { success: false, error: result.error };
    } catch (error) {
      console.error("Login error in context:", error);
      return {
        success: false,
        error: error instanceof Error ? error.message : "Login failed",
      };
    } finally {
      setIsLoggingIn(false);
    }
  };

  const logout = async () => {
    try {
      setIsInitializing(true);
      await authService.logout();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setUser(null);
      setInitializationAttempted(false);
      setIsInitializing(false);
    }
  };

  const refreshToken = async () => {
    try {
      const success = await authService.refreshToken();

      if (!success) {
        console.log("Token refresh failed, logging out");
        setUser(null);
        setInitializationAttempted(false);
        return false;
      }

      if (user && user.id === 0) {
        try {
          const currentUser = await authService.getCurrentUser();
          if (currentUser) {
            setUser(currentUser);
          }
        } catch (error) {
          console.log(
            "Could not fetch full user data after token refresh:",
            error
          );
        }
      }

      return true;
    } catch (error) {
      console.error("Refresh token error:", error);
      setUser(null);
      setInitializationAttempted(false);
      return false;
    }
  };

  const value = {
    user,
    isInitializing,
    isLoggingIn,
    isAuthenticated,
    login,
    logout,
    refreshToken,
    initializeAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
