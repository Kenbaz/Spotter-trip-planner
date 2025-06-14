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

  pickup_address: string;
  pickup_latitude: number;
  pickup_longitude: number;

  delivery_address: string;
  delivery_latitude: number;
  delivery_longitude: number;

  departure_datetime: string;

  total_distance_miles?: number;
  deadhead_distance_miles?: number;
  loaded_distance_miles?: number;
  total_driving_time?: number;
  deadhead_driving_time?: number;
  loaded_driving_time?: number;
  estimated_arrival_time?: string;
  estimated_pickup_time?: string;

  is_hos_compliant: boolean;
  compliance_summary: ComplianceSummary;
  created_at: string;
  updated_at: string;

  trip_legs: {
    deadhead: {
      origin: string;
      destination: string;
      distance_miles: number;
      driving_time_hours: number;
    };
    loaded: {
      origin: string;
      destination: string;
      distance_miles: number;
      driving_time_hours: number;
    };
  };

  stops: Stop[];
  hos_periods: HOSPeriod[];
  route?: Route;
  compliance_reports: ComplianceReport[];
}

export interface DriverCycleStatus {
  cycle_hours_used: number;
  remaining_cycle_hours: number;
  today_driving_hours: number;
  remaining_driving_today: number;
  today_on_duty_hours: number;
  remaining_on_duty_today: number;
  current_duty_status:
    | "off_duty"
    | "sleeper_berth"
    | "driving"
    | "on_duty_not_driving";
  needs_immediate_break: boolean;
  needs_daily_reset: boolean;
  needs_cycle_reset: boolean;
  compliance_warnings: ComplianceWarning[];
}

export interface ComplianceWarning {
  type:
    | "immediate_break_required"
    | "approaching_daily_driving_limit"
    | "approaching_daily_on_duty_limit"
    | "approaching_cycle_limit";
  message: string;
  severity: "critical" | "warning";
}

export interface CurrentStatusImpact {
  cycle_hours_used: number;
  remaining_cycle_hours: number;
  today_driving_hours: number;
  remaining_driving_today: number;
  today_on_duty_hours: number;
  remaining_on_duty_today: number;
  current_duty_status: string;
  needs_immediate_break: boolean;
  needs_daily_reset: boolean;
  needs_cycle_reset: boolean;
  compliance_warnings: ComplianceWarning[];
}

export interface TripListItem {
  trip_id: string;
  driver_name: string;
  vehicle_unit?: string;

  current_address: string;
  pickup_address: string;
  delivery_address: string;

  departure_datetime: string;
  estimated_arrival_time?: string;
  estimated_pickup_time?: string;

  total_distance_miles?: number;
  deadhead_distance_miles?: number;
  loaded_distance_miles?: number;
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

  pickup_address: string;
  pickup_latitude: number;
  pickup_longitude: number;

  delivery_address: string;
  delivery_latitude: number;
  delivery_longitude: number;

  departure_datetime: string;
  max_fuel_distance_miles?: number;
  pickup_duration_minutes?: number;
  delivery_duration_minutes?: number;

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

// Route and Stop Types
export interface Stop {
  id: number;
  stop_type:
    | "trip_start"
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

  leg_type?: "deadhead" | "loaded" | "pickup" | "delivery" | "transition" | "pre_trip";
  break_reason?: string;
}

export interface Route {
  id: number;
  route_geometry: RouteGeometry;
  route_instructions: RouteInstruction[];
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

  leg_type?: "deadhead" | "loaded" | "pickup" | "delivery";
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
  details?: Record<string, unknown>;
}

export interface Warning {
  type: string;
  message: string;
}

// API Response Types
export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  error?: string;
  details?: string;
  data?: T;
}

export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next?: string;
  previous?: string;
}

export interface TripCalculationRequest {
  optimize_route?: boolean;
  generate_eld_logs?: boolean;
  include_fuel_optimization?: boolean;
}

// Geocoding Types
export interface GeocodingRequest {
  address: string;
}

