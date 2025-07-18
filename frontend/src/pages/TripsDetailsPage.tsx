/* eslint-disable @typescript-eslint/no-explicit-any */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
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
  MapPin,
  Clock,
  Route,
  CheckCircle,
  AlertTriangle,
  Truck,
  FileText,
  Download,
  Map,
  Calculator,
  Navigation,
  RefreshCw,
  AlertCircle,
  Trash2,
  Settings,
  Plus,
} from "lucide-react";
import {
  useGetTripDetails,
  useGetTripComplianceReport,
  useDeleteTrip,
} from "../hooks/useTripQueries";
import { useTripCalculation } from "../hooks/useTripCalculation";
import {
  useTripELDLogs,
  useGenerateELDLogs,
  useCertifyELDLog,
  useEditELDLogEntry,
  useExportTripELDLogs,
} from "../hooks/useELDLogs";
import { ELDLogViewer } from "../components/ELDLogs/ELDLogViewer";
// import { ELDLogSummary } from "../components/ELDLogs/ELDLogSummary";
import { RouteMap } from "../components/Maps/RouteMap";
import { useMap } from "../hooks/useMap";
import { TripActions } from "../components/UI/TripActions";
import type { RoutePlanStop, TripELDLogsResponse } from "../types";
import type { LatLngExpression } from "leaflet";
import { motion } from "framer-motion";
import { DeleteConfirmationModal } from "../components/UI/DeleteTripModal";
import { SEO } from "../components/SEO/SEO";


type TabType = "overview" | "map" | "stops" | "hos" | "compliance" | "eld_logs";

