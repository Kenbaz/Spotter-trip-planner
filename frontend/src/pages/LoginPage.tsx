import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { Card, CardContent } from "../components/UI/Card";
import { AlertCircle } from "lucide-react";
import { SEO } from "../components/SEO/SEO";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const { login, isLoggingIn } = useAuth(); 
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const result = await login(username, password);
      if (!result.success) {
        setError(result.error || "Login failed");
      }
      // If login is successful, the auth context will update and redirect automatically
    } catch (err) {
      console.error("Login error:", err);
      setError("An unexpected error occurred");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <SEO
        title="Driver login"
        description="Sign in to your Spotter HOS driver account to access trip planning, compliance tracking, and generate routes"
        keywords="driver login, spotter hos, truck driver portal, hours of service login, trucking app"
        noIndex={true}
      />
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center">
            <span className="text-white font-bold text-2xl">S</span>
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">Spotter HOS</h2>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to your driver account
          </p>
        </div>

        {/* Login Form */}
        <Card>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md">
                  <AlertCircle className="w-5 h-5 text-red-500" />
                  <span className="text-sm text-red-700">{error}</span>
                </div>
              )}

              <Input
                label="Username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                autoComplete="username"
                disabled={isLoggingIn}
                className="text-gray-900"
              />

              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
                disabled={isLoggingIn}
                className="text-gray-900"
              />

              <Button
                type="submit"
                className="w-full"
                isLoading={isLoggingIn}
                disabled={!username || !password || isLoggingIn}
              >
                {isLoggingIn ? "Signing in..." : "Sign In"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center">
          <p className="text-xs text-gray-500">
            Having trouble signing in? Contact your fleet manager.
          </p>
        </div>
      </div>
    </div>
  );
}
