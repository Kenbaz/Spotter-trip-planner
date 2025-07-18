import { useMemo } from "react";
import { useAuth } from "../hooks/useAuth";
import { useMyTrips, useCurrentDriverStatus } from "../hooks/useTripQueries";
import { DriverStatusCard } from "../components/UI/DriverStatusCard";
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
} from "lucide-react";
import { Link } from "react-router-dom";
import type { TripListItem } from "../types";
import {motion} from "framer-motion";
import { SEO } from "../components/SEO/SEO";

interface DashboardStats {
  activeTripId: string | null;
  totalTrips: number;
  completedToday: number;
  inProgress: number;
  planned: number;
  hoursWorkedToday: number;
  nextBreakTime: string | null;
}

interface TripCounts {
  total: number;
  completed: number;
  inProgress: number;
  planned: number;
  draft: number;
}

function DashboardPage() {
  const { user } = useAuth();

  // Fetch trips and driver status
  const {
    data: tripsResponse,
    isLoading: tripsLoading,
    isError: tripsError,
    error: tripsErrorMsg,
    refetch: refetchTrips,
  } = useMyTrips();

  const {
    data: statusResponse,
    isLoading: statusLoading,
    isError: statusError,
    refetch: refetchStatus,
  } = useCurrentDriverStatus();

  const trips = useMemo(() => {
    return tripsResponse?.trips || [];
  }, [tripsResponse?.trips]);

  const driverStatus = useMemo(() => {
    return tripsResponse?.driver_status || statusResponse?.current_status;
  }, [tripsResponse?.driver_status, statusResponse?.current_status]);

  // Calculate dashboard statistics
  const dashboardStats = useMemo((): DashboardStats => {
    // Find active trip
    const activeTrip = trips.find(
      (trip: TripListItem) => trip.status === "in_progress"
    );

    // Count trips by status
    const today = new Date().toDateString();
    const completedToday = trips.filter((trip: TripListItem) => {
      const tripDate = new Date(trip.departure_datetime).toDateString();
      return tripDate === today && trip.status === "completed";
    }).length;

    const inProgress = trips.filter(
      (trip) => trip.status === "in_progress"
    ).length;
    const planned = trips.filter((trip) => trip.status === "Planned").length;

    // Calculate next break time if needed
    let nextBreakTime = null;
    if (driverStatus && driverStatus.current_duty_status === "driving") {
      const hoursUntilBreak = Math.max(
        0,
        8 - (driverStatus.today_driving_hours % 8)
      );
      if (hoursUntilBreak < 2) {
        const breakTime = new Date();
        breakTime.setHours(breakTime.getHours() + hoursUntilBreak);
        nextBreakTime = breakTime.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
      }
    }

    return {
      activeTripId: activeTrip?.trip_id || null,
      totalTrips: trips.length,
      completedToday,
      inProgress,
      planned,
      hoursWorkedToday: driverStatus?.today_on_duty_hours || 0,
      nextBreakTime,
    };
  }, [trips, driverStatus]);

  const tripCounts = useMemo((): TripCounts => {
    return {
      total: trips.length,
      completed: trips.filter((trip) => trip.status === "completed").length,
      inProgress: trips.filter((trip) => trip.status === "in_progress").length,
      planned: trips.filter((trip) => trip.status === "Planned").length,
      draft: trips.filter((trip) => trip.status === "draft").length,
    };
  }, [trips]);

  const recentTrips = useMemo(() => {
    return trips
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      .slice(0, 5);
  }, [trips]);

  const handleRefreshAll = () => {
    refetchTrips();
    refetchStatus();
  };

  const formatDateTime = (dateTimeString: string): string => {
    return new Date(dateTimeString).toLocaleDateString();
  };

  // Loading state
  if (tripsLoading || statusLoading) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex items-center justify-center h-[100vh] md:h-[80vh] lg:landscape:h-[80vh]">
            <LoadingSpinner size="large" />
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <>
      <SEO
        title="Driver Dashboard"
        description={`Driver dashboard for ${
          user?.first_name || user?.username
        }. View HOS status, manage trips, and track compliance in real-time.`}
        keywords="driver dashboard, HOS status, trip management, hours of service, compliance tracking"
        noIndex={true}
      />
      <Layout>
        <motion.div
          className="w-full pb-[10%] xl:pb-0 mt-[17%] md:mt-4 space-y-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 25,
            duration: 1,
          }}
        >
          <div className="w-full mt-[17%] md:mt-4 space-y-6">
            {/* Header */}
            <div className="grid gap-y-4 items-center justify-between">
              <div className="">
                <h1 className="text-2xl font-bold text-gray-900">
                  Welcome back, {user?.first_name || user?.username}
                </h1>
                <p className="text-gray-600 mt-1">
                  Here's your HOS status and trip overview for today
                </p>
              </div>
              <Link to="/trips/new" className="w-[10rem]">
                <Button
                  className="rounded-md"
                  leftIcon={<Plus className="w-4 h-4" />}
                >
                  Plan New Trip
                </Button>
              </Link>
            </div>

            {/* Current HOS Status */}
            <DriverStatusCard showActions={true} />

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-2">
              <Card>
                <CardContent className="p-2">
                  <div className="flex gap-4">
                    <Truck className="w-8 h-8 text-blue-600" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-600">
                        Active Trip
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {dashboardStats.activeTripId ? "1" : "0"}
                      </p>
                    </div>
                  </div>
                  {dashboardStats.activeTripId && (
                    <div className="mt-2">
                      <Link to={`/trips/${dashboardStats.activeTripId}`}>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-blue-600"
                        >
                          View Active Trip
                        </Button>
                      </Link>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardContent className="">
                  <div className="flex gap-4">
                    <Clock className="w-8 h-8 text-orange-600" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-600">
                        Hours Worked Today
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {dashboardStats.hoursWorkedToday.toFixed(1)}
                      </p>
                      <p className="text-xs text-gray-500">of 14 allowed</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="">
                  <div className="flex gap-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-600">
                        Completed Today
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {dashboardStats.completedToday}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="">
                <CardContent className="">
                  <div className="flex gap-4">
                    <Route className="w-8 h-8 text-purple-600" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-600">
                        Planned Trips
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {dashboardStats.planned}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Next Break Alert */}
            {dashboardStats.nextBreakTime && (
              <Card className="border-amber-200 bg-amber-50">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-3">
                    <AlertTriangle className="w-6 h-6 text-amber-600" />
                    <div>
                      <p className="font-medium text-amber-800">
                        Break Required Soon
                      </p>
                      <p className="text-sm text-amber-700">
                        Next 30-minute break required around{" "}
                        {dashboardStats.nextBreakTime}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 pb-10 lg:grid-cols-2 gap-6">
              {/* Recent Trips */}
              <Card className="max-h-[30rem] lg:max-h-[40rem] overflow-y-auto">
                <CardHeader>
                  <div className="flex items-center justify-between">
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
                      <Truck className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-500">No trips yet</p>
                      <Link to="/trips/new">
                        <Button className="mt-3 rounded-md" size="sm">
                          Plan Your First Trip
                        </Button>
                      </Link>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {recentTrips.map((trip) => (
                        <div
                          key={trip.trip_id}
                          className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {trip.pickup_address} → {trip.delivery_address}
                              </p>
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                  trip.status === "completed"
                                    ? "bg-green-100 text-green-800"
                                    : trip.status === "in_progress"
                                    ? "bg-yellow-100 text-yellow-800"
                                    : trip.status === "planned"
                                    ? "bg-blue-100 text-blue-800"
                                    : "bg-gray-100 text-gray-800"
                                }`}
                              >
                                {trip.status_display}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              <MapPin className="w-3 h-3 inline mr-1" />
                              {trip.total_distance_miles
                                ? `${Number(trip.total_distance_miles).toFixed(
                                    0
                                  )} mi`
                                : "Distance TBD"}
                              {trip.total_driving_time
                                ? ` • ${Number(trip.total_driving_time).toFixed(
                                    1
                                  )}h driving`
                                : ""}
                            </p>
                            <p className="text-xs text-gray-500">
                              Created {formatDateTime(trip.created_at)}
                            </p>
                          </div>
                          <div className="flex items-center space-x-2">
                            {!trip.is_hos_compliant && (
                              <AlertTriangle className="w-4 h-4 text-amber-500" />
                            )}
                            <Link to={`/trips/${trip.trip_id}`}>
                              <Button variant="ghost" size="sm">
                                View
                              </Button>
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Trip Summary & Actions */}
              <Card>
                <CardHeader>
                  <CardTitle>Trip Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Trip Status Grid */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <p className="text-sm text-gray-600">Total Trips</p>
                        <p className="text-xl font-bold text-gray-900">
                          {tripCounts.total}
                        </p>
                      </div>
                      <div className="bg-green-50 p-3 rounded-lg">
                        <p className="text-sm text-green-600">Completed</p>
                        <p className="text-xl font-bold text-green-900">
                          {tripCounts.completed}
                        </p>
                      </div>
                      <div className="bg-yellow-50 p-3 rounded-lg">
                        <p className="text-sm text-yellow-600">In Progress</p>
                        <p className="text-xl font-bold text-yellow-900">
                          {tripCounts.inProgress}
                        </p>
                      </div>
                      <div className="bg-blue-50 p-3 rounded-lg">
                        <p className="text-sm text-blue-600">Planned</p>
                        <p className="text-xl font-bold text-blue-900">
                          {tripCounts.planned}
                        </p>
                      </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="border-t pt-4">
                      <p className="text-sm font-medium text-gray-700 mb-3">
                        Quick Actions
                      </p>
                      <div className="space-y-2">
                        <Link to="/trips/new" className="block">
                          <Button
                            className="w-full rounded-md"
                            leftIcon={<Plus className="w-4 h-4" />}
                          >
                            Plan New Trip
                          </Button>
                        </Link>
                        <Link to="/trips" className="block">
                          <Button
                            variant="primary"
                            className="w-full rounded-md"
                            leftIcon={<Route className="w-4 h-4" />}
                          >
                            View All Trips
                          </Button>
                        </Link>
                        {dashboardStats.activeTripId && (
                          <Link
                            to={`/trips/${dashboardStats.activeTripId}`}
                            className="block"
                          >
                            <Button
                              variant="primary"
                              className="w-full rounded-md"
                              leftIcon={<Truck className="w-4 h-4" />}
                            >
                              View Active Trip
                            </Button>
                          </Link>
                        )}
                      </div>
                    </div>

                    {/* Today's Summary */}
                    <div className="border-t pt-4">
                      <h4 className="text-sm font-medium text-gray-900 mb-3">
                        Today's Summary
                      </h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Trips Completed</span>
                          <span className="font-medium text-gray-700">
                            {dashboardStats.completedToday}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Hours Worked</span>
                          <span className="font-medium text-gray-700">
                            {dashboardStats.hoursWorkedToday.toFixed(1)}h
                          </span>
                        </div>
                        {driverStatus && (
                          <>
                            <div className="flex justify-between">
                              <span className="text-gray-600">
                                Driving Hours
                              </span>
                              <span className="font-medium text-gray-700">
                                {driverStatus.today_driving_hours.toFixed(1)}h
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">HOS Status</span>
                              <span
                                className={`font-medium ${
                                  driverStatus.needs_immediate_break
                                    ? "text-red-600"
                                    : driverStatus.compliance_warnings.length >
                                      0
                                    ? "text-amber-600"
                                    : "text-green-600"
                                }`}
                              >
                                {driverStatus.needs_immediate_break
                                  ? "Break Required"
                                  : driverStatus.compliance_warnings.length > 0
                                  ? "Warnings"
                                  : "Compliant"}
                              </span>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Error States */}
            {(tripsError || statusError) && (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-medium text-red-800">
                        Error Loading Dashboard
                      </h4>
                      <p className="text-sm text-red-700 mt-1">
                        {tripsError &&
                          `Failed to load trips: ${tripsErrorMsg?.message}`}
                        {tripsError && statusError && " • "}
                        {statusError && `Failed to load HOS status`}
                      </p>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleRefreshAll}
                        className="mt-2 text-red-600 border-red-200 hover:bg-red-100"
                      >
                        Try Again
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </motion.div>
      </Layout>
    </>
  );
}

export default DashboardPage;
