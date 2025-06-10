/* eslint-disable @typescript-eslint/no-explicit-any */

import { apiClient } from "./apiClient";
import type {
  LoginResponse,
  TokenRefreshResponse,
  User,
} from "../types";

class AuthService {
  private readonly ACCESS_TOKEN_KEY = "access_token";
  private readonly REFRESH_TOKEN_KEY = "refresh_token";

  // Get token from localStorage
  getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
  }

  clearTokens(): void {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
  }

  // Check is user is authenticated
  isAuthenticated(): boolean {
    const accessToken = this.getAccessToken();
    if (!accessToken) return false;

    try {
      // Check if token is expired
      const payload = JSON.parse(atob(accessToken.split(".")[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp > currentTime;
    } catch (error) {
      console.error("Invalid token format:", error);
      return false;
    }
  }

  // Login user
  async login(
    username: string,
    password: string
  ): Promise<{
    success: boolean;
    user?: User;
    error?: string;
  }> {
    try {
      console.log("Attempting login for username:", username);
      const response = await apiClient.post<LoginResponse>("/login/", {
        username,
        password,
      });

      console.log("Login response:", response.data);

      if (response.data.access && response.data.refresh) {
        this.setTokens(response.data.access, response.data.refresh);
        return {
          success: true,
          user: response.data.user,
        };
      }

      return {
        success: false,
        error: "Invalid response format",
      };
    } catch (error: any) {
      console.error("Login error details:", error); // Debug log
      console.error("Error response:", error.response);
      
      let errorMessage = "Login failed";

      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.non_field_errors[0]) {
        errorMessage = error.response.data.non_field_errors[0];
      } else if (error.message) {
        errorMessage = error.message;
      }

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Logout user
  async logout(): Promise<void> {
    try {
      const refreshToken = this.getRefreshToken();
      if (refreshToken) {
        await apiClient.post("/auth/logout/", { refresh: refreshToken });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      this.clearTokens();
    }
  }

  // Refresh access token
  async refreshToken(): Promise<boolean> {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        return false;
      }

      const response = await apiClient.post<TokenRefreshResponse>(
        "/auth/refresh/",
        {
          refresh: refreshToken,
        }
      );

      if (response.data.access) {
        localStorage.setItem(this.ACCESS_TOKEN_KEY, response.data.access);
        return true;
      }

      return false;
    } catch (error) {
      console.error("Token refresh error:", error);
      this.clearTokens();
      return false;
    }
  }

  // Get current user
  async getCurrentUser(): Promise<User | null> {
    try {
      if (!this.isAuthenticated()) {
        return null;
      }

      const response = await apiClient.get<{ success: boolean; user: User }>(
        "/current_user/"
      );

      if (response.data.success) {
        return response.data.user;
      }

      return null;
    } catch (error: any) {
      console.error("Failed to get current user:", error);

      if (error.response?.status === 401) {
        this.clearTokens();
      }

      return null;
    }
  }

  // Verify token is still valid
  async verifyToken(): Promise<boolean> {
    try {
      const accessToken = this.getAccessToken();
      if (!accessToken) return false;

      await apiClient.post("/auth/verify/", {
        token: accessToken,
      });

      return true;
    } catch (error) {
      console.error("Token verification failed:", error);
      return false;
    }
  }
};

export const authService = new AuthService();
