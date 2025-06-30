import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout/Layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/UI/Card";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { LoadingSpinner } from "../components/UI/LoadingSpinner";
import {
  Plus,
//   Search,
  Route,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { useMyTrips } from "../hooks/useTripQueries";
import type { TripListItem } from "../types";


interface TripStats {
  completed: number;
  inProgress: number;
  planned: number;
  draft: number;
  total: number;
}


export function TripsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Fetch trips data
  const {
    data: tripsResponse,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useMyTrips(statusFilter === "all" ? undefined : statusFilter);

  // Process trips data
  const trips = useMemo(() => {
    return tripsResponse?.trips || [];
  }, [tripsResponse?.trips]);

  const totalCount = tripsResponse?.count || 0;

  // Filter trips based on search term
  const filteredTrips = useMemo(() => {
    if (!searchTerm.trim()) {
      return trips;
    }

    const searchLower = searchTerm.toLowerCase();
    return trips.filter((trip) => 
      trip.current_address.toLowerCase().includes(searchLower) ||
      trip.pickup_address.toLowerCase().includes(searchLower) || trip.delivery_address.toLowerCase().includes(searchLower) ||
      trip.trip_id.toLowerCase().includes(searchLower)
    );
  }, [trips, searchTerm]);

  // Calculate trip stats
  const tripStats = useMemo((): TripStats => {
    return trips.reduce(
      (stats, trip) => {
        stats.total++;
        switch (trip.status) {
          case "completed":
            stats.completed++;
            break;
          case "in_progress":
            stats.inProgress++;
            break;
          case "planned":
            stats.planned++;
            break;
          case "draft":
            stats.draft++;
            break;
          default:
            break;
        }
        return stats;
      },
      { completed: 0, inProgress: 0, planned: 0, draft: 0, total: 0 }
    );
  }, [trips]);

  const getStatusBadge = (status: string) => {
    const baseClasses =
      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium";

    switch (status) {
      case "completed":
        return `${baseClasses} bg-green-100 text-green-800`;
      case "in_progress":
        return `${baseClasses} bg-blue-100 text-blue-800`;
      case "planned":
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      case "draft":
        return `${baseClasses} bg-gray-100 text-gray-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

  const formatDateTime = (
    dateTimeString: string
  ): { date: string; time: string } => {
    const date = new Date(dateTimeString);
    return {
      date: date.toLocaleDateString(),
      time: date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
  };

  const handleRefresh = () => {
    refetch();
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">My Trips</h1>
              <p className="text-gray-600">Manage and track your trips</p>
            </div>
            <Link to="/trips/new">
              <Button leftIcon={<Plus className="w-4 h-4" />}>
                Plan New Trip
              </Button>
            </Link>
          </div>

          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="large" text="Loading your trips..." />
          </div>
        </div>
      </Layout>
    );
  }

  if (isError) {
    return (
      <Layout>
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">My Trips</h1>
              <p className="text-gray-600">Manage and track your trips</p>
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
                    Failed to Load Trips
                  </h3>
                  <p className="text-red-700 mt-1">
                    {error instanceof Error
                      ? error.message
                      : "An unexpected error occurred"}
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleRefresh}
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
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Trips</h1>
            <p className="text-gray-600">
              Manage and track your trips ({totalCount} total)
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefetching}
              leftIcon={
                <RefreshCw
                  className={`w-4 h-4 ${isRefetching ? "animate-spin" : ""}`}
                />
              }
            >
              Refresh
            </Button>
            <Link to="/trips/new">
              <Button leftIcon={<Plus className="w-4 h-4" />}>
                Plan New Trip
              </Button>
            </Link>
          </div>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Search by origin, destination, or trip ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              <div className="sm:w-48">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="draft">Draft</option>
                  <option value="planned">Planned</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Trip Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900">
                  {tripStats.completed}
                </p>
                <p className="text-sm text-gray-600">Completed</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">
                  {tripStats.inProgress}
                </p>
                <p className="text-sm text-gray-600">In Progress</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">
                  {tripStats.planned}
                </p>
                <p className="text-sm text-gray-600">Planned</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-600">
                  {tripStats.draft}
                </p>
                <p className="text-sm text-gray-600">Draft</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trips List */}
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>
                Trips ({filteredTrips.length}
                {searchTerm && ` of ${trips.length}`})
              </CardTitle>
              {isRefetching && <LoadingSpinner size="small" />}
            </div>
          </CardHeader>
          <CardContent>
            {filteredTrips.length === 0 ? (
              <div className="text-center py-12">
                <Route className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {trips.length === 0 ? "No trips found" : "No matching trips"}
                </h3>
                <p className="text-gray-600 mb-4">
                  {trips.length === 0
                    ? "Get started by planning your first trip."
                    : searchTerm || statusFilter !== "all"
                    ? "Try adjusting your search or filter criteria."
                    : "No trips match your current filters."}
                </p>
                {trips.length === 0 && (
                  <Link to="/trips/new">
                    <Button>Plan New Trip</Button>
                  </Link>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {filteredTrips.map((trip: TripListItem) => {
                  const departure = formatDateTime(trip.departure_datetime);
                  const estimatedArrival = trip.estimated_arrival_time
                    ? formatDateTime(trip.estimated_arrival_time)
                    : null;

                  return (
                    <Link
                      key={trip.trip_id}
                      to={`/trips/${trip.trip_id}`}
                      className="block hover:bg-gray-50 rounded-lg transition-colors"
                    >
                      <div className="p-4 border border-gray-200 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            {/* Route Info */}
                            <div className="flex items-center space-x-3 mb-2">
                              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                                <Route className="w-4 h-4 text-blue-600" />
                              </div>
                              <div className="flex-1">
                                <p className="font-medium text-gray-900">
                                  {trip.current_address} → {trip.pickup_address}{" "}
                                  → {trip.delivery_address}
                                </p>
                                <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                                  <span className="text-gray-900">
                                    Departure: {departure.date} at{" "}
                                    {departure.time}
                                  </span>
                                  {trip.total_distance_miles && (
                                    <span className="text-gray-900">
                                      {trip.total_distance_miles} miles
                                    </span>
                                  )}
                                  {trip.total_driving_time && (
                                    <span className="text-gray-900">
                                      {trip.total_driving_time} hours
                                    </span>
                                  )}
                                  <span className="text-gray-900">
                                    {trip.stops_count} stops
                                  </span>
                                  {estimatedArrival && (
                                    <span className="text-gray-900">
                                      ETA: {estimatedArrival.date} at{" "}
                                      {estimatedArrival.time}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Status and Compliance */}
                          <div className="flex items-center space-x-3">
                            <div className="text-right">
                              <span className={getStatusBadge(trip.status)}>
                                {trip.status_display}
                              </span>
                              <div className="flex items-center justify-end space-x-1 mt-1">
                                {trip.is_hos_compliant ? (
                                  <>
                                    <CheckCircle className="w-4 h-4 text-green-500" />
                                    <span className="text-sm text-green-600">
                                      Compliant
                                    </span>
                                  </>
                                ) : (
                                  <>
                                    <AlertTriangle className="w-4 h-4 text-yellow-500" />
                                    <span className="text-sm text-yellow-600">
                                      {trip.compliance_status}
                                    </span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Trip ID for reference */}
                        <div className="mt-2 pt-2 border-t border-gray-100">
                          <p className="text-xs text-gray-400">
                            Trip ID: {trip.trip_id}
                          </p>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
