import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
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
  MapPin,
  Clock,
  Truck,
  AlertCircle,
  CheckCircle,
  Calculator,
  ArrowLeft,
  Navigation,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useCreateTrip, useGeocodeMutation } from "../hooks/useTripQueries";
import type { CreateTripRequest } from "../types";


interface DriverCycleFormData {
  current_cycle_hours_used: number;
  hours_driven_today: number;
  hours_on_duty_today: number;
  current_duty_status:
    | "off_duty"
    | "sleeper_berth"
    | "driving"
    | "on_duty_not_driving";
  current_status_start_time: string;
  last_break_end_time?: string;
}

interface FormData {
  current_address: string;
  current_latitude: string;
  current_longitude: string;

  pickup_address: string;
  pickup_latitude: string;
  pickup_longitude: string;

  delivery_address: string;
  delivery_latitude: string;
  delivery_longitude: string;

  departure_datetime: string;
  max_fuel_distance_miles: number;
  pickup_duration_minutes: number;
  delivery_duration_minutes: number;
}

interface FormErrors {
  [key: string]: string;
}

interface GeocodingState {
  current: {
    isLoading: boolean;
    isGeocoded: boolean;
    error: string | null;
  };
  pickup: {
    isLoading: boolean;
    isGeocoded: boolean;
    error: string | null;
  };
  delivery: {
    isLoading: boolean;
    isGeocoded: boolean;
    error: string | null;
  };
}