// ELD Log Types
export interface ELDLogRequest {
  export_format?: "json" | "pdf_data";
  include_validation?: boolean;
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

export interface RouteGeometry {
  type: "LineString";
  coordinates: number[][];
}

export interface RouteInstruction { 
  Instruction: string;
  distance_meters: number;
  duration_seconds: number;
  type: number;
  name: string;
  way_points: number[];
}

export interface RouteWayPoint { 
  sequence: number;
  latitude: number;
  longitude: number;
  elevation?: number;
}

export interface ElevationPoint {
  distance: number;
  elevation: number;
  grade?: number;
}

export interface RouteData {
  success: boolean;
  provider: string;
  route_id: string;
  distance_meters: number;
  distance_miles: number;
  duration_seconds: number;
  duration_hours: number;
  geometry: RouteGeometry;
  instructions: RouteInstruction[];
  origin_lat: number;
  origin_lng: number;
  destination_lat: number;
  destination_lng: number;
  surface_type?: number[];
  tollways: number[];
  waypoints: RouteWayPoint[];
  elevation_profile: ElevationPoint[];
}

// Trip planning types
export interface RequiredBreak {
  type: "mandatory_break" | "daily_reset";
  duration_minutes: number;
  after_driving_hours?: number;
  after_hours?: number;
  break_number?: number;
  day_number?: number;
  description?: string;
}

export interface TripFeasibility {
  is_feasible: boolean;
  required_breaks: RequiredBreak[];
  violations: FeasibilityViolation[];
  estimated_completion_time: string;
  modifications_needed: string[];
  total_trip_hours: number;
  total_break_hours: number;
}

export interface FeasibilityViolation {
  type: "daily_driving_limit_exceeded" | "daily_on_duty_limit_exceeded";
  details: {
    driving_hours?: number;
    limit?: number;
    violation_hours?: number;
    on_duty_hours?: number;
  };
}

export interface RoutePlanStop {
  type:
    | "pickup"
    | "delivery"
    | "fuel"
    | "mandatory_break"
    | "daily_reset"
    | "fuel_and_break";
  address: string;
  latitude: number;
  longitude: number;
  arrival_time: string;
  departure_time?: string;
  duration_minutes: number;
  distance_from_origin: number;
  sequence_order: number;
  is_required_for_compliance: boolean;
  combined_functions?: string[];
  fuel_stop_number?: number;
  break_reason?: string;
}

export interface HOSPeriodPlan {
  duty_status: "off_duty" | "sleeper_berth" | "driving" | "on_duty_not_driving";
  start_datetime: string;
  end_datetime: string;
  duration_minutes: number;
  distance_traveled_miles?: number;
  start_location: string;
  end_location: string;
}

export interface RoutePlan {
  stops: RoutePlanStop[];
  hos_periods: HOSPeriodPlan[];
  total_duration_hours: number;
  estimated_pickup_time: string;
  estimated_arrival: string;
  optimization_notes: string[];
  current_status_impact?: CurrentStatusImpact;
}

// ELD Log Types
export interface GridPoint {
  time: string;
  minute_of_day: number;
  duty_status: string;
  duty_status_symbol: number;
  grid_row: number;
  grid_column: number;
}

export interface LogEntry {
  start_time: string;
  end_time: string;
  duty_status: string;
  duty_status_symbol: number;
  duration_minutes: number;
  location: string;
  odometer_start: number;
  odometer_end: number;
  vehicle_miles: number;
  remarks: string;
}

export interface DailyTotals {
  off_duty: number;
  sleeper_berth: number;
  driving: number;
  on_duty_not_driving: number;
  total_on_duty: number;
  total_driving: number;
}

export interface LocationRemark {
  time: string;
  location: string;
  type: string;
  duty_status: string;
  odometer: number;
}

export interface LogCertification {
  driver_signature: string | null;
  certification_date: string | null;
  is_certified: boolean;
}

export interface DailyELDLog {
  log_date: string;
  driver_name: string;
  carrier_name: string;
  vehicle_id: string;
  grid_data: GridPoint[];
  log_entries: LogEntry[];
  daily_totals: DailyTotals;
  location_remarks: LocationRemark[];
  certification: LogCertification;
}

export interface ELDLogSummary {
  trip_id: string;
  origin: string;
  destination: string;
  departure_time: string;
  estimated_arrival: string | null;
  total_distance_miles: number;
  total_driving_hours: number;
  total_on_duty_hours: number;
  trip_duration_hours: number;
  calculated_distance_miles: number;
  number_of_stops: number;
  number_of_duty_periods: number;
  hos_compliance_status: boolean;
}

export interface ValidationResult {
  is_compliant: boolean;
  violations: ValidationViolation[];
  warnings: ValidationWarning[];
  daily_validations: DailyValidation[];
}

export interface ValidationViolation {
  type:
    | "daily_driving_limit"
    | "daily_on_duty_limit"
    | "insufficient_off_duty"
    | "missing_30min_break";
  description: string;
  actual: number;
  limit?: number;
  required?: number;
}

export interface ValidationWarning {
  type: "approaching_driving_limit" | "approaching_on_duty_limit";
  description: string;
}

export interface DailyValidation {
  log_date: string;
  is_compliant: boolean;
  violations: ValidationViolation[];
  warnings: ValidationWarning[];
  totals_checked: DailyTotals;
}

// PDF Export Types
export interface GridVisualization {
  grid_matrix: number[][];
  row_labels: string[];
  column_labels: string[];
  legend: Record<
    number,
    {
      symbol: string;
      description: string;
      color: string;
    }
  >;
}

export interface PDFPageData {
  log_date: string;
  driver_info: {
    name: string;
    license_number: string;
    carrier: string;
  };
  vehicle_info: {
    vehicle_id: string;
    license_plate: string;
    vin: string;
  };
  grid_visualization: GridVisualization;
  duty_periods: LogEntry[];
  daily_totals: DailyTotals;
  location_remarks: LocationRemark[];
  certification_section: LogCertification;
}

export interface PDFExportData {
  success: boolean;
  trip_id: string;
  export_timestamp: string;
  page_data: PDFPageData[];
  summary_page: ELDLogSummary;
}

// API Status Types
export interface APIServiceStatus {
  status: "available" | "unavailable" | "error";
  response_time?: number;
  api_key_configured: boolean;
  status_code?: number;
  error?: string;
}

export interface APIStatusResponse {
  openrouteservice: APIServiceStatus;
}

// Route Optimization Types
export interface OptimizationResult {
  improved: boolean;
  route_plan: RoutePlan;
  optimization_type: "break_placement" | "fuel_timing" | "daily_reset";
  message: string;
}

// Updated main response types
export interface TripCalculationResponse {
  success: boolean;
  trip_id: string;
  feasibility: TripFeasibility;
  route_plan: RoutePlan;
  route_data: RouteData;
  optimization_applied: boolean;
  message: string;
  error?: string;
  details?: string;
  current_status_considered: boolean;
}

export interface ELDLogResponse {
  success: boolean;
  trip_id: string;
  total_days: number;
  log_date_range: {
    start: string;
    end: string;
  };
  daily_logs: DailyELDLog[];
  summary: ELDLogSummary;
  validation_results?: ValidationResult;
  generated_at: string;
  error?: string;
}

export interface RouteOptimizationResponse {
  success: boolean;
  optimized: boolean;
  route_plan: RoutePlan;
  feasibility: TripFeasibility;
  optimizations_applied: string[];
  message: string;
  error?: string;
}

// Geocoding response types
export interface GeocodingResponse {
  success: boolean;
  latitude?: number;
  longitude?: number;
  formatted_address?: string;
  confidence?: number;
  country?: string;
  region?: string;
  locality?: string;
  postal_code?: string;
  source?: string;
  error?: string;
}

export interface ReverseGeocodingResponse {
  success: boolean;
  formatted_address?: string;
  country?: string;
  region?: string;
  locality?: string;
  postal_code?: string;
  confidence?: number;
  source?: string;
  error?: string;
}

// Utility response types
export interface TestRouteResponse {
  success: boolean;
  route_data: RouteData;
  timestamp: string;
}

export interface APIStatusCheckResponse {
  success: boolean;
  api_status: APIStatusResponse;
  timestamp: string;
}