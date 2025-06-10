/* eslint-disable @typescript-eslint/no-explicit-any */

import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Layout } from "../components/Layout/Layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/UI/Card";
import { Button } from "../components/UI/Button";
import {
  ArrowLeft,
  MapPin,
  Clock,
  Route,
  CheckCircle,
  AlertTriangle,
  Truck,
  FileText,
  Download,
  Edit,
  Play,
  //   Pause,
  Square,
} from "lucide-react";

export function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const [activeTab, setActiveTab] = useState<
    "overview" | "stops" | "hos" | "compliance"
  >("overview");

  // Mock trip data - will be replaced with TanStack Query API call
  const trip = {
    trip_id: tripId,
    current_address: "Dallas, TX 75201",
    destination_address: "Houston, TX 77002",
    departure_datetime: "2024-01-16T06:00:00Z",
    estimated_arrival_time: "2024-01-16T10:30:00Z",
    total_distance_miles: 245,
    total_driving_time: 4.5,
    status: "planned",
    status_display: "Planned",
    is_hos_compliant: true,
    driver_name: "John Doe",
    vehicle_info: {
      unit_number: "Unit-001",
      year: 2023,
      make: "Freightliner",
      model: "Cascadia",
    },
    stops: [
      {
        id: 1,
        stop_type: "pickup",
        stop_type_display: "Pickup",
        sequence_order: 1,
        address: "Dallas, TX 75201",
        arrival_time: "2024-01-16T06:00:00Z",
        departure_time: "2024-01-16T07:00:00Z",
        duration_minutes: 60,
        distance_from_origin_miles: 0,
        is_required_for_compliance: false,
      },
      {
        id: 2,
        stop_type: "fuel",
        stop_type_display: "Fuel Stop",
        sequence_order: 2,
        address: "Huntsville, TX 77340",
        arrival_time: "2024-01-16T08:30:00Z",
        departure_time: "2024-01-16T09:15:00Z",
        duration_minutes: 45,
        distance_from_origin_miles: 120,
        is_required_for_compliance: false,
      },
      {
        id: 3,
        stop_type: "delivery",
        stop_type_display: "Delivery",
        sequence_order: 3,
        address: "Houston, TX 77002",
        arrival_time: "2024-01-16T10:30:00Z",
        departure_time: "2024-01-16T11:30:00Z",
        duration_minutes: 60,
        distance_from_origin_miles: 245,
        is_required_for_compliance: false,
      },
    ],
    hos_periods: [
      {
        id: 1,
        duty_status: "on_duty_not_driving",
        duty_status_display: "On Duty (Not Driving)",
        start_datetime: "2024-01-16T06:00:00Z",
        end_datetime: "2024-01-16T07:00:00Z",
        duration_minutes: 60,
        duration_hours: 1,
        start_location: "Dallas, TX",
        is_compliant: true,
      },
      {
        id: 2,
        duty_status: "driving",
        duty_status_display: "Driving",
        start_datetime: "2024-01-16T07:00:00Z",
        end_datetime: "2024-01-16T08:30:00Z",
        duration_minutes: 90,
        duration_hours: 1.5,
        distance_traveled_miles: 120,
        is_compliant: true,
      },
    ],
    compliance_summary: {
      is_compliant: true,
      score: 95,
      violations_count: 0,
    },
  };

  const getStatusBadge = (status: string, isCompliant: boolean) => {
    const baseClasses =
      "inline-flex items-center px-3 py-1 rounded-full text-sm font-medium";

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

  const tabs = [
    { id: "overview", label: "Overview", icon: Route },
    { id: "stops", label: "Stops", icon: MapPin },
    { id: "hos", label: "HOS Periods", icon: Clock },
    { id: "compliance", label: "Compliance", icon: CheckCircle },
  ];

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link to="/trips">
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<ArrowLeft className="w-4 h-4" />}
              >
                Back to Trips
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {trip.current_address} → {trip.destination_address}
              </h1>
              <p className="text-gray-600">Trip ID: {trip.trip_id}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {trip.status === "planned" && (
              <Button leftIcon={<Play className="w-4 h-4" />}>
                Start Trip
              </Button>
            )}
            {trip.status === "in_progress" && (
              <Button
                variant="danger"
                leftIcon={<Square className="w-4 h-4" />}
              >
                End Trip
              </Button>
            )}
            {trip.status === "draft" && (
              <Link to={`/trips/${tripId}/edit`}>
                <Button leftIcon={<Edit className="w-4 h-4" />}>
                  Edit Trip
                </Button>
              </Link>
            )}
            <Button
              variant="secondary"
              leftIcon={<Download className="w-4 h-4" />}
            >
              Export ELD
            </Button>
          </div>
        </div>

        {/* Trip Status Card */}
        <Card>
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Route className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Status</p>
                  <span
                    className={getStatusBadge(
                      trip.status,
                      trip.is_hos_compliant
                    )}
                  >
                    {trip.status_display}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">HOS Compliance</p>
                  <p
                    className={`font-medium ${
                      trip.is_hos_compliant ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {trip.is_hos_compliant ? "Compliant" : "Non-Compliant"}
                  </p>
                  <p className="text-xs text-gray-500">
                    Score: {trip.compliance_summary.score}%
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Duration</p>
                  <p className="font-medium">{trip.total_driving_time} hours</p>
                  <p className="text-xs text-gray-500">
                    {trip.total_distance_miles} miles
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Truck className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Vehicle</p>
                  <p className="font-medium">{trip.vehicle_info.unit_number}</p>
                  <p className="text-xs text-gray-500">
                    {trip.vehicle_info.year} {trip.vehicle_info.make}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Trip Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Departure</p>
                    <p className="font-medium">
                      {new Date(trip.departure_datetime).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Estimated Arrival</p>
                    <p className="font-medium">
                      {trip.estimated_arrival_time
                        ? new Date(trip.estimated_arrival_time).toLocaleString()
                        : "Not calculated"}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Total Distance</p>
                    <p className="font-medium">
                      {trip.total_distance_miles} miles
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Driving Time</p>
                    <p className="font-medium">
                      {trip.total_driving_time} hours
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Driver</p>
                    <p className="font-medium">{trip.driver_name}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Total Stops</p>
                    <p className="font-medium">{trip.stops.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Route Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    </div>
                    <div>
                      <p className="font-medium">{trip.current_address}</p>
                      <p className="text-sm text-gray-600">Origin</p>
                    </div>
                  </div>

                  {trip.stops
                    .filter(
                      (s) =>
                        s.stop_type !== "pickup" && s.stop_type !== "delivery"
                    )
                    .map((stop, index) => (
                      <div
                        key={stop.id}
                        className="flex items-center space-x-3"
                      >
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                        </div>
                        <div>
                          <p className="font-medium">{stop.address}</p>
                          <p className="text-sm text-gray-600">
                            {stop.stop_type_display}
                          </p>
                        </div>
                      </div>
                    ))}

                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                      <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    </div>
                    <div>
                      <p className="font-medium">{trip.destination_address}</p>
                      <p className="text-sm text-gray-600">Destination</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "stops" && (
          <Card>
            <CardHeader>
              <CardTitle>Trip Stops ({trip.stops.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {trip.stops.map((stop) => (
                  <div
                    key={stop.id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <span className="text-sm font-bold text-blue-600">
                          {stop.sequence_order}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium">{stop.address}</p>
                        <p className="text-sm text-gray-600">
                          {stop.stop_type_display}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">
                        {new Date(stop.arrival_time).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}{" "}
                        -
                        {new Date(stop.departure_time).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                      <p className="text-sm text-gray-500">
                        {stop.duration_minutes} minutes
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "hos" && (
          <Card>
            <CardHeader>
              <CardTitle>
                HOS Duty Periods ({trip.hos_periods.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {trip.hos_periods.map((period) => (
                  <div
                    key={period.id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-4">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          period.duty_status === "driving"
                            ? "bg-red-100"
                            : period.duty_status === "on_duty_not_driving"
                            ? "bg-blue-100"
                            : period.duty_status === "off_duty"
                            ? "bg-green-100"
                            : "bg-gray-100"
                        }`}
                      >
                        <Clock
                          className={`w-5 h-5 ${
                            period.duty_status === "driving"
                              ? "text-red-600"
                              : period.duty_status === "on_duty_not_driving"
                              ? "text-blue-600"
                              : period.duty_status === "off_duty"
                              ? "text-green-600"
                              : "text-gray-600"
                          }`}
                        />
                      </div>
                      <div>
                        <p className="font-medium">
                          {period.duty_status_display}
                        </p>
                        <p className="text-sm text-gray-600">
                          {period.start_location}
                        </p>
                        {period.distance_traveled_miles && (
                          <p className="text-sm text-gray-500">
                            {period.distance_traveled_miles} miles
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">
                        {new Date(period.start_datetime).toLocaleTimeString(
                          [],
                          { hour: "2-digit", minute: "2-digit" }
                        )}{" "}
                        -
                        {new Date(period.end_datetime).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                      <p className="text-sm text-gray-500">
                        {period.duration_hours} hours
                      </p>
                      <div className="flex items-center justify-end space-x-1 mt-1">
                        {period.is_compliant ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                        )}
                        <span
                          className={`text-xs ${
                            period.is_compliant
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          {period.is_compliant ? "Compliant" : "Violation"}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "compliance" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <CheckCircle className="w-5 h-5 mr-2" />
                  Compliance Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div>
                      <p className="font-medium text-green-800">
                        Overall Status
                      </p>
                      <p className="text-sm text-green-600">HOS Compliant</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-green-600">
                        {trip.compliance_summary.score}%
                      </p>
                      <p className="text-sm text-green-600">Score</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">
                        Total Driving Hours
                      </span>
                      <span className="font-medium">
                        {trip.total_driving_time} / 11 hours
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">
                        Total On-Duty Hours
                      </span>
                      <span className="font-medium">5.5 / 14 hours</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">
                        Required Breaks
                      </span>
                      <span className="font-medium">0 / 0</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Violations</span>
                      <span className="font-medium text-green-600">
                        {trip.compliance_summary.violations_count}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <FileText className="w-5 h-5 mr-2" />
                  Compliance Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full justify-start" variant="ghost">
                  <Download className="w-4 h-4 mr-2" />
                  Download ELD Logs
                </Button>

                <Button className="w-full justify-start" variant="ghost">
                  <FileText className="w-4 h-4 mr-2" />
                  Generate Compliance Report
                </Button>

                <Button className="w-full justify-start" variant="ghost">
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Validate HOS Compliance
                </Button>

                <div className="pt-3 border-t border-gray-200">
                  <p className="text-sm text-gray-600 mb-2">
                    Next Required Action:
                  </p>
                  <p className="text-sm font-medium text-green-600">
                    ✓ No immediate actions required
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </Layout>
  );
}
