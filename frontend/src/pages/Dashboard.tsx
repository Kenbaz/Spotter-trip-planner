import { useMemo } from "react";
import { useAuth } from "../hooks/useAuth";
import { useMyTrips } from "../hooks/useTripQueries";
import { Layout } from "../components/Layout/Layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/UI/Card";
import { Button } from "../components/UI/Button";
import { LoadingSpinner } from "../components/UI/LoadingSpinner";
import {
  Route,
  Clock,
  CheckCircle,
  AlertTriangle,
  Plus,
  Truck,
  MapPin,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { Link } from "react-router-dom";
import type { TripListItem } from "../types";

interface DashboardStats {
  drivingHours: number;
  maxDrivingHours: number;
  onDutyHours: number;
  maxOnDutyHours: number;
  isCompliant: boolean;
  nextBreakRequired: string | null;
  activeTripId: string | null;
}

interface TripCounts {
  total: number;
  completed: number;
  inProgress: number;
  planned: number;
  draft: number;
}

export function DashboardPage() {
  const { user } = useAuth();

  // Fetch trips data
  const {
    data: tripsResponse,
    isLoading,
    isError,
    error,
    refetch,
  } = useMyTrips();

  
  const trips = useMemo(() => {
    return tripsResponse?.trips || [];
  }, [tripsResponse?.trips]);


  // Calculate dashboard statistics
  const dashboardStats = useMemo((): DashboardStats => {
    // Find active trip
    const activeTrip = trips.find(
      (trip: TripListItem) => trip.status === "in_progress"
    );

    // For demo purposes, calculate approximate stats
    // In a real app, this would come from actual HOS tracking data
    const completedToday = trips.filter((trip: TripListItem) => {
      const tripDate = new Date(trip.departure_datetime).toDateString();
      const today = new Date().toDateString();
      return tripDate === today && trip.status === "completed";
    });

    const totalDrivingTime = completedToday.reduce((total, trip) => {
      return total + (trip.total_driving_time || 0);
    }, 0);

    const totalOnDutyTime = totalDrivingTime * 1.3; // Approximate on-duty time

    const isCompliant = totalDrivingTime <= 11 && totalOnDutyTime <= 14;

    // Calculate next break requirement (simplified)
    let nextBreakRequired = null;
    if (activeTrip && totalDrivingTime > 0) {
      const hoursUntilBreak = Math.max(0, 8 - (totalDrivingTime % 8));
      if (hoursUntilBreak < 2) {
        const breakTime = new Date();
        breakTime.setHours(breakTime.getHours() + hoursUntilBreak);
        nextBreakRequired = breakTime.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
      }
    }

    return {
      drivingHours: Math.round(totalDrivingTime * 10) / 10,
      maxDrivingHours: 11,
      onDutyHours: Math.round(totalOnDutyTime * 10) / 10,
      maxOnDutyHours: 14,
      isCompliant,
      nextBreakRequired,
      activeTripId: activeTrip?.trip_id || null,
    };
  }, [trips]);

  // Calculate trip counts
  const tripCounts = useMemo((): TripCounts => {
    return trips.reduce(
      (counts, trip: TripListItem) => {
        counts.total++;
        switch (trip.status) {
          case "completed":
            counts.completed++;
            break;
          case "in_progress":
            counts.inProgress++;
            break;
          case "planned":
            counts.planned++;
            break;
          case "draft":
            counts.draft++;
            break;
          default:
            break;
        }
        return counts;
      },
      { total: 0, completed: 0, inProgress: 0, planned: 0, draft: 0 }
    );
  }, [trips]);

  // Get recent trips (last 5)
  const recentTrips = useMemo(() => {
    return trips
      .sort(
        (a: TripListItem, b: TripListItem) =>
          new Date(b.departure_datetime).getTime() -
          new Date(a.departure_datetime).getTime()
      )
      .slice(0, 5);
  }, [trips]);

  const formatDateTime = (dateTimeString: string): string => {
    return new Date(dateTimeString).toLocaleDateString();
  };

  // Loading state
  if (isLoading) {
    return (
      <Layout>
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Welcome back, {user?.first_name}!
              </h1>
              <p className="text-gray-600">Loading your dashboard...</p>
            </div>
          </div>

          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="large" text="Loading dashboard data..." />
          </div>
        </div>
      </Layout>
    );
  }

  // Error state
  if (isError) {
    return (
      <Layout>
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Welcome back, {user?.first_name}!
              </h1>
              <p className="text-gray-600">Dashboard</p>
            </div>
            <Link to="/trips/new">
              <Button leftIcon={<Plus className="w-4 h-4" />}>
                Plan New Trip
              </Button>
            </Link>
          </div>

          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <AlertCircle className="w-8 h-8 text-red-600" />
                <div>
                  <h3 className="text-lg font-medium text-red-800">
                    Failed to Load Dashboard
                  </h3>
                  <p className="text-red-700 mt-1">
                    {error instanceof Error
                      ? error.message
                      : "An unexpected error occurred"}
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => refetch()}
                    className="mt-3"
                    leftIcon={<RefreshCw className="w-4 h-4" />}
                  >
                    Try Again
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Welcome Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome back, {user?.first_name}!
            </h1>
            <p className="text-gray-600">
              Here's your HOS status and recent activity
            </p>
          </div>
          <Link to="/trips/new">
            <Button leftIcon={<Plus className="w-4 h-4" />}>
              Plan New Trip
            </Button>
          </Link>
        </div>

        {/* Active Trip Alert */}
        {dashboardStats.activeTripId && (
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Truck className="w-6 h-6 text-blue-600" />
                  <div>
                    <p className="font-medium text-blue-800">
                      Active Trip in Progress
                    </p>
                    <p className="text-sm text-blue-600">
                      You have an active trip running. Monitor your HOS status
                      carefully.
                    </p>
                  </div>
                </div>
                <Link to={`/trips/${dashboardStats.activeTripId}`}>
                  <Button variant="secondary" size="sm">
                    View Trip
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}

        {/* HOS Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Driving Hours */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    Driving Hours
                  </p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dashboardStats.drivingHours} /{" "}
                    {dashboardStats.maxDrivingHours}
                  </p>
                  <p className="text-sm text-gray-500">
                    {(
                      dashboardStats.maxDrivingHours -
                      dashboardStats.drivingHours
                    ).toFixed(1)}{" "}
                    hours remaining
                  </p>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* On-Duty Hours */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    On-Duty Hours
                  </p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dashboardStats.onDutyHours} /{" "}
                    {dashboardStats.maxOnDutyHours}
                  </p>
                  <p className="text-sm text-gray-500">
                    {(
                      dashboardStats.maxOnDutyHours - dashboardStats.onDutyHours
                    ).toFixed(1)}{" "}
                    hours remaining
                  </p>
                </div>
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Truck className="w-6 h-6 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Compliance Status */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    HOS Status
                  </p>
                  <p
                    className={`text-2xl font-bold ${
                      dashboardStats.isCompliant
                        ? "text-green-600"
                        : "text-red-600"
                    }`}
                  >
                    {dashboardStats.isCompliant ? "Compliant" : "Violation"}
                  </p>
                  <p className="text-sm text-gray-500">Current status</p>
                </div>
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    dashboardStats.isCompliant ? "bg-green-100" : "bg-red-100"
                  }`}
                >
                  {dashboardStats.isCompliant ? (
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 text-red-600" />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Next Break */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">
                    Next Break
                  </p>
                  <p className="text-2xl font-bold text-gray-900">
                    {dashboardStats.nextBreakRequired || "N/A"}
                  </p>
                  <p className="text-sm text-gray-500">
                    {dashboardStats.nextBreakRequired
                      ? "30-min break required"
                      : "No break required"}
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trip Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {tripCounts.completed}
                </p>
                <p className="text-sm text-gray-600">Completed</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">
                  {tripCounts.inProgress}
                </p>
                <p className="text-sm text-gray-600">In Progress</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">
                  {tripCounts.planned}
                </p>
                <p className="text-sm text-gray-600">Planned</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-600">
                  {tripCounts.draft}
                </p>
                <p className="text-sm text-gray-600">Draft</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Trips and Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Trips List */}
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Recent Trips</CardTitle>
                <Link to="/trips">
                  <Button variant="ghost" size="sm">
                    View All
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {recentTrips.length === 0 ? (
                <div className="text-center py-8">
                  <Route className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-4">No trips yet</p>
                  <Link to="/trips/new">
                    <Button size="sm">Plan Your First Trip</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {recentTrips.map((trip: TripListItem) => (
                    <Link
                      key={trip.trip_id}
                      to={`/trips/${trip.trip_id}`}
                      className="block hover:bg-gray-50 rounded-lg transition-colors"
                    >
                      <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                            <Route className="w-5 h-5 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">
                              {trip.current_address} →{" "}
                              {trip.destination_address}
                            </p>
                            <p className="text-sm text-gray-500">
                              {formatDateTime(trip.departure_datetime)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              trip.status === "completed"
                                ? "bg-green-100 text-green-800"
                                : trip.status === "in_progress"
                                ? "bg-blue-100 text-blue-800"
                                : trip.status === "planned"
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {trip.status_display}
                          </span>
                          {trip.is_hos_compliant && (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          )}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Link to="/trips/new" className="block">
                  <Button className="w-full justify-start" variant="ghost">
                    <Plus className="w-4 h-4 mr-2" />
                    Plan New Trip
                  </Button>
                </Link>

                <Link to="/trips" className="block">
                  <Button className="w-full justify-start" variant="ghost">
                    <Route className="w-4 h-4 mr-2" />
                    View My Trips
                  </Button>
                </Link>

                {dashboardStats.activeTripId && (
                  <Link
                    to={`/trips/${dashboardStats.activeTripId}`}
                    className="block"
                  >
                    <Button className="w-full justify-start" variant="ghost">
                      <Truck className="w-4 h-4 mr-2" />
                      View Active Trip
                    </Button>
                  </Link>
                )}

                <Link to="/profile" className="block">
                  <Button className="w-full justify-start" variant="ghost">
                    <MapPin className="w-4 h-4 mr-2" />
                    Update Profile
                  </Button>
                </Link>
              </div>

              {/* Today's Summary */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h4 className="text-sm font-medium text-gray-900 mb-3">
                  Today's Summary
                </h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Trips Completed</span>
                    <span className="font-medium">{tripCounts.completed}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Hours Driven</span>
                    <span className="font-medium">
                      {dashboardStats.drivingHours}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">HOS Status</span>
                    <span
                      className={`font-medium ${
                        dashboardStats.isCompliant
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {dashboardStats.isCompliant ? "Compliant" : "Violation"}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
