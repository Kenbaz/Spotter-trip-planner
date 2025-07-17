import { apiClient } from "./apiClient";
import type { LoginResponse, TokenRefreshResponse, User, ApiError } from "../types";


class AuthService {
  private readonly ACCESS_TOKEN_KEY = "access_token";
  private readonly REFRESH_TOKEN_KEY = "refresh_token";
  private readonly MAX_RETRY_ATTEMPTS = 3;
  private readonly RETRY_DELAY = 1000; // 1 second

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

  // Check if user is authenticated with improved token validation
  isAuthenticated(): boolean {
    const accessToken = this.getAccessToken();
    if (!accessToken) return false;

    try {
      // Parse JWT token to check expiration
      const payload = JSON.parse(atob(accessToken.split(".")[1]));
      const currentTime = Date.now() / 1000;

      // Add 60 second buffer to account for clock skew
      return payload.exp > currentTime + 60;
    } catch (error) {
      console.error("Invalid token format:", error);
      return false;
    }
  }

  // Utility function to check if token is about to expire (within 5 minutes)
  private isTokenExpiringSoon(): boolean {
    const accessToken = this.getAccessToken();
    if (!accessToken) return false;

    try {
      const payload = JSON.parse(atob(accessToken.split(".")[1]));
      const currentTime = Date.now() / 1000;
      const fiveMinutesFromNow = currentTime + 300; // 5 minutes

      return payload.exp < fiveMinutesFromNow;
    } catch {
      return false;
    }
  }

  // Helper function to wait before retry
  private async delay(milliseconds: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
  }

  // Determine if error is a network/temporary error vs auth error
  private isTemporaryError(error: ApiError): boolean {
    // Network errors
    if (!error.response) return true;

    // Server errors (5xx) are temporary
    if (error.response.status >= 500) return true;

    // Request timeout
    if (error.code === "ECONNABORTED") return true;

    // These are auth errors - not temporary
    if ([401, 403].includes(error.response.status)) return false;

    // Other 4xx errors might be temporary (rate limiting, etc.)
    if (error.response.status >= 400 && error.response.status < 500)
      return true;

    return false;
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
      const response = await apiClient.post<LoginResponse>("/login/", {
        username,
        password,
      });

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
    } catch (error) {
      console.error("Login error details:", error);

      const apiError = error as ApiError;
      console.error("Error response:", apiError.response?.data);

      let errorMessage = "Login failed";

      if (apiError.response?.data) {
        const errorData = apiError.response.data;

        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
          errorMessage = errorData.non_field_errors[0];
        } else if (errorData.error) {
          errorMessage = errorData.error;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (typeof errorData === "string") {
          errorMessage = errorData;
        }
      } else if (apiError.message) { 
        errorMessage = apiError.message;
      }

      if (
        errorMessage.toLowerCase().includes("invalid credentials") ||
        errorMessage.toLowerCase().includes("authentication failed") ||
        errorMessage.toLowerCase().includes("invalid username") ||
        errorMessage.toLowerCase().includes("invalid password") ||
        errorMessage.toLowerCase().includes("unable to log in")
      ) {
        errorMessage =
          "Invalid username or password. Please check your credentials and try again.";
      } else if (apiError.response?.status === 400) {
        errorMessage =
          "Invalid username or password. Please check your credentials and try again.";
      } else if (apiError.response?.status === 401) {
        errorMessage =
          "Invalid username or password. Please check your credentials and try again.";
      } else if (apiError.response?.status === 429) {
        errorMessage =
          "Too many login attempts. Please wait a moment and try again.";
      } else if (apiError.response?.status && apiError.response.status >= 500) {
        errorMessage =
          "Server error. Please try again later or contact support.";
      } else if (!apiError.response) {
        errorMessage =
          "Unable to connect to the server. Please check your internet connection.";
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

  // Refresh access token with improved error handling
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

        // If we get a new refresh token, update it
        if (response.data.refresh) {
          localStorage.setItem(this.REFRESH_TOKEN_KEY, response.data.refresh);
        }

        return true;
      }

      return false;
    } catch (error) {
      console.error("Token refresh error:", error);

      const apiError = error as ApiError;

      // Only clear tokens if it's definitely an auth error
      if (apiError.response?.status === 401) {
        console.log("Refresh token is invalid, clearing tokens");
        this.clearTokens();
      }

      return false;
    }
  }

  // Get current user with retry logic and improved error handling
  async getCurrentUser(): Promise<User | null> {
    // First check if we have a valid token
    if (!this.isAuthenticated()) {
      return null;
    }

    // Try to refresh token if it's expiring soon
    if (this.isTokenExpiringSoon()) {
      const refreshed = await this.refreshToken();
      if (!refreshed) {
        return null;
      }
    }

    // Attempt to get current user with retry logic
    for (let attempt = 1; attempt <= this.MAX_RETRY_ATTEMPTS; attempt++) {
      try {
        // The backend returns the user data directly, not wrapped in { success, user }
        const response = await apiClient.get<User>("/current_user/");

        if (response.data && typeof response.data === "object") {
          return response.data;
        }

        return null;
      } catch (error) {
        console.error(`Get current user attempt ${attempt} failed:`, error);

        const apiError = error as ApiError;

        // If it's an auth error (401/403), don't retry
        if (apiError.response?.status === 401) {
          console.log("Received 401 error - attempting token refresh");

          // Try to refresh token once
          const refreshed = await this.refreshToken();
          if (refreshed && attempt === 1) {
            console.log("Token refreshed, retrying current user request");
            continue; // Retry with new token
          } else {
            console.log(
              "Token refresh failed or max attempts reached, clearing tokens"
            );
            this.clearTokens();
            return null;
          }
        }

        // If it's the last attempt or a non-temporary error, give up
        if (
          attempt === this.MAX_RETRY_ATTEMPTS ||
          !this.isTemporaryError(apiError)
        ) {
          console.error(
            "Max attempts reached or non-temporary error, giving up"
          );

          // Only clear tokens for auth errors, not network errors
          if (apiError.response?.status === 403) {
            this.clearTokens();
          }

          return null;
        }

        // Wait before retrying for temporary errors
        // console.log(
        //   `Temporary error detected, waiting ${this.RETRY_DELAY}ms before retry`
        // );
        await this.delay(this.RETRY_DELAY * attempt);
      }
    }

    return null;
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

      const apiError = error as ApiError;

      // Only clear tokens for definitive auth errors
      if (apiError.response?.status === 401) {
        this.clearTokens();
      }

      return false;
    }
  }
}

export const authService = new AuthService();
