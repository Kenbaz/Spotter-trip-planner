import { useMemo, useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
// import { LoadingSpinner } from "../components/UI/LoadingSpinner";
import {
  Plus,
  Route,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  Check,
} from "lucide-react";
import { useMyTrips } from "../hooks/useTripQueries";
import type { TripListItem } from "../types";
import { SEO } from "../components/SEO/SEO";

interface TripStats {
  completed: number;
  inProgress: number;
  planned: number;
  draft: number;
  total: number;
}

// Custom Animated Dropdown Component
interface DropdownOption {
  value: string;
  label: string;
}

interface FilterDropdownProps {
  value: string;
  onChange: (value: string) => void;
  options: DropdownOption[];
  placeholder?: string;
  className?: string;
}

function FilterDropdown({
  value,
  onChange,
  options,
  placeholder = "Select option",
  className = "",
}: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((option) => option.value === value);

  const handleOptionClick = (optionValue: string) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Dropdown Trigger */}
      <motion.div
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-[#FEFEFE] cursor-pointer focus:outline-none flex items-center justify-between"
        whileHover={{ borderColor: "#3b82f6" }}
        whileTap={{ scale: 0.98 }}
      >
        <span className="text-gray-900">
          {selectedOption?.label || placeholder}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4 text-gray-500" />
        </motion.div>
      </motion.div>

      {/* Dropdown Options */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 25,
              duration: 0.2,
            }}
            className="absolute top-full left-0 right-0 mt-1 bg-[#FEFEFE] border border-gray-300 rounded-md shadow-lg z-50 overflow-hidden"
          >
            {options.map((option) => (
              <motion.div
                key={option.value}
                onClick={() => handleOptionClick(option.value)}
                className={`px-3 py-2 cursor-pointer flex items-center justify-between hover:bg-gray-50 transition-colors ${
                  value === option.value
                    ? "bg-blue-50 text-blue-600"
                    : "text-gray-900"
                }`}
              >
                <span>{option.label}</span>
                {value === option.value && (
                  <Check className="w-4 h-4 text-blue-600" />
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TripsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Dropdown options
  const statusOptions: DropdownOption[] = [
    { value: "all", label: "All Status" },
    { value: "draft", label: "Draft" },
    { value: "planned", label: "Planned" },
    { value: "in_progress", label: "In Progress" },
    { value: "completed", label: "Completed" },
  ];

  // Fetch trips data
  const {
    data: tripsResponse,
    isLoading,
    isError,
    error,
    refetch,
  } = useMyTrips(statusFilter === "all" ? undefined : statusFilter);

  // Process trips data
  const trips = useMemo(() => {
    return tripsResponse?.trips || [];
  }, [tripsResponse?.trips]);

  // Filter trips based on search term
  const filteredTrips = useMemo(() => {
    if (!searchTerm.trim()) {
      return trips;
    }

    const searchLower = searchTerm.toLowerCase();
    return trips.filter(
      (trip) =>
        trip.current_address.toLowerCase().includes(searchLower) ||
        trip.pickup_address.toLowerCase().includes(searchLower) ||
        trip.delivery_address.toLowerCase().includes(searchLower) ||
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

  const TripCardSkeleton = () => (
    <div className="p-4 border h-24 bg-gray-200 border-gray-200 rounded-lg animate-pulse"></div>
  );

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
    <>
      <SEO
        title="Trips Page"
        description="View all trips"
        keywords="trips, trip management, trucking, HOS compliance"
      />
      <Layout>
        <motion.div
          className="space-y-6 mt-[14%] pb-[20%] md:mt-0 md:h-full pt-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 25,
            duration: 0.6,
          }}
        >
          {/* Header */}
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-gray-900">My Trips</h1>
            <p className="text-gray-600">Track your trips</p>
          </div>

          {/* Filters */}
          <Card className="px-2 py-4 md:px-4">
            <CardContent className="">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="Search by origin, destination"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="text-gray-900"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Trip Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
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
          <Card className="px-3 pb-0 lg:h-auto border border-blue-700">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>
                  Trips ({filteredTrips.length}
                  {searchTerm && ` of ${trips.length}`})
                </CardTitle>
                <div className="w-[10rem] md:w-[14rem]">
                  <FilterDropdown
                    value={statusFilter}
                    onChange={setStatusFilter}
                    options={statusOptions}
                    placeholder="Select status"
                    className="w-full"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="max-h-[30rem] md:max-h-[55vh] overflow-y-auto custom-scrollbar pt-4 pb-8 sm:pb-[17%] md:pb-[11%] -mt-[4%] lg:-mt-3">
              {isLoading ? (
                // Skeleton loading state
                <div className="space-y-4">
                  {[...Array(3)].map((_, index) => (
                    <TripCardSkeleton key={index} />
                  ))}
                </div>
              ) : filteredTrips.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{
                    type: "spring",
                    stiffness: 300,
                    damping: 25,
                    duration: 1,
                  }}
                >
                  <div className="text-center py-12">
                    <Route className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      {trips.length === 0
                        ? "No trips found"
                        : "No matching trips"}
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
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{
                    type: "spring",
                    stiffness: 300,
                    damping: 25,
                    duration: 1,
                  }}
                >
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
                                      {trip.current_address} →{" "}
                                      {trip.pickup_address} →{" "}
                                      {trip.delivery_address}
                                    </p>
                                    <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                                      <span className="text-gray-900 hidden lg:block">
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
                                        <span className="text-gray-900 hidden xl:block">
                                          ETA: {estimatedArrival.date} at{" "}
                                          {estimatedArrival.time}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>

                              {/* Status and Compliance */}
                              <div className="md:flex items-center hidden space-x-3">
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
                                      <div className="md:flex gap-1 items-center">
                                        <AlertTriangle className="w-4 h-4 text-yellow-500" />
                                        <span className="text-sm text-yellow-600">
                                          {trip.compliance_status}
                                        </span>
                                      </div>
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
                </motion.div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </Layout>
    </>
  );
}

export default TripsPage;