export function CreateTripPage() {
  const navigate = useNavigate();

  const createTripMutation = useCreateTrip();
  const geocodeMutation = useGeocodeMutation();

  const [driverCycle, setDriverCycle] = useState<DriverCycleFormData>({
    current_cycle_hours_used: 0,
    hours_driven_today: 0,
    hours_on_duty_today: 0,
    current_duty_status: "off_duty",
    current_status_start_time: new Date().toISOString().slice(0, 16),
    last_break_end_time: "",
  });

  // Initial form data
  const [formData, setFormData] = useState<FormData>({
    current_address: "",
    current_latitude: "",
    current_longitude: "",
    pickup_address: "",
    pickup_latitude: "",
    pickup_longitude: "",
    delivery_address: "",
    delivery_latitude: "",
    delivery_longitude: "",
    departure_datetime: "",
    max_fuel_distance_miles: 1000,
    pickup_duration_minutes: 60,
    delivery_duration_minutes: 60,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [geocodingState, setGeocodingState] = useState<GeocodingState>({
    current: {
      isLoading: false,
      isGeocoded: false,
      error: null,
    },
    pickup: {
      isLoading: false,
      isGeocoded: false,
      error: null,
    },
    delivery: {
      isLoading: false,
      isGeocoded: false,
      error: null,
    },
  });



  const isCreatingTrip = createTripMutation.isPending;
  const isFormDisabled = isCreatingTrip || geocodingState.current.isLoading || geocodingState.pickup.isLoading || geocodingState.delivery.isLoading;


  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.current_address.trim()) {
      newErrors.current_address = "Origin address is required";
    }
    if (!formData.pickup_address.trim()) {
      newErrors.destination_address = "Pickup address is required";
    }
    if (!formData.delivery_address.trim()) {
      newErrors.destination_address = "Delivery address is required";
    }
    if (!formData.departure_datetime) {
      newErrors.departure_datetime = "Departure time is required";
    } else {
      const departureDate = new Date(formData.departure_datetime);
      if (departureDate <= new Date()) {
        newErrors.departure_datetime = "Departure time must be in the future";
      }
    }

    // Check if addressed are geocoded
    if (!geocodingState.current.isGeocoded && formData.current_address.trim()) {
      newErrors.current_address = "Please geocode your current location";
    }
    if (!geocodingState.pickup.isGeocoded && formData.pickup_address.trim()) {
      newErrors.pickup_address = "Please geocode the pickup location";
    }
    if (
      !geocodingState.delivery.isGeocoded &&
      formData.delivery_address.trim()
    ) {
      newErrors.delivery_address = "Please geocode the delivery location";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateCycleData = (): boolean => {
    const newErrors: FormErrors = {};

    // Check cycle hours
    if (
      driverCycle.current_cycle_hours_used < 0 ||
      driverCycle.current_cycle_hours_used > 70
    ) {
      newErrors.current_cycle_hours_used =
        "Cycle hours must be between 0 and 70";
    }

    if (
      driverCycle.hours_driven_today < 0 ||
      driverCycle.hours_driven_today > 11
    ) {
      newErrors.hours_driven_today =
        "Today's driving hours must be between 0 and 11";
    }

    if (
      driverCycle.hours_on_duty_today < 0 ||
      driverCycle.hours_on_duty_today > 14
    ) {
      newErrors.hours_on_duty_today =
        "Today's on-duty hours must be between 0 and 14";
    }

    // Check if driving hours exceed on-duty hours
    if (driverCycle.hours_driven_today > driverCycle.hours_on_duty_today) {
      newErrors.hours_driven_today =
        "Driving hours cannot exceed on-duty hours";
    }

    if (
      driverCycle.hours_on_duty_today > driverCycle.current_cycle_hours_used
    ) {
      newErrors.hours_on_duty_today =
        "Today's hours cannot exceed total cycle hours";
    }

    // Check if currently driving for too long without break
    if (driverCycle.current_duty_status === "driving") {
      const statusStart = new Date(driverCycle.current_status_start_time);
      const now = new Date();
      const hoursSinceStart =
        (now.getTime() - statusStart.getTime()) / (1000 * 60 * 60);
      const totalDrivingToday =
        driverCycle.hours_driven_today + hoursSinceStart;

      if (totalDrivingToday > 8 && !driverCycle.last_break_end_time) {
        newErrors.current_duty_status =
          "Driver needs 30-minute break (driving more than 8 hours)";
      }
    }

    setErrors((prev) => ({ ...prev, ...newErrors }));
    return Object.keys(newErrors).length === 0;
  };


  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!validateForm() || !validateCycleData()) {
      return;
    }

    try {
      // Prepare trip data for API
      const tripData: CreateTripRequest & DriverCycleFormData = {
        // Location data
        current_address: formData.current_address.trim(),
        current_latitude: parseFloat(formData.current_latitude),
        current_longitude: parseFloat(formData.current_longitude),
        pickup_address: formData.pickup_address.trim(),
        pickup_latitude: parseFloat(formData.pickup_latitude),
        pickup_longitude: parseFloat(formData.pickup_longitude),
        delivery_address: formData.delivery_address.trim(),
        delivery_latitude: parseFloat(formData.delivery_latitude),
        delivery_longitude: parseFloat(formData.delivery_longitude),

        // Trip timing
        departure_datetime: formData.departure_datetime,
        max_fuel_distance_miles: formData.max_fuel_distance_miles,
        pickup_duration_minutes: formData.pickup_duration_minutes,
        delivery_duration_minutes: formData.delivery_duration_minutes,

        // Current cycle data
        current_cycle_hours_used: driverCycle.current_cycle_hours_used,
        hours_driven_today: driverCycle.hours_driven_today,
        hours_on_duty_today: driverCycle.hours_on_duty_today,
        current_duty_status: driverCycle.current_duty_status,
        current_status_start_time: driverCycle.current_status_start_time,
        last_break_end_time: driverCycle.last_break_end_time || undefined,
      };

      const result = await createTripMutation.mutateAsync(tripData)

      if (result.success) { 
        navigate(`/trips/${result.trip.trip_id}`)
      }
    } catch (error) {
      console.error("Error creating trip:", error);
    }
  };

  const handleGeocode = async (field: "current" | "pickup" | "delivery") => {
    const addressField = `${field}_address` as keyof FormData;
    const address = formData[addressField] as string;

    if (!address.trim()) {
      return;
    }

    setGeocodingState((prev) => ({
      ...prev,
      [field]: { ...prev[field], isLoading: true, error: null },
    }));

    try {
      const result = await geocodeMutation.mutateAsync(address.trim());

      if (result.success && result.latitude && result.longitude) {
        setFormData(prev => ({
          ...prev,
          [`${field}_latitude`]: result.latitude!.toString(),
          [`${field}_longitude`]: result.longitude!.toString(),
        }));

        setGeocodingState(prev => ({
          ...prev,
          [field]: { isLoading: false, isGeocoded: true, error: null },
        }));

        // Clear any previous errors for this field
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[addressField];
          return newErrors;
        });
      } else {
        throw new Error(result.error || "Geocoding failed");
      }
    } catch (error) { 
      const errorMessage = error instanceof Error ? error.message : "Geocoding error occurred";

      setGeocodingState(prev => ({
        ...prev,
        [field]: { isLoading: false, isGeocoded: false, error: errorMessage },
      }));
    }
  };


  const handleAddressChange = (
    field: "current" | "pickup" | "delivery",
    value: string
  ) => {
    const addressField = `${field}_address` as keyof FormData;

    setFormData(prev => ({
      ...prev,
      [addressField]: value
    }))
    setGeocodingState(prev => ({
      ...prev,
      [field]: { ...prev[field], isGeocoded: false, error: null },
    }));
  };

  const getGeocodingButtonState = (
    field: "current" | "pickup" | "delivery"
  ) => {
    const state = geocodingState[field];
    const addressField = `${field}_address` as keyof FormData;
    const address = formData[addressField] as string;

    if (state.isLoading)
      return {
        disabled: true,
        text: "Geocoding...",
        variant: "secondary" as const,
      };
    if (state.isGeocoded)
      return { disabled: false, text: "✓", variant: "secondary" as const };
    if (!address.trim())
      return { disabled: true, text: "📍", variant: "secondary" as const };
    return { disabled: false, text: "📍", variant: "secondary" as const };
  };


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
                Plan New Trip
              </h1>
              <p className="text-gray-600">
                Create a new HOS-compliant trip plan
              </p>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {createTripMutation.isError && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-4">
              <div className="flex items-center space-x-2 text-red-800">
                <AlertCircle className="w-5 h-5" />
                <span className="font-medium">Failed to create trip</span>
              </div>
              <p className="text-sm text-red-700 mt-1">
                {createTripMutation.error instanceof Error
                  ? createTripMutation.error.message
                  : "An unexpected error occurred"}
              </p>
            </CardContent>
          </Card>
        )}

        <form
          onSubmit={handleSubmit}
          className="grid grid-cols-1 lg:grid-cols-3 gap-6"
        >
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Clock className="w-5 h-5 mr-2" />
                  Current HOS Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 border border-orange-200 rounded-lg bg-orange-50">
                  <h4 className="font-medium text-orange-800 mb-3">
                    Enter your current Hours of Service status
                  </h4>
                  <p className="text-sm text-orange-700 mb-4">
                    This information is required to ensure your trip plan
                    complies with HOS regulations.
                  </p>

                  {/* Cycle Hours */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      label="Current Cycle Hours Used"
                      type="number"
                      value={driverCycle.current_cycle_hours_used}
                      onChange={(e) =>
                        setDriverCycle((prev) => ({
                          ...prev,
                          current_cycle_hours_used:
                            parseFloat(e.target.value) || 0,
                        }))
                      }
                      min="0"
                      max="70"
                      step="0.1"
                      helperText="Hours used in your current 8-day cycle (out of 70)"
                      error={errors.current_cycle_hours_used}
                      disabled={isFormDisabled}
                    />

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Current Duty Status
                      </label>
                      <select
                        value={driverCycle.current_duty_status}
                        onChange={(e) =>
                          setDriverCycle((prev) => ({
                            ...prev,
                            current_duty_status: e.target.value as any,
                          }))
                        }
                        className={`w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                          errors.current_duty_status ? "border-red-300" : ""
                        }`}
                        disabled={isFormDisabled}
                      >
                        <option value="off_duty">Off Duty</option>
                        <option value="sleeper_berth">Sleeper Berth</option>
                        <option value="driving">Currently Driving</option>
                        <option value="on_duty_not_driving">
                          On Duty (Not Driving)
                        </option>
                      </select>
                      {errors.current_duty_status && (
                        <p className="mt-1 text-sm text-red-600">
                          {errors.current_duty_status}
                        </p>
                      )}
                      <p className="mt-1 text-sm text-gray-500">
                        What are you doing right now?
                      </p>
                    </div>
                  </div>

                  {/* Today's Hours */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <Input
                      label="Hours Driven Today"
                      type="number"
                      value={driverCycle.hours_driven_today}
                      onChange={(e) =>
                        setDriverCycle((prev) => ({
                          ...prev,
                          hours_driven_today: parseFloat(e.target.value) || 0,
                        }))
                      }
                      min="0"
                      max="11"
                      step="0.1"
                      helperText="Hours already driven today (out of 11 allowed)"
                      error={errors.hours_driven_today}
                      disabled={isFormDisabled}
                    />

                    <Input
                      label="Hours On-Duty Today"
                      type="number"
                      value={driverCycle.hours_on_duty_today}
                      onChange={(e) =>
                        setDriverCycle((prev) => ({
                          ...prev,
                          hours_on_duty_today: parseFloat(e.target.value) || 0,
                        }))
                      }
                      min="0"
                      max="14"
                      step="0.1"
                      helperText="Total on-duty hours today (out of 14 allowed)"
                      error={errors.hours_on_duty_today}
                      disabled={isFormDisabled}
                    />
                  </div>

                  {/* Status Timing */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <Input
                      label="When Did Current Status Start?"
                      type="datetime-local"
                      value={driverCycle.current_status_start_time}
                      onChange={(e) =>
                        setDriverCycle((prev) => ({
                          ...prev,
                          current_status_start_time: e.target.value,
                        }))
                      }
                      helperText="When did you start your current duty status?"
                      disabled={isFormDisabled}
                    />

                    <Input
                      label="Last 30-Min Break Ended (Optional)"
                      type="datetime-local"
                      value={driverCycle.last_break_end_time}
                      onChange={(e) =>
                        setDriverCycle((prev) => ({
                          ...prev,
                          last_break_end_time: e.target.value,
                        }))
                      }
                      helperText="When did your last 30-minute break end?"
                      disabled={isFormDisabled}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
            {/* Trip Locations */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MapPin className="w-5 h-5 mr-2" />
                  Trip Locations
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Current Location */}
                <div className="p-4 border border-blue-200 rounded-lg bg-blue-50">
                  <div className="flex items-center space-x-2 mb-3">
                    <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                      1
                    </div>
                    <h4 className="font-medium text-blue-800">
                      Your Current Location
                    </h4>
                  </div>
                  <div className="flex space-x-2">
                    <Input
                      label="Current Address"
                      value={formData.current_address}
                      onChange={(e) =>
                        handleAddressChange("current", e.target.value)
                      }
                      placeholder="Where are you now?"
                      error={
                        errors.current_address ||
                        geocodingState.current.error ||
                        undefined
                      }
                      className="flex-1"
                      disabled={isFormDisabled}
                    />
                    <Button
                      type="button"
                      variant={getGeocodingButtonState("current").variant}
                      onClick={() => handleGeocode("current")}
                      className="mt-6"
                      disabled={getGeocodingButtonState("current").disabled}
                      isLoading={geocodingState.current.isLoading}
                    >
                      {getGeocodingButtonState("current").text}
                    </Button>
                  </div>
                  {geocodingState.current.isGeocoded && (
                    <div className="flex items-center mt-1 text-xs text-green-600">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Coordinates: {formData.current_latitude},{" "}
                      {formData.current_longitude}
                    </div>
                  )}
                </div>

                {/* Visual Arrow */}
                <div className="flex justify-center">
                  <Navigation className="w-6 h-6 text-gray-400" />
                </div>

                {/* Pickup Location */}
                <div className="p-4 border border-green-200 rounded-lg bg-green-50">
                  <div className="flex items-center space-x-2 mb-3">
                    <div className="w-6 h-6 bg-green-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                      2
                    </div>
                    <h4 className="font-medium text-green-800">
                      Pickup Location
                    </h4>
                  </div>
                  <div className="flex space-x-2">
                    <Input
                      label="Pickup Address"
                      value={formData.pickup_address}
                      onChange={(e) =>
                        handleAddressChange("pickup", e.target.value)
                      }
                      placeholder="Where will you pick up the freight?"
                      error={
                        errors.pickup_address ||
                        geocodingState.pickup.error ||
                        undefined
                      }
                      className="flex-1"
                      disabled={isFormDisabled}
                    />
                    <Button
                      type="button"
                      variant={getGeocodingButtonState("pickup").variant}
                      onClick={() => handleGeocode("pickup")}
                      className="mt-6"
                      disabled={getGeocodingButtonState("pickup").disabled}
                      isLoading={geocodingState.pickup.isLoading}
                    >
                      {getGeocodingButtonState("pickup").text}
                    </Button>
                  </div>
                  {geocodingState.pickup.isGeocoded && (
                    <div className="flex items-center mt-1 text-xs text-green-600">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Coordinates: {formData.pickup_latitude},{" "}
                      {formData.pickup_longitude}
                    </div>
                  )}
                </div>

                {/* Visual Arrow */}
                <div className="flex justify-center">
                  <Navigation className="w-6 h-6 text-gray-400" />
                </div>

                {/* Delivery Location */}
                <div className="p-4 border border-red-200 rounded-lg bg-red-50">
                  <div className="flex items-center space-x-2 mb-3">
                    <div className="w-6 h-6 bg-red-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                      3
                    </div>
                    <h4 className="font-medium text-red-800">
                      Delivery Location
                    </h4>
                  </div>
                  <div className="flex space-x-2">
                    <Input
                      label="Delivery Address"
                      value={formData.delivery_address}
                      onChange={(e) =>
                        handleAddressChange("delivery", e.target.value)
                      }
                      placeholder="Where will you deliver the freight?"
                      error={
                        errors.delivery_address ||
                        geocodingState.delivery.error ||
                        undefined
                      }
                      className="flex-1"
                      disabled={isFormDisabled}
                    />
                    <Button
                      type="button"
                      variant={getGeocodingButtonState("delivery").variant}
                      onClick={() => handleGeocode("delivery")}
                      className="mt-6"
                      disabled={getGeocodingButtonState("delivery").disabled}
                      isLoading={geocodingState.delivery.isLoading}
                    >
                      {getGeocodingButtonState("delivery").text}
                    </Button>
                  </div>
                  {geocodingState.delivery.isGeocoded && (
                    <div className="flex items-center mt-1 text-xs text-green-600">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Coordinates: {formData.delivery_latitude},{" "}
                      {formData.delivery_longitude}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Timing Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Clock className="w-5 h-5 mr-2" />
                  Timing Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  label="Departure Date & Time"
                  type="datetime-local"
                  value={formData.departure_datetime}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      departure_datetime: e.target.value,
                    }))
                  }
                  error={errors.departure_datetime}
                  min={new Date().toISOString().slice(0, 16)}
                  disabled={isFormDisabled}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Pickup Duration (minutes)"
                    type="number"
                    value={formData.pickup_duration_minutes}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        pickup_duration_minutes: parseInt(e.target.value) || 0,
                      }))
                    }
                    min="15"
                    max="240"
                    helperText="Time needed for pickup activities"
                    disabled={isFormDisabled}
                  />

                  <Input
                    label="Delivery Duration (minutes)"
                    type="number"
                    value={formData.delivery_duration_minutes}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        delivery_duration_minutes:
                          parseInt(e.target.value) || 0,
                      }))
                    }
                    min="15"
                    max="240"
                    helperText="Time needed for delivery activities"
                    disabled={isFormDisabled}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Vehicle Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Truck className="w-5 h-5 mr-2" />
                  Vehicle Settings
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Input
                  label="Maximum Fuel Distance (miles)"
                  type="number"
                  value={formData.max_fuel_distance_miles}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      max_fuel_distance_miles: parseInt(e.target.value) || 0,
                    }))
                  }
                  min="200"
                  max="1200"
                  helperText="Maximum distance between fuel stops"
                  disabled={isFormDisabled}
                />
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Trip Preview */}
            <Card>
              <CardHeader>
                <CardTitle>Trip Preview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600">Current Location</p>
                  <p className="font-medium">
                    {formData.current_address || "Not set"}
                  </p>
                  {geocodingState.current.isGeocoded && (
                    <p className="text-xs text-green-600">✓ Geocoded</p>
                  )}
                </div>

                <div className="flex justify-center">
                  <div className="w-px h-4 bg-gray-300"></div>
                </div>

                <div>
                  <p className="text-sm text-gray-600">Pickup Location</p>
                  <p className="font-medium">
                    {formData.pickup_address || "Not set"}
                  </p>
                  {geocodingState.pickup.isGeocoded && (
                    <p className="text-xs text-green-600">✓ Geocoded</p>
                  )}
                </div>

                <div className="flex justify-center">
                  <div className="w-px h-4 bg-gray-300"></div>
                </div>

                <div>
                  <p className="text-sm text-gray-600">Delivery Location</p>
                  <p className="font-medium">
                    {formData.delivery_address || "Not set"}
                  </p>
                  {geocodingState.delivery.isGeocoded && (
                    <p className="text-xs text-green-600">✓ Geocoded</p>
                  )}
                </div>

                <div className="pt-3 border-t border-gray-200">
                  <div>
                    <p className="text-sm text-gray-600">Departure</p>
                    <p className="font-medium">
                      {formData.departure_datetime
                        ? new Date(formData.departure_datetime).toLocaleString()
                        : "Not set"}
                    </p>
                  </div>

                  <div className="mt-3">
                    <p className="text-sm text-gray-600">Estimated Distances</p>
                    <p className="font-medium text-gray-400">
                      Calculate route to see
                    </p>
                  </div>

                  <div className="mt-3">
                    <p className="text-sm text-gray-600">Estimated Duration</p>
                    <p className="font-medium text-gray-400">
                      Calculate route to see
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardContent className="space-y-3">
                <Button
                  type="submit"
                  className="w-full"
                  isLoading={isCreatingTrip}
                  leftIcon={<Calculator className="w-4 h-4" />}
                  disabled={
                    isFormDisabled ||
                    !formData.current_address ||
                    !formData.pickup_address ||
                    !formData.delivery_address ||
                    !formData.departure_datetime ||
                    !geocodingState.current.isGeocoded ||
                    !geocodingState.pickup.isGeocoded ||
                    !geocodingState.delivery.isGeocoded
                  }
                >
                  {isCreatingTrip ? "Creating Trip..." : "Create Trip"}
                </Button>

                <div className="text-center">
                  <Link to="/trips">
                    <Button variant="ghost" size="sm" disabled={isCreatingTrip}>
                      Cancel
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Trip Structure Info */}
            <Card>
              <CardHeader>
                <CardTitle>Trip Structure</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                  <span className="text-gray-600">Deadhead Leg</span>
                </div>
                <p className="text-xs text-gray-500 ml-5">
                  Current location → Pickup (empty truck)
                </p>

                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span className="text-gray-600">Pickup Activity</span>
                </div>
                <p className="text-xs text-gray-500 ml-5">
                  Loading freight at pickup location
                </p>

                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="text-gray-600">Loaded Leg</span>
                </div>
                <p className="text-xs text-gray-500 ml-5">
                  Pickup → Delivery (carrying freight)
                </p>

                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                  <span className="text-gray-600">Delivery Activity</span>
                </div>
                <p className="text-xs text-gray-500 ml-5">
                  Unloading freight at delivery location
                </p>
              </CardContent>
            </Card>

            {/* HOS Guidelines */}
            <Card>
              <CardHeader>
                <CardTitle>HOS Guidelines</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Max Driving</span>
                  <span className="font-medium">11 hours</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Max On-Duty</span>
                  <span className="font-medium">14 hours</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Required Break</span>
                  <span className="font-medium">30 min / 8 hrs</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Daily Reset</span>
                  <span className="font-medium">10 hours</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </form>
      </div>
    </Layout>
  );
}
