/* eslint-disable @typescript-eslint/no-explicit-any */

import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiClient {
  private client: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (error?: any) => void;
  }> = [];

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 second timeout
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }

  private processQueue(error: any, token: string | null = null): void {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });

    this.failedQueue = [];
  }

  // Check if the request is to an authentication endpoint
  private isAuthenticationEndpoint(url?: string): boolean {
    if (!url) return false;

    const authEndpoints = ["/login/", "/auth/refresh/", "/auth/verify/"];
    return authEndpoints.some((endpoint) => url.includes(endpoint));
  }

  private setupInterceptors(): void {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("access_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Don't try to refresh tokens for authentication endpoints
        if (this.isAuthenticationEndpoint(originalRequest.url)) {
          console.log(
            "401 error on authentication endpoint, not attempting token refresh"
          );
          return Promise.reject(error);
        }

        // If unauthorized and we haven't already tried to refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // If we're already refreshing, queue this request
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            })
              .then((token) => {
                originalRequest.headers.Authorization = `Bearer ${token}`;
                return this.client(originalRequest);
              })
              .catch((err) => {
                return Promise.reject(err);
              });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const refreshToken = localStorage.getItem("refresh_token");
            if (!refreshToken) {
              throw new Error("No refresh token available");
            }

            console.log("Attempting to refresh token due to 401 error");

            // Try to refresh the token
            const refreshResponse = await axios.post(
              `${API_BASE_URL}/auth/refresh/`,
              { refresh: refreshToken }
            );

            const newAccessToken = refreshResponse.data.access;
            localStorage.setItem("access_token", newAccessToken);

            // If we get a new refresh token, update it
            if (refreshResponse.data.refresh) {
              localStorage.setItem(
                "refresh_token",
                refreshResponse.data.refresh
              );
            }

            console.log("Token refreshed successfully in interceptor");

            // Process the queued requests with new token
            this.processQueue(null, newAccessToken);

            // Retry the original request with new token
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            console.error("Token refresh failed in interceptor:", refreshError);

            // Process the queued requests with error
            this.processQueue(refreshError, null);

            // Clear tokens
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");

            if (
              window.location.pathname !== "/login" &&
              !originalRequest.url?.includes("/auth/")
            ) {
              console.log("Redirecting to login due to refresh failure");
              window.location.href = "/login";
            }

            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // HTTP methods
  async get<T = any>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return this.client.get<T>(url, config);
  }

  async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, config);
  }

  async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, config);
  }

  async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(url, data, config);
  }

  async delete<T = any>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, config);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
