import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { Card, CardContent } from "../components/UI/Card";
import { AlertCircle, Play } from "lucide-react";
import { SEO } from "../components/SEO/SEO";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  const { login, isLoggingIn } = useAuth();

  // Demo credentials
  const DEMO_USERNAME = "John_Doe";
  const DEMO_PASSWORD = "@Johndriver1234";

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

  const handleDemoLogin = async () => {
    setError("");
    setIsDemoLoading(true);

    try {
      const result = await login(DEMO_USERNAME, DEMO_PASSWORD);
      if (!result.success) {
        setError(result.error || "Demo login failed");
      }
    } catch (err) {
      console.error("Demo login error:", err);
      setError("Demo login failed - please try again");
    } finally {
      setIsDemoLoading(false);
    }
  };


  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 pb-[20%] md:pb-0">
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

        {/* Demo Access Section */}
        <Card className="bg-blue-50 border-blue-200">
          <CardContent>
            <div className="text-center space-y-4">
              <div className="flex items-center justify-center space-x-2">
                <Play className="w-5 h-5 text-blue-600" />
                <h3 className="text-lg font-semibold text-blue-900">
                  Try Our Demo
                </h3>
              </div>

              <p className="text-sm text-blue-700">
                Experience the full HOS Trip Planner immediately with our demo
                account
              </p>

              <div className="space-y-3">
                <Button
                  onClick={handleDemoLogin}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                  isLoading={isDemoLoading}
                  disabled={isLoggingIn}
                >
                  {isDemoLoading ? "Accessing Demo..." : "Access Demo Account"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Divider */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-gray-50 text-gray-500">
              Or sign in with your account
            </span>
          </div>
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
                disabled={isLoggingIn || isDemoLoading}
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
                disabled={isLoggingIn || isDemoLoading}
                className="text-gray-900"
              />

              <Button
                type="submit"
                className="w-full"
                isLoading={isLoggingIn}
                disabled={
                  !username || !password || isLoggingIn || isDemoLoading
                }
              >
                {isLoggingIn ? "Signing in..." : "Sign In"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center space-y-2">
          <p className="text-xs text-gray-500">
            Having trouble signing in? Contact your fleet manager.
          </p>
          <p className="text-xs text-gray-400">
            Demo account provides full access to explore all features
          </p>
        </div>
      </div>
    </div>
  );
}
