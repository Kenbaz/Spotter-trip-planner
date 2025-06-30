import { useState, useCallback } from "react";
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
import { AddressAutocomplete } from "../components/UI/AddressAutocomplete";
import {
  Clock,
  AlertCircle,
  Calculator,
  ArrowLeft,
  Navigation,
  Route as RouteIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useCreateTrip, useReverseGeocodeMutation } from "../hooks/useTripQueries";
import { useAddressInput } from "../hooks/useAddressInput";
import type { CreateTripRequest, TripSettings, CurrentDriverStatus } from "../types";
import { DriverStatusCard } from "../components/UI/DriverStatusCard";


interface FormErrors {
  [key: string]: string;
}


export function CreateTripPage() {
  const navigate = useNavigate();
  const createTripMutation = useCreateTrip();
  const reverseGeocodeMutation = useReverseGeocodeMutation();

  // Enhanced address inputs
  const currentLocation = useAddressInput();
  const pickupLocation = useAddressInput();
  const deliveryLocation = useAddressInput();

  const [tripSettings, setTripSettings] = useState<TripSettings>({
    departure_datetime: "",
    max_fuel_distance_miles: 1000,
    pickup_duration_minutes: 60,
    delivery_duration_minutes: 60,
  });

  const [currentDriverStatus, setCurrentDriverStatus] =
    useState<CurrentDriverStatus | null>(null);
  const [isStatusLoaded, setIsStatusLoaded] = useState(false);

  const [errors, setErrors] = useState<FormErrors>({});

  const isFormDisabled = createTripMutation.isPending || !isStatusLoaded;


  const handleDriverStatusLoad = useCallback((status: CurrentDriverStatus) => {
    setCurrentDriverStatus(status);
    setIsStatusLoaded(true);
    // Clear any previous driver status errors
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors.driver_status;
      return newErrors;
    });
  }, []);


  const prepareDriverCycleData = useCallback((status: CurrentDriverStatus) => {
    return {
      trip_start_cycle_hours: status.total_cycle_hours,
      trip_start_driving_hours: status.today_driving_hours,
      trip_start_on_duty_hours: status.today_on_duty_hours,
      trip_start_duty_status: status.current_duty_status,
      trip_start_status_time: status.current_status_start,
      trip_start_last_break: status.last_30min_break_end || undefined,
    };
  }, []);

  // Get user's current location using browser geolocation
  const handleGetCurrentLocation = useCallback(() => {
    if ("geolocation" in navigator) {
      // Clear any previous errors
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors.current_address;
        return newErrors;
      });

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;
          
          try {
            // Reverse geocode to get human-readable address from coordinates
            const result = await reverseGeocodeMutation.mutateAsync({
              latitude,
              longitude,
            });

            if (result.success && result.formatted_address) {
              // Use the formatted address from reverse geocoding
              currentLocation.handleCoordinatesChange(
                latitude,
                longitude,
                result.formatted_address
              );
            } else {
              // Fallback to coordinates if reverse geocoding fails
              currentLocation.handleCoordinatesChange(
                latitude,
                longitude,
                `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`
              );
            }
          } catch (error) {
            console.error("Reverse geocoding failed:", error);
            // Fallback to coordinates
            currentLocation.handleCoordinatesChange(
              latitude,
              longitude,
              `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(
                4
              )})`
            );
          }
        },
        (error) => {
          console.error("Error getting location:", error);
          let errorMessage = "Unable to get your current location";
          
          switch (error.code) {
            case error.PERMISSION_DENIED:
              errorMessage =
                "Location access denied. Please enable location permissions.";
              break;
            case error.POSITION_UNAVAILABLE:
              errorMessage = "Location information unavailable.";
              break;
            case error.TIMEOUT:
              errorMessage = "Location request timed out.";
              break;
          }
          setErrors(prev => ({
            ...prev,
            current_address: errorMessage,
          }));
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000, // 5 minutes
        }
      );
    } else {
      setErrors((prev) => ({
        ...prev,
        current_address: "Geolocation is not supported by your browser.",
      }));
    }
  }, [currentLocation, reverseGeocodeMutation]);


  // const prepareDriverCycleData = (driverCycle: DriverCycleFormData) => {
  //   const safeParseFloat = (value: number | string): number => {
  //     if (typeof value === "number") return value;
  //     const parsed = parseFloat(value.toString());
  //     return isNaN(parsed) ? 0 : parsed;
  //   };

  //   // Helper function to format datetime to ISO string
  //   const formatDateTime = (dateTimeValue: string): string => {
  //     if (!dateTimeValue) return "";

  //     try {
  //       const date = new Date(dateTimeValue);
  //       if (isNaN(date.getTime())) {
  //         throw new Error("Invalid date");
  //       }
  //       return date.toISOString();
  //     } catch (error) {
  //       console.error("Error formatting datetime:", error);
  //       return "";
  //     }
  //   };

  //   return {
  //     current_cycle_hours_used: safeParseFloat(
  //       driverCycle.current_cycle_hours_used
  //     ),
  //     hours_driven_today: safeParseFloat(driverCycle.hours_driven_today),
  //     hours_on_duty_today: safeParseFloat(driverCycle.hours_on_duty_today),
  //     current_duty_status: driverCycle.current_duty_status,
  //     current_status_start_time: formatDateTime(
  //       driverCycle.current_status_start_time
  //     ),
  //     last_break_end_time: driverCycle.last_break_end_time
  //       ? formatDateTime(driverCycle.last_break_end_time)
  //       : undefined,
  //   };
  // };


  // const validateDriverCycleData = (
  //   driverCycle: DriverCycleFormData
  // ): string[] => {
  //   const errors: string[] = [];

  //   // Validate numeric fields
  //   if (
  //     driverCycle.current_cycle_hours_used < 0 ||
  //     driverCycle.current_cycle_hours_used > 70
  //   ) {
  //     errors.push("70-Hour Cycle Used must be between 0 and 70 hours");
  //   }

  //   if (
  //     driverCycle.hours_driven_today < 0 ||
  //     driverCycle.hours_driven_today > 11
  //   ) {
  //     errors.push("Hours Driven Today must be between 0 and 11 hours");
  //   }

  //   if (
  //     driverCycle.hours_on_duty_today < 0 ||
  //     driverCycle.hours_on_duty_today > 14
  //   ) {
  //     errors.push("Hours On-Duty Today must be between 0 and 14 hours");
  //   }

  //   if (driverCycle.hours_driven_today > driverCycle.hours_on_duty_today) {
  //     errors.push("Hours Driven Today cannot exceed Hours On-Duty Today");
  //   }

  //   if (
  //     driverCycle.hours_on_duty_today > driverCycle.current_cycle_hours_used
  //   ) {
  //     errors.push("Hours On-Duty Today cannot exceed total cycle hours used");
  //   }

  //   // Validate datetime fields
  //   if (!driverCycle.current_status_start_time) {
  //     errors.push("Current Status Start Time is required");
  //   } else {
  //     try {
  //       const statusStartDate = new Date(driverCycle.current_status_start_time);
  //       if (isNaN(statusStartDate.getTime())) {
  //         errors.push("Current Status Start Time is invalid");
  //       } else if (statusStartDate > new Date()) {
  //         errors.push("Current Status Start Time cannot be in the future");
  //       }
  //     } catch {
  //       errors.push("Current Status Start Time is invalid");
  //     }
  //   }

  //   if (driverCycle.last_break_end_time) {
  //     try {
  //       const breakEndDate = new Date(driverCycle.last_break_end_time);
  //       if (isNaN(breakEndDate.getTime())) {
  //         errors.push("Last Break End Time is invalid");
  //       } else if (breakEndDate > new Date()) {
  //         errors.push("Last Break End Time cannot be in the future");
  //       }
  //     } catch {
  //       errors.push("Last Break End Time is invalid");
  //     }
  //   }

  //   return errors;
  // };


  const validateForm = useCallback(() => {
    const newErrors: FormErrors = {};

    // Validate driver status
    if (!currentDriverStatus) {
      newErrors.driver_status =
        "Driver HOS status must be loaded before creating a trip";
      return newErrors;
    }

    // Validate locations
    if (!currentLocation.isValid) {
      newErrors.current_address =
        "Please enter and verify your current location";
    }
    if (!pickupLocation.isValid) {
      newErrors.pickup_address = "Please enter and verify the pickup location";
    }
    if (!deliveryLocation.isValid) {
      newErrors.delivery_address =
        "Please enter and verify the delivery location";
    }

    // Validate trip settings
    if (!tripSettings.departure_datetime) {
      newErrors.departure = "Departure date and time is required";
      return newErrors;
    }

    // Validate departure time is not in the past
    const departureDate = new Date(tripSettings.departure_datetime);
    if (departureDate <= new Date()) {
      newErrors.departure = "Departure time must be in the future";
      return newErrors;
    }

    // Check if driver can start trip
    if (currentDriverStatus.needs_immediate_break) {
      newErrors.compliance =
        "You must take a 30-minute break before starting a new trip";
      return newErrors;
    }

    return newErrors;
  }, [
    currentDriverStatus,
    currentLocation,
    pickupLocation,
    deliveryLocation,
    tripSettings,
  ]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setErrors({});

    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    // Validate driver cycle data
    // const driverCycleErrors = validateDriverCycleData(driverCycle);
    // if (driverCycleErrors.length > 0) {
    //   setErrors({
    //     driver_cycle: driverCycleErrors.join(", "),
    //   });
    //   return;
    // }

    // Prepare properly formatted data
    // const preparedDriverCycle = prepareDriverCycleData(driverCycle);

    try {
      const tripData: CreateTripRequest = {
        current_address: currentLocation.addressData.address,
        current_latitude: currentLocation.addressData.latitude!,
        current_longitude: currentLocation.addressData.longitude!,
        pickup_address: pickupLocation.addressData.address,
        pickup_latitude: pickupLocation.addressData.latitude!,
        pickup_longitude: pickupLocation.addressData.longitude!,
        delivery_address: deliveryLocation.addressData.address,
        delivery_latitude: deliveryLocation.addressData.latitude!,
        delivery_longitude: deliveryLocation.addressData.longitude!,
        departure_datetime: new Date(
          tripSettings.departure_datetime
        ).toISOString(),
        max_fuel_distance_miles:
          Number(tripSettings.max_fuel_distance_miles) || 1000,
        pickup_duration_minutes:
          Number(tripSettings.pickup_duration_minutes) || 60,
        delivery_duration_minutes:
          Number(tripSettings.delivery_duration_minutes) || 60,
        // Driver cycle data
        ...prepareDriverCycleData(currentDriverStatus!),
      };

      console.log("Creating trip with starting conditions:", tripData);

      const result = await createTripMutation.mutateAsync(tripData);

      if (result.success) {
        navigate(`/trips/${result.trip.trip_id}`);
      }
    } catch (error) {
      console.error("Error creating trip:", error);

      // Handle API validation errors
      if (error && typeof error === "object" && "response" in error) {
        const apiError = error as {
          response?: { data?: Record<string, unknown> };
        };
        if (apiError.response?.data) {
          const responseData = apiError.response.data;

          if (
            typeof responseData === "object" &&
            responseData !== null &&
            "error" in responseData
          ) {
            setErrors({
              api: String(responseData.error),
            });
          } else {
            // Handle field-specific validation errors from Django
            const fieldErrors: FormErrors = {};
            Object.entries(responseData).forEach(([field, messages]) => {
              if (Array.isArray(messages)) {
                fieldErrors[field] = messages.join(", ");
              } else if (typeof messages === "string") {
                fieldErrors[field] = messages;
              } else {
                fieldErrors[field] = String(messages);
              }
            });
            setErrors(fieldErrors);
          }
        }
      } else {
        setErrors({
          general: "An unexpected error occurred. Please try again.",
        });
      }
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center space-x-4">
          <Link to="/trips">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Trips
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Plan New Trip</h1>
            <p className="text-gray-600">
              Create a new HOS-compliant trip with smart address autocomplete
            </p>
          </div>
        </div>

        {/* Current Driver HOS Status */}
        <DriverStatusCard
          onStatusLoad={handleDriverStatusLoad}
          showActions={false}
          className="mb-6"
        />

        {/* Show warning if driver status indicates issues */}
        {currentDriverStatus?.needs_immediate_break && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-4">
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-800">Break Required</h4>
                  <p className="text-sm text-red-700 mt-1">
                    You must take a 30-minute break before starting a new trip.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Trip Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Trip Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <RouteIcon className="w-5 h-5" />
                <span>Trip Details</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-6">
                {/* Current Location with GPS button */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                  <div className="md:col-span-3">
                    <AddressAutocomplete
                      label="Current Location"
                      value={currentLocation.addressData.address}
                      onChange={currentLocation.handleAddressChange}
                      onCoordinatesChange={
                        currentLocation.handleCoordinatesChange
                      }
                      placeholder="Enter your current location..."
                      error={errors.current_address}
                      disabled={isFormDisabled}
                      required
                      autoFocus
                    />
                  </div>
                  <div>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={handleGetCurrentLocation}
                      disabled={isFormDisabled}
                      className="w-full"
                      title="Current Address"
                    >
                      <Navigation className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Pickup Location */}
                <AddressAutocomplete
                  label="Pickup Location"
                  value={pickupLocation.addressData.address}
                  onChange={pickupLocation.handleAddressChange}
                  onCoordinatesChange={pickupLocation.handleCoordinatesChange}
                  placeholder="Enter pickup location..."
                  error={errors.pickup_address}
                  disabled={isFormDisabled}
                  required
                />

                {/* Delivery Location */}
                <AddressAutocomplete
                  label="Delivery Location"
                  value={deliveryLocation.addressData.address}
                  onChange={deliveryLocation.handleAddressChange}
                  onCoordinatesChange={deliveryLocation.handleCoordinatesChange}
                  placeholder="Enter delivery location..."
                  error={errors.delivery_address}
                  disabled={isFormDisabled}
                  required
                />
              </div>

              {/* Departure Time and Settings */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center space-x-2">
                    <Clock className="w-4 h-4" />
                    <span>Departure Date & Time</span>
                  </label>
                  <Input
                    type="datetime-local"
                    value={tripSettings.departure_datetime}
                    onChange={(e) =>
                      setTripSettings((prev) => ({
                        ...prev,
                        departure_datetime: e.target.value,
                      }))
                    }
                    disabled={isFormDisabled}
                    error={errors.departure_datetime}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Max Fuel Distance (miles)
                  </label>
                  <Input
                    type="number"
                    value={tripSettings.max_fuel_distance_miles}
                    onChange={(e) =>
                      setTripSettings((prev) => ({
                        ...prev,
                        max_fuel_distance_miles:
                          parseInt(e.target.value) || 1000,
                      }))
                    }
                    disabled={isFormDisabled}
                    min="200"
                    max="1200"
                  />
                </div>
              </div>

              {/* Duration Settings */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Pickup Duration (minutes)
                  </label>
                  <Input
                    type="number"
                    value={tripSettings.pickup_duration_minutes}
                    onChange={(e) =>
                      setTripSettings((prev) => ({
                        ...prev,
                        pickup_duration_minutes: parseInt(e.target.value) || 60,
                      }))
                    }
                    disabled={isFormDisabled}
                    min="15"
                    max="480"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Delivery Duration (minutes)
                  </label>
                  <Input
                    type="number"
                    value={tripSettings.delivery_duration_minutes}
                    onChange={(e) =>
                      setTripSettings((prev) => ({
                        ...prev,
                        delivery_duration_minutes:
                          parseInt(e.target.value) || 60,
                      }))
                    }
                    disabled={isFormDisabled}
                    min="15"
                    max="480"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit Actions */}
          <div className="flex justify-end space-x-4">
            <Link to="/trips">
              <Button
                type="button"
                variant="secondary"
                disabled={isFormDisabled}
              >
                Cancel
              </Button>
            </Link>
            <Button
              type="submit"
              disabled={
                isFormDisabled || currentDriverStatus?.needs_immediate_break
              }
              isLoading={createTripMutation.isPending}
              leftIcon={<Calculator className="w-4 h-4" />}
            >
              {createTripMutation.isPending
                ? "Creating Trip..."
                : currentDriverStatus?.needs_immediate_break
                ? "Break Required"
                : !isStatusLoaded
                ? "Loading Status..."
                : "Create Trip"
              }
            </Button>
          </div>

          {/* Global Form Errors */}
          {Object.keys(errors).length > 0 && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-medium text-red-800">
                      Please fix the following errors:
                    </h4>
                    <ul className="mt-2 text-sm text-red-700 space-y-1">
                      {Object.entries(errors).map(([field, error]) => (
                        <li key={field}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </form>
      </div>
    </Layout>
  );
}