function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [selectedLogIndex, setSelectedLogIndex] = useState(0);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

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
    // optimizeRoute,
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
    data: eldLogsData,
    isLoading: isELDLoading,
    isError: isELDError,
    error: eldError,
  } = useTripELDLogs(tripId || "");

  const generateELDMutation = useGenerateELDLogs();
  const certifyLogMutation = useCertifyELDLog();
  const editLogEntryMutation = useEditELDLogEntry();
  const exportTripLogsMutation = useExportTripELDLogs();

  const trip = tripResponse?.trip;
  // console.log("trips data:", trip);
  const complianceReport = complianceResponse?.compliance_report;

  const seoData = {
    title: trip
      ? `Trip ${trip.trip_id} - ${trip.status}`
      : "Trip Details",
    description: trip
      ? `Trip details for ${trip.current_address} → ${trip.pickup_address} → ${trip.delivery_address}`
      : "View trip details, routes, and compliance information.",
    keywords: trip
      ? `trip ${trip.trip_id}, ${trip.status}, route details, HOS compliance`
      : "trip details, route info, HOS compliance",
  };

  const { routeCoordinates, routeStops } = useMap({ trip });

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

  // const handleOptimizeRoute = async () => {
  //   clearErrors();
  //   try {
  //     await optimizeRoute({
  //       optimize_breaks: true,
  //       optimize_fuel_stops: true,
  //       optimize_daily_resets: true,
  //     });
  //   } catch (error) {
  //     console.error("Error optimizing route:", error);
  //   }
  // };

  const handleGenerateELDLogs = async () => {
    if (!tripId) return;

    try {
      await generateELDMutation.mutateAsync({
        tripId,
        options: {
          save_to_database: true,
          include_compliance_validation: true,
          export_format: "json",
        },
      });
    } catch (error) {
      console.error("Failed to generate ELD Logs:", error);
    }
  };

  const handleCertifyLog = async (
    logId: string,
    signature?: string,
    notes?: string
  ) => {
    try {
      await certifyLogMutation.mutateAsync({
        logId,
        request: {
          certification_signature: signature,
          certification_notes: notes,
        },
      });
    } catch (error) {
      console.error("Failed to certify log:", error);
      throw error;
    }
  };

  const handleEditLogEntry = async (
    logId: string,
    entryId: number,
    field: string,
    value: string,
    reason: string
  ) => {
    try {
      await editLogEntryMutation.mutateAsync({
        logId,
        request: {
          log_entry_id: entryId,
          field_name: field as any,
          new_value: value,
          edit_reason: reason,
        },
      });
    } catch (error) {
      console.error("Failed to edit log entry:", error);
      throw error;
    }
  };

  const handleExportTripLogs = async (format: string, purpose: string) => {
    if (!tripId) return;

    try {
      const response = await exportTripLogsMutation.mutateAsync({
        tripId,
        request: {
          export_format: format as any,
          export_purpose: purpose as any,
        },
      });

      if (response.download_url) {
        window.open(response.download_url, "_blank");
      }
    } catch (error) {
      console.error("Failed to export trip logs:", error);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  }

  const handleCancleDelete = () => { 
    setShowDeleteModal(false);
  }

  const handleDeleteTrip = async () => {
    if (!trip) return;

    try {
      await deleteTrip.mutateAsync(trip.trip_id);
      navigate("/trips");
    } catch (error) {
      console.error("Failed to delete trip:", error);
    }
  };

  const handleDeleteConfirm = () => {
    setShowDeleteModal(false);
    handleDeleteTrip();
  }

  const handleStopClick = (stop: RoutePlanStop) => {
    // Show stop details or navigate to stop tab
    setActiveTab("stops");

    // Optional: scroll to the specific stop in the stops tab
    setTimeout(() => {
      const stopElement = document.getElementById(
        `stop-${stop.address.replace(/\s+/g, "-")}`
      );
      if (stopElement) {
        stopElement.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 100);
  };

  // Add this handler for map clicks (optional - for future route modification):
  const handleMapClick = (coordinates: LatLngExpression) => {
    console.log("Map clicked at:", coordinates);
    // Future: Allow route modification by clicking on map
  };

  const hasCompletionData = () => {
    const recentCompletionKey = `trip_completion_${trip?.trip_id}`;
    const storedCompletion = sessionStorage.getItem(recentCompletionKey);
    return !!storedCompletion;
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: Route },
    { id: "map", label: "Map", icon: Map },
    { id: "stops", label: "Stops", icon: MapPin },
    { id: "hos", label: "HOS Periods", icon: Clock },
    { id: "compliance", label: "Compliance", icon: CheckCircle },
    { id: "eld_logs", label: "ELD Logs", icon: FileText },
  ] as const;

  // Loading state
  if (isTripLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-[100vh] md:h-[80vh] lg:landscape:h-[80vh]">
          <LoadingSpinner size="large" />
        </div>
      </Layout>
    );
  }

  // Error state
  if (isTripError || !trip) {
    return (
      <Layout>
        <div className="space-y-6 mt-14 md:mt-5 md:pr-4">
          <Card className="border-red-200 bg-red-50">
            <CardContent className="">
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
    <>
      <SEO
        title={seoData.title}
        description={seoData.description}
        keywords={seoData.keywords}
      />
      <Layout>
        <motion.div
          className="space-y-6 mt-14 pb-[15%] md:pb-[4%] xl:pb-0 pt-4 md:mt-0"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 25,
            duration: 1,
          }}
        >
          {/* Header */}
          <div className="space-y-4">
            <h1 className="text-[1.3rem] font-bold text-gray-900">
              {trip.pickup_address} → {trip.delivery_address}
            </h1>
            <p className="text-gray-600">Trip ID: {trip.trip_id}</p>
          </div>

          {/* Error Messages */}
          {(calculationError || optimizationError) && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-medium text-red-800">
                      Operation Failed
                    </h4>
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
                    {/* {eldError && (
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
                  </Button> */}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {trip.status === "draft" && (
            <Card className="py-4 px-3 shadow-none pb-4 md:pb-10">
              <CardContent>
                <div className="space-y-3">
                  <CardHeader>
                    <CardTitle className="flex items-center">
                      <Settings className="w-5 h-5 mr-2" />
                      Trip Actions
                    </CardTitle>
                  </CardHeader>
                  <div className="flex items-center space-x-2 text-green-600 mb-2">
                    <Calculator className="w-5 h-5" />
                    <span className="font-medium">Route Planning</span>
                  </div>
                  <div className="grid grid-cols-2 xl:flex xl:items-center gap-3">
                    <Button
                      leftIcon={<Calculator className="w-4 h-4" />}
                      onClick={handleCalculateRoute}
                      isLoading={isCalculating}
                      disabled={isCalculating || isOptimizing}
                      className="bg-green-600 hover:bg-green-700 w-[100%] xl:w-[20%]"
                    >
                      {isCalculating ? "Generating..." : "Generate Route"}
                    </Button>

                    <Button
                      variant="danger"
                      leftIcon={<Trash2 className="w-4 h-4" />}
                      onClick={handleDeleteClick}
                      isLoading={deleteTrip.isPending}
                      disabled={deleteTrip.isPending}
                      className="w-[100%] xl:w-[20%]"
                    >
                      {deleteTrip.isPending ? "Deleting..." : "Delete Trip"}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {trip.status === "completed" && !eldLogsData?.logs?.length && (
            <Card className="py-4 px-3 shadow-none">
              <CardContent>
                <Button
                  onClick={handleGenerateELDLogs}
                  isLoading={generateELDMutation.isPending}
                  leftIcon={<FileText className="w-4 h-4" />}
                  className="bg-green-600 hover:bg-green-700"
                >
                  Generate ELD Logs
                </Button>
              </CardContent>
            </Card>
          )}

          {(trip.status === "Planned" ||
            (trip.status === "completed" && hasCompletionData())) && (
            <Card className="py-4 px-3 shadow-none">
              <CardContent>
                <div className="pt-4">
                  <div className="flex items-center space-x-2 text-green-600 mb-3">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">
                      {trip.status === "Planned"
                        ? "Trip Completion"
                        : "Trip Summary"}
                    </span>
                  </div>
                  <TripActions
                    trip={trip}
                    onTripCompleted={(response) => {
                      // Refetch trip data to get updated status
                      refetchTrip();
                      console.log("Trip completed:", response.message);
                    }}
                    showFullActions={false}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trip Status Card */}
          <Card className="shadow-none md:p-7">
            <CardContent className="">
              <div className="grid grid-cols-2 gap-6">
                <div className="flex items-center space-x-3">
                  <div className="p-[0.65rem] md:p-[0.8rem] bg-blue-100 rounded-lg flex items-center justify-center">
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
                  <div className="p-[0.65rem] md:p-[0.8rem] bg-green-100 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">HOS Compliance</p>
                    <p
                      className={`font-medium text-sm ${
                        trip.is_hos_compliant
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {trip.is_hos_compliant ? "Compliant" : "Non-Compliant"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="p-[0.65rem] md:p-[0.8rem] bg-purple-100 rounded-lg flex items-center justify-center">
                    <Clock className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Duration</p>
                    <p className="font-medium text-gray-800">
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
                  <div className="p-[0.65rem] md:p-[0.8rem] bg-orange-100 rounded-lg flex items-center justify-center">
                    <Truck className="w-6 h-6 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Vehicle</p>
                    <p className="font-medium text-gray-800">
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
          <div className="border-b border-gray-200 overflow-hidden">
            <nav className="-mb-px flex space-x-8 overflow-x-auto custom-scrollbar pr-4">
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
                  {tab.id === "eld_logs" && eldLogsData && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      ✓
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content - keeping all existing tab content unchanged */}
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="shadow-none">
                <CardHeader>
                  <CardTitle>Trip Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-700">Departure</p>
                      <p className="font-medium text-gray-700">
                        {formatDateTime(trip.departure_datetime)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Estimated Arrival</p>
                      <p className="font-medium text-gray-700">
                        {trip.estimated_arrival_time
                          ? formatDateTime(trip.estimated_arrival_time)
                          : "Not calculated"}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Total Distance</p>
                      <p className="font-medium text-gray-700">
                        {trip.total_distance_miles
                          ? `${trip.total_distance_miles} miles`
                          : "Not calculated"}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Driving Time</p>
                      <p className="font-medium text-gray-700">
                        {trip.total_driving_time
                          ? `${trip.total_driving_time} hours`
                          : "Not calculated"}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Driver</p>
                      <p className="font-medium text-gray-700">
                        {trip.driver_name}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Total Stops</p>
                      <p className="font-medium text-gray-700">
                        {trip.stops.length}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-none pb-10">
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
                          <p className="font-medium text-gray-500">
                            {trip.current_address} → {trip.pickup_address}
                          </p>
                          <p className="text-sm text-gray-600">
                            Current Location → Pickup Location
                          </p>
                        </div>
                        {trip.deadhead_distance_miles && (
                          <div className="text-right text-sm text-gray-500">
                            <p>{trip.deadhead_distance_miles} miles</p>
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
                          <p className="font-medium text-gray-500">
                            {trip.pickup_address} → {trip.delivery_address}
                          </p>
                          <p className="text-sm text-gray-600">
                            Pickup Location → Delivery Location
                          </p>
                        </div>
                        {trip.loaded_distance_miles && (
                          <div className="text-right text-sm text-gray-500">
                            <p>{trip.loaded_distance_miles} miles</p>
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
                              <p className="font-medium text-gray-500 text-sm">
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
                          <p className="font-medium text-gray-500">
                            {trip.delivery_address}
                          </p>
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

          {/* Rest of the tab content remains exactly the same as your original code */}
          {activeTab === "map" && (
            <div className="space-y-6">
              {/* Map Container */}
              <Card className="shadow-none px-2 md:px-4">
                <CardHeader>
                  <div className="flex items-center justify-between space-x-2">
                    {trip.total_distance_miles && (
                      <span className="text-sm text-gray-600">
                        Total Distance: {trip.total_distance_miles} miles
                      </span>
                    )}
                    {trip.is_hos_compliant ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        HOS Compliant
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <AlertTriangle className="w-3 h-3 mr-1" />
                        Non-Compliant
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="h-96 lg:h-[500px]">
                    <RouteMap
                      trip={trip}
                      routeStops={routeStops}
                      routeCoordinates={routeCoordinates}
                      onStopClick={handleStopClick}
                      onMapClick={handleMapClick}
                      className="h-full"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Map Information Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Route Summary */}
                <Card className="shadow-none">
                  <CardHeader>
                    <CardTitle className="text-lg">Route Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Stops:</span>
                        <span className="font-medium text-gray-700">
                          {routeStops.length}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Driving Time:</span>
                        <span className="font-medium text-gray-700">
                          {trip.total_driving_time
                            ? `${trip.total_driving_time}h`
                            : "TBD"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Time:</span>
                        <span className="font-medium text-gray-700">
                          {trip.estimated_arrival_time &&
                          trip.departure_datetime
                            ? `${Math.round(
                                (new Date(
                                  trip.estimated_arrival_time
                                ).getTime() -
                                  new Date(trip.departure_datetime).getTime()) /
                                  (1000 * 60 * 60)
                              )}h`
                            : "TBD"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Fuel Stops:</span>
                        <span className="font-medium text-gray-700">
                          {
                            routeStops.filter((s) => s.type === "fuel_stop")
                              .length
                          }
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Navigation Actions */}
                <Card className="shadow-none">
                  <CardHeader>
                    <CardTitle className="text-lg">Navigation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <Button
                        variant="primary"
                        size="sm"
                        className="w-full"
                        leftIcon={<Navigation className="w-4 h-4" />}
                        onClick={() => {
                          if (navigator.geolocation) {
                            navigator.geolocation.getCurrentPosition(
                              (position) => {
                                const { latitude, longitude } = position.coords;
                                const url = `https://maps.google.com/maps?daddr=${trip.pickup_latitude},${trip.pickup_longitude}&saddr=${latitude},${longitude}`;
                                window.open(url, "_blank");
                              }
                            );
                          }
                        }}
                      >
                        Start Navigation
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full"
                        leftIcon={<Download className="w-4 h-4" />}
                      >
                        Export Route
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full"
                        leftIcon={<Settings className="w-4 h-4" />}
                        // onClick={() => setActiveTab("stops")}
                      >
                        Modify Stops
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Quick Stop Actions */}
              {routeStops.length > 0 && (
                <Card className="shadow-none pb-10">
                  <CardHeader>
                    <CardTitle className="text-lg">
                      Quick Stop Actions
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2  gap-2">
                      {routeStops.slice(0, 8).map((stop, index) => {
                        const isBreakStop = [
                          "required_break",
                          "rest_break",
                          "sleeper_berth",
                        ].includes(stop.type);
                        const isFuelStop = stop.type === "fuel_stop";

                        return (
                          <Button
                            key={index}
                            variant="secondary"
                            size="sm"
                            className={`text-left justify-start ${
                              isBreakStop
                                ? "border-yellow-200 hover:bg-yellow-50"
                                : isFuelStop
                                ? "border-purple-200 hover:bg-purple-50"
                                : "border-gray-200 hover:bg-gray-50"
                            }`}
                            onClick={() => handleStopClick(stop)}
                          >
                            <div className="flex items-center space-x-2">
                              <div
                                className={`w-2 h-2 rounded-full ${
                                  isBreakStop
                                    ? "bg-yellow-500"
                                    : isFuelStop
                                    ? "bg-purple-500"
                                    : "bg-blue-500"
                                }`}
                              />
                              <div className="min-w-0 flex-1">
                                <p className="text-xs font-medium truncate">
                                  {stop.type.replace("_", " ").toUpperCase()}
                                </p>
                                <p className="text-xs text-gray-500 truncate">
                                  {stop.address.length > 20
                                    ? `${stop.address.substring(0, 20)}...`
                                    : stop.address}
                                </p>
                              </div>
                            </div>
                          </Button>
                        );
                      })}
                    </div>

                    {routeStops.length > 8 && (
                      <div className="mt-3 text-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setActiveTab("stops")}
                        >
                          View All {routeStops.length} Stops
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {activeTab === "stops" && (
            <Card className="shadow-none px-3 pb-10 md:px-6">
              <CardHeader>
                <CardTitle>Trip Stops ({trip.stops.length})</CardTitle>
              </CardHeader>
              <CardContent className="shadow-none">
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
                        className="flex items-center justify-between px-3 py-4 border border-gray-200 rounded-lg"
                      >
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center justify-center">
                            <span className="text-sm font-bold text-blue-600">
                              {stop.sequence_order}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium text-gray-600">
                              {stop.address}
                            </p>
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
            <Card className="shadow-none px-3 pb-10 md:px-6">
              <CardHeader>
                <CardTitle>
                  HOS Duty Periods ({trip.hos_periods.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {trip.hos_periods.length === 0 ? (
                  <div className="text-center py-8">
                    <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">
                      No HOS periods generated yet
                    </p>
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
                            className={`p-[0.7rem] rounded-lg flex items-center justify-center ${
                              period.duty_status === "driving"
                                ? "bg-green-100"
                                : period.duty_status === "on_duty_not_driving"
                                ? "bg-blue-100"
                                : period.duty_status === "off_duty"
                                ? "bg-red-100"
                                : "bg-gray-100"
                            }`}
                          >
                            <Clock
                              className={`w-5 h-5 ${
                                period.duty_status === "driving"
                                  ? "text-green-600"
                                  : period.duty_status === "on_duty_not_driving"
                                  ? "text-blue-600"
                                  : period.duty_status === "off_duty"
                                  ? "text-red-600"
                                  : "text-gray-600"
                              }`}
                            />
                          </div>
                          <div>
                            <p className="font-medium text-gray-600">
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
              <Card className="shadow-none px-3 md:px-6">
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
                          <span className="font-medium text-gray-700">
                            {trip.total_driving_time
                              ? `${trip.total_driving_time} / 11 hours`
                              : "Not calculated"}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-600">
                            Total On-Duty Hours
                          </span>
                          <span className="font-medium text-gray-700">
                            {complianceReport?.total_on_duty_hours
                              ? `${complianceReport.total_on_duty_hours} / 14 hours`
                              : "Not calculated"}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-600">
                            Required Breaks
                          </span>
                          <span className="font-medium text-gray-700">
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
                        complianceReport?.violations.length > 0 && (
                          <div className="mt-4 p-3 bg-red-50 rounded-lg">
                            <h4 className="font-medium text-red-800 mb-2">
                              Violations Found
                            </h4>
                            <ul className="space-y-1">
                              {complianceReport?.violations
                                .slice(0, 2)
                                .map((violation, index) => (
                                  <p
                                    key={index}
                                    className="text-sm font-medium text-red-600"
                                  >
                                    ⚠{" "}
                                    {violation.type
                                      .replace(/_/g, " ")
                                      .toUpperCase()}
                                  </p>
                                ))}
                              {complianceReport &&
                                complianceReport.violations.length > 2 && (
                                  <p className="text-xs text-gray-500">
                                    +{complianceReport.violations.length - 2}{" "}
                                    more violations
                                  </p>
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
                              {complianceReport.warnings.map(
                                (warning, index) => (
                                  <li
                                    key={index}
                                    className="text-sm text-yellow-700"
                                  >
                                    • {warning.message}
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="shadow-none">
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
                    onClick={() => {
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
                      refetchTrip();
                    }}
                    disabled={!trip.hos_periods.length}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Validate HOS Compliance
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}

          {activeTab === "eld_logs" && (
            <TripELDLogsSection
              tripId={tripId || ""}
              tripStatus={trip.status}
              eldLogsData={eldLogsData}
              isLoading={isELDLoading}
              isError={isELDError}
              error={eldError}
              selectedLogIndex={selectedLogIndex}
              onLogSelect={setSelectedLogIndex}
              onGenerateLogs={handleGenerateELDLogs}
              onCertifyLog={handleCertifyLog}
              onEditLogEntry={handleEditLogEntry}
              onExportAll={() => handleExportTripLogs("pdf", "driver_record")}
              isGenerating={generateELDMutation.isPending}
              isCertifying={certifyLogMutation.isPending}
              isEditing={editLogEntryMutation.isPending}
              isExporting={exportTripLogsMutation.isPending}
            />
          )}
        </motion.div>
        <DeleteConfirmationModal
          isOpen={showDeleteModal}
          onClose={handleCancleDelete}
          onConfirm={handleDeleteConfirm}
          isLoading={deleteTrip.isPending}
          tripTitle={
            trip?.pickup_address && trip?.delivery_address
              ? `${trip.pickup_address} → ${trip.delivery_address}`
              : "this trip"
          }
        />
      </Layout>
    </>
  );
}

interface TripELDLogsSectionProps {
  tripId: string;
  tripStatus: string;
  eldLogsData: TripELDLogsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  selectedLogIndex: number;
  onLogSelect: (index: number) => void;
  onGenerateLogs: () => void;
  onCertifyLog: (
    logId: string,
    signature?: string,
    notes?: string
  ) => Promise<void>;
  onEditLogEntry: (
    logId: string,
    entryId: number,
    field: string,
    value: string,
    reason: string
  ) => Promise<void>;
  onExportAll: () => Promise<void>;
  isGenerating: boolean;
  isCertifying: boolean;
  isEditing: boolean;
  isExporting: boolean;
}

function TripELDLogsSection({
  // tripId,
  tripStatus,
  eldLogsData,
  isLoading,
  isError,
  error,
  selectedLogIndex,
  // onLogSelect,
  onGenerateLogs,
  isGenerating,
  // isExporting,
}: TripELDLogsSectionProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="large" text="Loading ELD logs..." />
      </div>
    );
  }

  if (isError) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="p-6">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-8 h-8 text-red-600" />
            <div>
              <h3 className="text-lg font-medium text-red-800">
                Failed to Load ELD Logs
              </h3>
              <p className="text-red-700 mt-1">
                {error?.message || "Unable to load ELD logs for this trip"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No logs exist yet
  if (!eldLogsData?.logs || eldLogsData.logs.length === 0) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                ELD Logs
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No ELD Logs Generated
              </h3>
              <p className="text-gray-600 mb-6">
                {tripStatus === "completed"
                  ? "Generate ELD logs from this completed trip."
                  : "Complete the trip and calculate the route to generate ELD logs."}
              </p>

              {tripStatus === "completed" && (
                <Button
                  onClick={onGenerateLogs}
                  isLoading={isGenerating}
                  leftIcon={<Plus className="w-4 h-4" />}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {isGenerating ? "Generating..." : "Generate ELD Logs"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const dailyLogs = eldLogsData.logs;
  const currentLog = dailyLogs[selectedLogIndex];

  return (
    <div className="space-y-6">
      {/* Current Log Viewer */}
      {currentLog && (
        <ELDLogViewer
          dailyLog={currentLog}
        />
      )}
    </div>
  );
}

export default TripDetailPage;