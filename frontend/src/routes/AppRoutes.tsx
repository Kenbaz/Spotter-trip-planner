import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { LoadingSpinner } from "../components/UI/LoadingSpinner";
import { LoginPage } from "../pages/LoginPage";
// import DashboardPage from "../pages/Dashboard";
// import TripsPage from "../pages/TripsPage";
// import TripDetailPage from "../pages/TripsDetailsPage";
import { CreateTripPage } from "../pages/CreateTripsPage";
import { ProtectedRoute } from "../components/Auth/ProtectedRoute";
import { PublicRoute } from "../components/Auth/PublicRoute";
import {
  LazyLoadedDashboardPage,
  LazyLoadedTripsPage,
  LazyLoadedTripDetailPage,
} from "../components/LazyComponents/LazyComponents";


export function AppRoutes() { 
    const { isInitializing } = useAuth();

    if (isInitializing) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <LoadingSpinner size="large" />
            </div>
        );
    }

    return (
      <Routes>
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <LazyLoadedDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <LazyLoadedDashboardPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/trips"
          element={
            <ProtectedRoute>
              <LazyLoadedTripsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/trips/new"
          element={
            <ProtectedRoute>
              <CreateTripPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/trips/:tripId"
          element={
            <ProtectedRoute>
              <LazyLoadedTripDetailPage />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
}
