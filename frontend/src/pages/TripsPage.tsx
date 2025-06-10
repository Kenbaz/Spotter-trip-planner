import { useState } from "react";
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
import {
  Plus,
//   Search,
  Route,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

export function TripsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Mock data - will be replaced with TanStack Query API calls
  const trips = [
    {
      trip_id: "550e8400-e29b-41d4-a716-446655440001",
      current_address: "Dallas, TX",
      destination_address: "Houston, TX",
      departure_datetime: "2024-01-15T08:00:00Z",
      estimated_arrival_time: "2024-01-15T12:30:00Z",
      total_distance_miles: 245,
      total_driving_time: 4.5,
      status: "completed",
      status_display: "Completed",
      is_hos_compliant: true,
      stops_count: 3,
      compliance_status: "Compliant",
      created_at: "2024-01-14T10:00:00Z",
    },
    {
      trip_id: "550e8400-e29b-41d4-a716-446655440002",
      current_address: "Houston, TX",
      destination_address: "Austin, TX",
      departure_datetime: "2024-01-16T06:00:00Z",
      estimated_arrival_time: "2024-01-16T09:15:00Z",
      total_distance_miles: 165,
      total_driving_time: 3.25,
      status: "in_progress",
      status_display: "In Progress",
      is_hos_compliant: true,
      stops_count: 2,
      compliance_status: "Compliant",
      created_at: "2024-01-15T14:30:00Z",
    },
    {
      trip_id: "550e8400-e29b-41d4-a716-446655440003",
      current_address: "Austin, TX",
      destination_address: "San Antonio, TX",
      departure_datetime: "2024-01-17T07:00:00Z",
      estimated_arrival_time: "2024-01-17T08:45:00Z",
      total_distance_miles: 80,
      total_driving_time: 1.75,
      status: "planned",
      status_display: "Planned",
      is_hos_compliant: true,
      stops_count: 1,
      compliance_status: "Compliant",
      created_at: "2024-01-16T16:00:00Z",
    },
    {
      trip_id: "550e8400-e29b-41d4-a716-446655440004",
      current_address: "San Antonio, TX",
      destination_address: "El Paso, TX",
      departure_datetime: "2024-01-18T05:00:00Z",
      estimated_arrival_time: null,
      total_distance_miles: null,
      total_driving_time: null,
      status: "draft",
      status_display: "Draft",
      is_hos_compliant: false,
      stops_count: 0,
      compliance_status: "Not Analyzed",
      created_at: "2024-01-17T09:15:00Z",
    },
  ];

  const getStatusBadge = (status: string, isCompliant: boolean) => {
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

  const filteredTrips = trips.filter((trip) => {
    const matchesSearch =
      trip.current_address.toLowerCase().includes(searchTerm.toLowerCase()) ||
      trip.destination_address.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || trip.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
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

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Search by origin or destination..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                //   leftIcon={<Search className="w-4 h-4" />}
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
                  {trips.filter((t) => t.status === "completed").length}
                </p>
                <p className="text-sm text-gray-600">Completed</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">
                  {trips.filter((t) => t.status === "in_progress").length}
                </p>
                <p className="text-sm text-gray-600">In Progress</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">
                  {trips.filter((t) => t.status === "planned").length}
                </p>
                <p className="text-sm text-gray-600">Planned</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-600">
                  {trips.filter((t) => t.status === "draft").length}
                </p>
                <p className="text-sm text-gray-600">Draft</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trips List */}
        <Card>
          <CardHeader>
            <CardTitle>Trips ({filteredTrips.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {filteredTrips.length === 0 ? (
              <div className="text-center py-12">
                <Route className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No trips found
                </h3>
                <p className="text-gray-600 mb-4">
                  {searchTerm || statusFilter !== "all"
                    ? "Try adjusting your search or filter criteria."
                    : "Get started by planning your first trip."}
                </p>
                <Link to="/trips/new">
                  <Button>Plan New Trip</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredTrips.map((trip) => (
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
                            <div>
                              <p className="font-medium text-gray-900">
                                {trip.current_address} →{" "}
                                {trip.destination_address}
                              </p>
                              <div className="flex items-center space-x-4 text-sm text-gray-500">
                                <span>
                                  Departure:{" "}
                                  {new Date(
                                    trip.departure_datetime
                                  ).toLocaleDateString()}{" "}
                                  at{" "}
                                  {new Date(
                                    trip.departure_datetime
                                  ).toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </span>
                                {trip.total_distance_miles && (
                                  <span>{trip.total_distance_miles} miles</span>
                                )}
                                {trip.total_driving_time && (
                                  <span>{trip.total_driving_time} hours</span>
                                )}
                                <span>{trip.stops_count} stops</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Status and Compliance */}
                        <div className="flex items-center space-x-3">
                          <div className="text-right">
                            <span
                              className={getStatusBadge(
                                trip.status,
                                trip.is_hos_compliant
                              )}
                            >
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
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
