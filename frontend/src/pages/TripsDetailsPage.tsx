import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
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
  Square,
  Calculator,
  RefreshCw,
  AlertCircle,
  Trash2,
  Settings,
} from "lucide-react";
import {
  useGetTripDetails,
  useGetTripComplianceReport,
  useDeleteTrip,
} from "../hooks/useTripQueries";
import { useTripCalculation } from "../hooks/useTripCalculation";
import { useELDLogs } from "../hooks/useELDLogs";
import { ELDLogViewer } from "../components/ELDLogs/ELDLogViewer";


type TabType = "overview" | "stops" | "hos" | "compliance" | "eld_logs";

export function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>("overview");

  const {
    data: tripResponse,
    isLoading: isTripLoading,
    isError: isTripError,
    error: tripError,
    refetch: refetchTrip,
  } = useGetTripDetails(tripId);

  const { data: complianceResponse, isLoading: isComplianceLoading } =
    useGetTripComplianceReport(tripId);

  const deleteTrip = useDeleteTrip();

  const {
    calculateRoute,
    optimizeRoute,
    isCalculating,
    isOptimizing,
    calculationError,
    optimizationError,
    clearErrors,
  } = useTripCalculation(tripId!, {
    onCalculationSuccess: () => {
      refetchTrip();
    },
    onOptimizationSuccess: () => {
      refetchTrip();
    },
  });

  const {
    eldData,
    isLoading: isELDLoading,
    error: eldError,
    generateLogs,
    downloadPDF,
    clearError: clearELDError,
  } = useELDLogs(tripId!, {
    onSuccess: () => {
      console.log("ELD logs generated successfully");
    },
    onError: (error) => {
      console.error("ELD generation error:", error);
    },
  });

  const trip = tripResponse?.trip;
  const complianceReport = complianceResponse?.compliance_report;

  const getStatusBadge = (status: string) => {
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

  const formatDateTime = (dateTimeString: string): string => {
    return new Date(dateTimeString).toLocaleString();
  };

  const formatTime = (dateTimeString: string): string => {
    return new Date(dateTimeString).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleCalculateRoute = async () => {
    clearErrors();
    try {
      await calculateRoute({
        optimize_route: true,
        generate_eld_logs: false,
        include_fuel_optimization: true,
      });
    } catch (error) {
      console.error("Error calculating route:", error);
    }
  };

  const handleOptimizeRoute = async () => {
    clearErrors();
    try {
      await optimizeRoute({
        optimize_breaks: true,
        optimize_fuel_stops: true,
        optimize_daily_resets: true,
      });
    } catch (error) {
      console.error("Error optimizing route:", error);
    }
  };

  const handleGenerateELD = async () => {
    clearELDError();
    try {
      const result = await generateLogs({
        export_format: "json",
        include_validation: true,
      });

      if (result?.success) {
        console.log("ELD logs generated successfully");
      }
    } catch (error) {
      console.error("Error generating ELD logs:", error);
    }
  };

  const handleDownloadELD = async () => {
    try {
      await downloadPDF();
    } catch (error) {
      console.error("Error downloading ELD PDF:", error);
    }
  };

  const handleDeleteTrip = async () => {
    if (!trip) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete this trip? This action cannot be undone.`
    );

    if (confirmed) {
      try {
        await deleteTrip.mutateAsync(trip.trip_id);
        navigate("/trips");
      } catch (error) {
        console.error("Failed to delete trip:", error);
      }
    }
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: Route },
    { id: "stops", label: "Stops", icon: MapPin },
    { id: "hos", label: "HOS Periods", icon: Clock },
    { id: "compliance", label: "Compliance", icon: CheckCircle },
    { id: "eld_logs", label: "ELD Logs", icon: FileText },
  ] as const;

  // Loading state
  if (isTripLoading) {
    return (
      <Layout>
        <div className="space-y-6">
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
                Loading Trip...
              </h1>
            </div>
          </div>

          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="large" text="Loading trip details..." />
          </div>
        </div>
      </Layout>
    );
  }

  // Error state
  if (isTripError || !trip) {
    return (
      <Layout>
        <div className="space-y-6">
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
                Trip Not Found
              </h1>
            </div>
          </div>

          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <AlertCircle className="w-8 h-8 text-red-600" />
                <div>
                  <h3 className="text-lg font-medium text-red-800">
                    Failed to Load Trip
                  </h3>
                  <p className="text-red-700 mt-1">
                    {tripError instanceof Error
                      ? tripError.message
                      : "The requested trip could not be found or loaded."}
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => refetchTrip()}
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
                {trip.pickup_address} → {trip.delivery_address}
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
              onClick={handleGenerateELD}
              isLoading={isELDLoading}
              disabled={isELDLoading || !trip.hos_periods.length}
            >
              {eldData ? "Refresh ELD" : "Generate ELD"}
            </Button>
          </div>
        </div>

        {/* Error Messages */}
        {(calculationError || optimizationError || eldError) && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-medium text-red-800">Operation Failed</h4>
                  {calculationError && (
                    <p className="text-sm text-red-700 mt-1">
                      Route Calculation: {calculationError}
                    </p>
                  )}
                  {optimizationError && (
                    <p className="text-sm text-red-700 mt-1">
                      Route Optimization: {optimizationError}
                    </p>
                  )}
                  {eldError && (
                    <p className="text-sm text-red-700 mt-1">
                      ELD Generation: {eldError}
                    </p>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      clearErrors();
                      clearELDError();
                    }}
                    className="mt-2 text-red-700 hover:text-red-800"
                  >
                    Dismiss
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Trip Actions Card */}
        {trip.is_editable && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Settings className="w-5 h-5 mr-2" />
                Trip Actions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                <Button
                  leftIcon={<Calculator className="w-4 h-4" />}
                  onClick={handleCalculateRoute}
                  isLoading={isCalculating}
                  disabled={isCalculating || isOptimizing}
                >
                  {isCalculating ? "Calculating..." : "Calculate Route"}
                </Button>

                {trip.hos_periods.length > 0 && (
                  <Button
                    variant="secondary"
                    leftIcon={<RefreshCw className="w-4 h-4" />}
                    onClick={handleOptimizeRoute}
                    isLoading={isOptimizing}
                    disabled={isCalculating || isOptimizing}
                  >
                    {isOptimizing ? "Optimizing..." : "Optimize Route"}
                  </Button>
                )}

                {trip.status === "draft" && (
                  <Button
                    variant="danger"
                    leftIcon={<Trash2 className="w-4 h-4" />}
                    onClick={handleDeleteTrip}
                    isLoading={deleteTrip.isPending}
                    disabled={deleteTrip.isPending}
                  >
                    {deleteTrip.isPending ? "Deleting..." : "Delete Trip"}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

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
                  <span className={getStatusBadge(trip.status)}>
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
                  <p className="font-medium">
                    {trip.total_driving_time
                      ? `${trip.total_driving_time} hours`
                      : "Not calculated"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {trip.total_distance_miles
                      ? `${trip.total_distance_miles} miles`
                      : "Not calculated"}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Truck className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Vehicle</p>
                  <p className="font-medium">
                    {trip.vehicle_info?.unit_number || "No vehicle assigned"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {trip.vehicle_info
                      ? `${trip.vehicle_info.year} ${trip.vehicle_info.make}`
                      : ""}
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
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.id === "eld_logs" && eldData && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    ✓
                  </span>
                )}
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
                      {formatDateTime(trip.departure_datetime)}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Estimated Arrival</p>
                    <p className="font-medium">
                      {trip.estimated_arrival_time
                        ? formatDateTime(trip.estimated_arrival_time)
                        : "Not calculated"}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Total Distance</p>
                    <p className="font-medium">
                      {trip.total_distance_miles
                        ? `${trip.total_distance_miles} miles`
                        : "Not calculated"}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Driving Time</p>
                    <p className="font-medium">
                      {trip.total_driving_time
                        ? `${trip.total_driving_time} hours`
                        : "Not calculated"}
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
                {trip.stops.length === 0 ? (
                  <div className="text-center py-8">
                    <Route className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">No route calculated yet</p>
                    <p className="text-sm text-gray-500">
                      Calculate route to see stops and details
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Current Location */}
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                      </div>
                      <div className="flex-1">
                        <p className="font-medium">{trip.current_address}</p>
                        <p className="text-sm text-gray-600">
                          Current Location
                        </p>
                      </div>
                      {trip.deadhead_distance_miles && (
                        <div className="text-right text-sm text-gray-500">
                          <p>{trip.deadhead_distance_miles} mi</p>
                          <p>{trip.deadhead_driving_time}h</p>
                        </div>
                      )}
                    </div>

                    {/* Deadhead stops */}
                    {trip.stops
                      .filter((s) => s.leg_type === "deadhead")
                      .map((stop) => (
                        <div
                          key={stop.id}
                          className="flex items-center space-x-3 ml-4"
                        >
                          <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center">
                            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                          </div>
                          <div>
                            <p className="font-medium text-sm">
                              {stop.address}
                            </p>
                            <p className="text-xs text-gray-600">
                              {stop.stop_type_display}
                            </p>
                          </div>
                        </div>
                      ))}

                    {/* Pickup Location */}
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      </div>
                      <div className="flex-1">
                        <p className="font-medium">{trip.pickup_address}</p>
                        <p className="text-sm text-gray-600">Pickup Location</p>
                      </div>
                      {trip.loaded_distance_miles && (
                        <div className="text-right text-sm text-gray-500">
                          <p>{trip.loaded_distance_miles} mi</p>
                          <p>{trip.loaded_driving_time}h</p>
                        </div>
                      )}
                    </div>

                    {/* Loaded leg stops */}
                    {trip.stops
                      .filter((s) => s.leg_type === "loaded")
                      .map((stop) => (
                        <div
                          key={stop.id}
                          className="flex items-center space-x-3 ml-4"
                        >
                          <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center">
                            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                          </div>
                          <div>
                            <p className="font-medium text-sm">
                              {stop.address}
                            </p>
                            <p className="text-xs text-gray-600">
                              {stop.stop_type_display}
                            </p>
                          </div>
                        </div>
                      ))}

                    {/* Delivery Location */}
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                        <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                      </div>
                      <div>
                        <p className="font-medium">{trip.delivery_address}</p>
                        <p className="text-sm text-gray-600">
                          Delivery Location
                        </p>
                      </div>
                    </div>
                  </div>
                )}
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
              {trip.stops.length === 0 ? (
                <div className="text-center py-8">
                  <MapPin className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No stops planned yet</p>
                  <p className="text-sm text-gray-500">
                    Calculate route to generate stops
                  </p>
                </div>
              ) : (
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
                          {stop.is_required_for_compliance && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 mt-1">
                              Required for HOS
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">
                          {formatTime(stop.arrival_time)} -{" "}
                          {formatTime(stop.departure_time)}
                        </p>
                        <p className="text-sm text-gray-500">
                          {stop.duration_minutes} minutes
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {Math.round(stop.distance_from_origin_miles)} miles
                          from origin
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
              {trip.hos_periods.length === 0 ? (
                <div className="text-center py-8">
                  <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No HOS periods generated yet</p>
                  <p className="text-sm text-gray-500">
                    Calculate route to generate HOS periods
                  </p>
                </div>
              ) : (
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
                          {formatTime(period.start_datetime)} -{" "}
                          {formatTime(period.end_datetime)}
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
              )}
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
                {isComplianceLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <LoadingSpinner
                      size="medium"
                      text="Loading compliance data..."
                    />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div
                      className={`flex items-center justify-between p-3 rounded-lg ${
                        trip.is_hos_compliant ? "bg-green-50" : "bg-red-50"
                      }`}
                    >
                      <div>
                        <p
                          className={`font-medium ${
                            trip.is_hos_compliant
                              ? "text-green-800"
                              : "text-red-800"
                          }`}
                        >
                          Overall Status
                        </p>
                        <p
                          className={`text-sm ${
                            trip.is_hos_compliant
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          {trip.is_hos_compliant
                            ? "HOS Compliant"
                            : "HOS Non-Compliant"}
                        </p>
                      </div>
                      <div className="text-right">
                        <p
                          className={`text-2xl font-bold ${
                            trip.is_hos_compliant
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          {trip.compliance_summary.score}%
                        </p>
                        <p
                          className={`text-sm ${
                            trip.is_hos_compliant
                              ? "text-green-600"
                              : "text-red-600"
                          }`}
                        >
                          Score
                        </p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">
                          Total Driving Hours
                        </span>
                        <span className="font-medium">
                          {trip.total_driving_time
                            ? `${trip.total_driving_time} / 11 hours`
                            : "Not calculated"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">
                          Total On-Duty Hours
                        </span>
                        <span className="font-medium">
                          {complianceReport?.total_on_duty_hours
                            ? `${complianceReport.total_on_duty_hours} / 14 hours`
                            : "Not calculated"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">
                          Required Breaks
                        </span>
                        <span className="font-medium">
                          {complianceReport
                            ? `${complianceReport.scheduled_30min_breaks} / ${complianceReport.required_30min_breaks}`
                            : "Not calculated"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">
                          Violations
                        </span>
                        <span
                          className={`font-medium ${
                            trip.compliance_summary.violations_count > 0
                              ? "text-red-600"
                              : "text-green-600"
                          }`}
                        >
                          {trip.compliance_summary.violations_count}
                        </span>
                      </div>
                    </div>

                    {complianceReport &&
                      complianceReport.violations.length > 0 && (
                        <div className="mt-4 p-3 bg-red-50 rounded-lg">
                          <h4 className="font-medium text-red-800 mb-2">
                            Violations Found
                          </h4>
                          <ul className="space-y-1">
                            {complianceReport.violations.map(
                              (violation, index) => (
                                <li
                                  key={index}
                                  className="text-sm text-red-700"
                                >
                                  • {violation.description}
                                </li>
                              )
                            )}
                          </ul>
                        </div>
                      )}

                    {complianceReport &&
                      complianceReport.warnings.length > 0 && (
                        <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                          <h4 className="font-medium text-yellow-800 mb-2">
                            Warnings
                          </h4>
                          <ul className="space-y-1">
                            {complianceReport.warnings.map((warning, index) => (
                              <li
                                key={index}
                                className="text-sm text-yellow-700"
                              >
                                • {warning.message}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                  </div>
                )}
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
                <Button
                  className="w-full justify-start"
                  variant="ghost"
                  onClick={handleGenerateELD}
                  isLoading={isELDLoading}
                  disabled={isELDLoading || !trip.hos_periods.length}
                >
                  <Download className="w-4 h-4 mr-2" />
                  {isELDLoading ? "Generating..." : "Download ELD Logs"}
                </Button>

                <Button
                  className="w-full justify-start"
                  variant="ghost"
                  onClick={() => {
                    // This would open a compliance report modal or navigate to report page
                    console.log("Generate compliance report");
                  }}
                  disabled={!complianceReport}
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Generate Compliance Report
                </Button>

                <Button
                  className="w-full justify-start"
                  variant="ghost"
                  onClick={() => {
                    // This would trigger a compliance validation
                    refetchTrip();
                  }}
                  disabled={!trip.hos_periods.length}
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Validate HOS Compliance
                </Button>

                <div className="pt-3 border-t border-gray-200">
                  <p className="text-sm text-gray-600 mb-2">
                    Next Required Action:
                  </p>
                  {trip.is_hos_compliant ? (
                    <p className="text-sm font-medium text-green-600">
                      ✓ No immediate actions required
                    </p>
                  ) : (
                    <div className="space-y-1">
                      {complianceReport?.violations
                        .slice(0, 2)
                        .map((violation, index) => (
                          <p
                            key={index}
                            className="text-sm font-medium text-red-600"
                          >
                            ⚠ {violation.type.replace(/_/g, " ").toUpperCase()}
                          </p>
                        ))}
                      {complianceReport &&
                        complianceReport.violations.length > 2 && (
                          <p className="text-xs text-gray-500">
                            +{complianceReport.violations.length - 2} more
                            violations
                          </p>
                        )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "eld_logs" && (
          <div className="space-y-6">
            {/* Generate ELD Action */}
            {!eldData && trip.hos_periods.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <FileText className="w-5 h-5 mr-2" />
                    Generate ELD Logs
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-gray-600 mb-2">
                        Generate Electronic Logging Device (ELD) logs for this
                        trip.
                      </p>
                      <p className="text-sm text-gray-500">
                        This will create visual log sheets showing duty status
                        changes and compliance data.
                      </p>
                    </div>
                    <Button
                      leftIcon={<FileText className="w-4 h-4" />}
                      onClick={handleGenerateELD}
                      isLoading={isELDLoading}
                      disabled={isELDLoading}
                    >
                      {isELDLoading ? "Generating..." : "Generate ELD Logs"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <ELDLogViewer
              eldData={eldData}
              isLoading={isELDLoading}
              error={eldError}
              onDownload={handleDownloadELD}
              onRefresh={handleGenerateELD}
            />

            {trip.hos_periods.length === 0 && (
              <Card>
                <CardContent className="p-6">
                  <div className="text-center py-8">
                    <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      No HOS Data Available
                    </h3>
                    <p className="text-gray-600 mb-4">
                      Calculate the trip route first to generate HOS periods and
                      ELD logs.
                    </p>
                    <Button
                      leftIcon={<Calculator className="w-4 h-4" />}
                      onClick={handleCalculateRoute}
                      isLoading={isCalculating}
                      disabled={isCalculating}
                    >
                      Calculate Route
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
