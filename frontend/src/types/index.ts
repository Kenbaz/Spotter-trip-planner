/* eslint-disable @typescript-eslint/no-explicit-any */

// User and auth types
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role_display: string;
  is_driver: boolean;
  is_fleet_manager: boolean;
  is_super_admin: boolean;
  is_active_driver: boolean;
  employee_id: string;
  phone_number?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  hire_date?: string;
  date_joined: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface TokenRefreshResponse {
  access: string;
}

// Vehicle Types
export interface Vehicle {
  id: number;
  unit_number: string;
  year: number;
  make: string;
  model: string;
  vehicle_type: "truck" | "trailer" | "truck_trailer";
  maintenance_status: "active" | "maintenance" | "out of service";
  is_active: boolean;
}

export interface VehicleAssignment {
  id: number;
  driver_name: string;
  vehicle_info: Vehicle;
  start_date: string;
  assignment_type: "permanent" | "temporary";
  is_active: boolean;
}

// Trip Types
export interface Trip {
  trip_id: string;
  driver_name: string;
  driver_username: string;
  vehicle_info: Vehicle | null;
  company_name: string;
  created_by_name: string;
  status: "draft" | "planned" | "in_progress" | "completed" | "cancelled";
  status_display: string;
  is_editable: boolean;
  current_address: string;
  current_latitude: number;
  current_longitude: number;
  destination_address: string;
  destination_latitude: number;
  destination_longitude: number;
  departure_datetime: string;
  max_fuel_distance_miles: number;
  pickup_duration_minutes: number;
  delivery_duration_minutes: number;
  total_distance_miles?: number;
  total_driving_time?: number;
  estimated_arrival_time?: string;
  is_hos_compliant: boolean;
  compliance_summary: ComplianceSummary;
  created_at: string;
  updated_at: string;
  stops: Stop[];
  hos_periods: HOSPeriod[];
  route?: Route;
  compliance_reports: ComplianceReport[];
}

export interface TripListItem {
  trip_id: string;
  driver_name: string;
  vehicle_unit?: string;
  current_address: string;
  destination_address: string;
  departure_datetime: string;
  estimated_arrival_time?: string;
  total_distance_miles?: number;
  total_driving_time?: number;
  status: string;
  status_display: string;
  is_hos_compliant: boolean;
  stops_count: number;
  compliance_status: string;
  created_at: string;
}

export interface CreateTripRequest {
  current_address: string;
  current_latitude: number;
  current_longitude: number;
  destination_address: string;
  destination_latitude: number;
  destination_longitude: number;
  departure_datetime: string;
  max_fuel_distance_miles?: number;
  pickup_duration_minutes?: number;
  delivery_duration_minutes?: number;
}

// Route and Stop Types
export interface Stop {
  id: number;
  stop_type:
    | "pickup"
    | "delivery"
    | "fuel"
    | "rest"
    | "mandatory_break"
    | "daily_reset"
    | "fuel_and_break";
  stop_type_display: string;
  sequence_order: number;
  address: string;
  latitude?: number;
  longitude?: number;
  arrival_time: string;
  departure_time: string;
  duration_minutes: number;
  distance_from_origin_miles: number;
  distance_to_next_stop_miles?: number;
  is_required_for_compliance: boolean;
  is_optimized_stop: boolean;
  optimization_notes?: string;
}

export interface Route {
  id: number;
  route_geometry: any;
  route_instructions: any[];
  total_distance_meters: number;
  distance_miles: number;
  total_duration_seconds: number;
  duration_hours: number;
  external_route_id: string;
  api_provider: string;
  calculated_by_name?: string;
  created_at: string;
}

// HOS and Compliance Types
export interface HOSPeriod {
  id: number;
  duty_status: "off_duty" | "sleeper_berth" | "driving" | "on_duty_not_driving";
  duty_status_display: string;
  start_datetime: string;
  end_datetime: string;
  duration_minutes: number;
  duration_hours: number;
  start_location: string;
  end_location: string;
  distance_traveled_miles?: number;
  is_compliant: boolean;
  compliance_notes?: string;
  verified_by_driver: boolean;
}

export interface ComplianceReport {
  id: number;
  is_compliant: boolean;
  compliance_score: number;
  total_driving_hours: number;
  total_on_duty_hours: number;
  total_off_duty_hours: number;
  violations: Violation[];
  warnings: Warning[];
  violations_count: number;
  warnings_count: number;
  required_30min_breaks: number;
  scheduled_30min_breaks: number;
  required_daily_resets: number;
  scheduled_daily_resets: number;
  generated_by_name?: string;
  reviewed_by_fleet_manager: boolean;
  created_at: string;
}

export interface ComplianceSummary {
  is_compliant: boolean;
  score: number;
  violations_count: number;
}

export interface Violation {
  type: string;
  description: string;
  details?: any;
}

export interface Warning {
  type: string;
  message: string;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  error?: string;
  details?: string;
  data?: T;
}

export interface TripCalculationRequest {
  optimize_route?: boolean;
  generate_eld_logs?: boolean;
  include_fuel_optimization?: boolean;
}

export interface TripCalculationResponse {
  success: boolean;
  trip_id: string;
  feasibility: any;
  route_plan: any;
  route_data: any;
  optimization_applied: boolean;
  message: string;
  error?: string;
  details?: string;
}

// Geocoding Types
export interface GeocodingRequest {
  address: string;
}

export interface GeocodingResponse {
  success: boolean;
  latitude?: number;
  longitude?: number;
  formatted_address?: string;
  confidence?: number;
  country?: string;
  region?: string;
  error?: string;
}

// ELD Log Types
export interface ELDLogRequest {
  export_format?: "json" | "pdf_data";
  include_validation?: boolean;
}

export interface ELDLogResponse {
  success: boolean;
  trip_id: string;
  total_days: number;
  log_date_range: {
    start: string;
    end: string;
  };
  daily_logs: DailyLog[];
  summary: any;
  validation_results?: any;
  generated_at: string;
  error?: string;
}

export interface DailyLog {
  log_date: string;
  driver_name: string;
  carrier_name: string;
  vehicle_id: string;
  grid_data: any[];
  log_entries: any[];
  daily_totals: any;
  location_remarks: any[];
  certification: any;
}

// Utility Types
export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface AddressSuggestion {
  formatted_address: string;
  latitude: number;
  longitude: number;
  confidence: number;
}
