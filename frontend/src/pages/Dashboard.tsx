import { useAuth } from "../hooks/useAuth";
import { Layout } from "../components/Layout/Layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/UI/Card";
import { Button } from "../components/UI/Button";
import {
  Route,
  Clock,
  CheckCircle,
  AlertTriangle,
  Plus,
  Truck,
  MapPin,
} from "lucide-react";
import { Link } from "react-router-dom";

export function DashboardPage() {
  const { user } = useAuth();

  // Mock data - will be replaced with real API calls
  const todayStats = {
    drivingHours: 3.5,
    maxDrivingHours: 11,
    onDutyHours: 5.2,
    maxOnDutyHours: 14,
    isCompliant: true,
    nextBreakRequired: "2:30 PM",
  };

  const recentTrips = [
    {
      id: "1",
      origin: "Dallas, TX",
      destination: "Houston, TX",
      status: "completed",
      departureTime: "2024-01-15T08:00:00Z",
      isCompliant: true,
    },
    {
      id: "2",
      origin: "Houston, TX",
      destination: "Austin, TX",
      status: "in_progress",
      departureTime: "2024-01-16T06:00:00Z",
      isCompliant: true,
    },
  ];

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
                    {todayStats.drivingHours} / {todayStats.maxDrivingHours}
                  </p>
                  <p className="text-sm text-gray-500">
                    {todayStats.maxDrivingHours - todayStats.drivingHours} hours
                    remaining
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
                    {todayStats.onDutyHours} / {todayStats.maxOnDutyHours}
                  </p>
                  <p className="text-sm text-gray-500">
                    {todayStats.maxOnDutyHours - todayStats.onDutyHours} hours
                    remaining
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
                      todayStats.isCompliant ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {todayStats.isCompliant ? "Compliant" : "Violation"}
                  </p>
                  <p className="text-sm text-gray-500">Current status</p>
                </div>
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    todayStats.isCompliant ? "bg-green-100" : "bg-red-100"
                  }`}
                >
                  {todayStats.isCompliant ? (
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
                    {todayStats.nextBreakRequired}
                  </p>
                  <p className="text-sm text-gray-500">30-min break required</p>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Trips */}
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
              <div className="space-y-4">
                {recentTrips.map((trip) => (
                  <div
                    key={trip.id}
                    className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Route className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {trip.origin} → {trip.destination}
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(trip.departureTime).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          trip.status === "completed"
                            ? "bg-green-100 text-green-800"
                            : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {trip.status === "completed"
                          ? "Completed"
                          : "In Progress"}
                      </span>
                      {trip.isCompliant && (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
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

                <Link to="/profile" className="block">
                  <Button className="w-full justify-start" variant="ghost">
                    <MapPin className="w-4 h-4 mr-2" />
                    Update Profile
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
