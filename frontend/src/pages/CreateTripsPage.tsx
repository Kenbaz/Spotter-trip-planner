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
  Save,
  Calculator,
  ArrowLeft,
} from "lucide-react";
import { Link } from "react-router-dom";

export function CreateTripPage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    current_address: "",
    current_latitude: "",
    current_longitude: "",
    destination_address: "",
    destination_latitude: "",
    destination_longitude: "",
    departure_datetime: "",
    max_fuel_distance_miles: 1000,
    pickup_duration_minutes: 60,
    delivery_duration_minutes: 60,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.current_address.trim()) {
      newErrors.current_address = "Origin address is required";
    }
    if (!formData.destination_address.trim()) {
      newErrors.destination_address = "Destination address is required";
    }
    if (!formData.departure_datetime) {
      newErrors.departure_datetime = "Departure time is required";
    } else {
      const departureDate = new Date(formData.departure_datetime);
      if (departureDate <= new Date()) {
        newErrors.departure_datetime = "Departure time must be in the future";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    try {
      // TODO: Implement API call to create trip
      console.log("Creating trip:", formData);

      // Mock success - navigate to trip detail
      setTimeout(() => {
        navigate("/trips/550e8400-e29b-41d4-a716-446655440000");
      }, 1000);
    } catch (error) {
      console.error("Error creating trip:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    setIsLoading(true);
    try {
      // TODO: Implement API call to save draft
      console.log("Saving draft:", formData);
      navigate("/trips");
    } catch (error) {
      console.error("Error saving draft:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGeocode = async (field: "origin" | "destination") => {
    const address =
      field === "origin"
        ? formData.current_address
        : formData.destination_address;

    if (!address.trim()) {
      return;
    }

    try {
      // TODO: Implement geocoding API call
      console.log("Geocoding:", address);

      // Mock geocoding result
      const mockCoords = {
        latitude: field === "origin" ? 32.7767 : 29.7604,
        longitude: field === "origin" ? -96.797 : -95.3698,
      };

      if (field === "origin") {
        setFormData((prev) => ({
          ...prev,
          current_latitude: mockCoords.latitude.toString(),
          current_longitude: mockCoords.longitude.toString(),
        }));
      } else {
        setFormData((prev) => ({
          ...prev,
          destination_latitude: mockCoords.latitude.toString(),
          destination_longitude: mockCoords.longitude.toString(),
        }));
      }
    } catch (error) {
      console.error("Geocoding error:", error);
    }
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

        <form
          onSubmit={handleSubmit}
          className="grid grid-cols-1 lg:grid-cols-3 gap-6"
        >
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Route Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MapPin className="w-5 h-5 mr-2" />
                  Route Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex space-x-2">
                    <Input
                      label="Origin Address"
                      value={formData.current_address}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          current_address: e.target.value,
                        })
                      }
                      placeholder="Enter pickup location"
                      error={errors.current_address}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => handleGeocode("origin")}
                      className="mt-6"
                      disabled={!formData.current_address.trim()}
                    >
                      <MapPin className="w-4 h-4" />
                    </Button>
                  </div>
                  {formData.current_latitude && formData.current_longitude && (
                    <p className="text-xs text-green-600 mt-1">
                      ✓ Coordinates: {formData.current_latitude},{" "}
                      {formData.current_longitude}
                    </p>
                  )}
                </div>

                <div>
                  <div className="flex space-x-2">
                    <Input
                      label="Destination Address"
                      value={formData.destination_address}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          destination_address: e.target.value,
                        })
                      }
                      placeholder="Enter delivery location"
                      error={errors.destination_address}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => handleGeocode("destination")}
                      className="mt-6"
                      disabled={!formData.destination_address.trim()}
                    >
                      <MapPin className="w-4 h-4" />
                    </Button>
                  </div>
                  {formData.destination_latitude &&
                    formData.destination_longitude && (
                      <p className="text-xs text-green-600 mt-1">
                        ✓ Coordinates: {formData.destination_latitude},{" "}
                        {formData.destination_longitude}
                      </p>
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
                    setFormData({
                      ...formData,
                      departure_datetime: e.target.value,
                    })
                  }
                  error={errors.departure_datetime}
                  min={new Date().toISOString().slice(0, 16)}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Pickup Duration (minutes)"
                    type="number"
                    value={formData.pickup_duration_minutes}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        pickup_duration_minutes: parseInt(e.target.value) || 0,
                      })
                    }
                    min="15"
                    max="240"
                    helperText="Time needed for pickup activities"
                  />

                  <Input
                    label="Delivery Duration (minutes)"
                    type="number"
                    value={formData.delivery_duration_minutes}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        delivery_duration_minutes:
                          parseInt(e.target.value) || 0,
                      })
                    }
                    min="15"
                    max="240"
                    helperText="Time needed for delivery activities"
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
                    setFormData({
                      ...formData,
                      max_fuel_distance_miles: parseInt(e.target.value) || 0,
                    })
                  }
                  min="200"
                  max="1200"
                  helperText="Maximum distance between fuel stops"
                />
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Preview */}
            <Card>
              <CardHeader>
                <CardTitle>Trip Preview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600">Origin</p>
                  <p className="font-medium">
                    {formData.current_address || "Not set"}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-600">Destination</p>
                  <p className="font-medium">
                    {formData.destination_address || "Not set"}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-600">Departure</p>
                  <p className="font-medium">
                    {formData.departure_datetime
                      ? new Date(formData.departure_datetime).toLocaleString()
                      : "Not set"}
                  </p>
                </div>

                <div className="pt-3 border-t border-gray-200">
                  <p className="text-sm text-gray-600">Estimated Distance</p>
                  <p className="font-medium text-gray-400">
                    Calculate route to see
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-600">Estimated Duration</p>
                  <p className="font-medium text-gray-400">
                    Calculate route to see
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardContent className="space-y-3">
                <Button
                  type="submit"
                  className="w-full"
                  isLoading={isLoading}
                  leftIcon={<Calculator className="w-4 h-4" />}
                  disabled={
                    !formData.current_address ||
                    !formData.destination_address ||
                    !formData.departure_datetime
                  }
                >
                  Calculate Route & HOS
                </Button>

                <Button
                  type="button"
                  variant="secondary"
                  className="w-full"
                  onClick={handleSaveDraft}
                  leftIcon={<Save className="w-4 h-4" />}
                  disabled={isLoading}
                >
                  Save as Draft
                </Button>

                <div className="text-center">
                  <Link to="/trips">
                    <Button variant="ghost" size="sm">
                      Cancel
                    </Button>
                  </Link>
                </div>
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
