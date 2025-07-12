/* eslint-disable @typescript-eslint/no-explicit-any */
import type { LatLngExpression } from "leaflet";

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

export interface ApiError {
  response?: {
    status: number;
    data?: {
      detail?: string;
      non_field_errors?: string[];
      error?: string;
      message?: string;
    };
  };
  code?: string;
  message?: string;
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
  refresh: string;
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
  status: "draft" | "Planned" | "in_progress" | "completed" | "cancelled";
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
  completed_at?: string;

  starting_cycle_hours?: number;
  starting_driving_hours?: number;
  starting_on_duty_hours?: number;
  starting_duty_status?: string;

  hos_updated: boolean;

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

export interface CurrentDriverStatus {
  total_cycle_hours: number;
  today_driving_hours: number;
  today_on_duty_hours: number;
  current_duty_status:
    | "off_duty"
    | "sleeper_berth"
    | "driving"
    | "on_duty_not_driving";
  current_status_start: string;
  last_30min_break_end?: string;
  today_date: string;
  // Calculated fields
  remaining_cycle_hours: number;
  remaining_driving_hours_today: number;
  remaining_on_duty_hours_today: number;
  needs_immediate_break: boolean;
  compliance_warnings: ComplianceWarning[];
}

export interface CurrentDriverStatusResponse {
  success: boolean;
  current_status: CurrentDriverStatus;
  last_updated: string;
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

  trip_start_cycle_hours: number;
  trip_start_driving_hours: number;
  trip_start_on_duty_hours: number;
  trip_start_duty_status:
    | "off_duty"
    | "sleeper_berth"
    | "driving"
    | "on_duty_not_driving";
  trip_start_status_time: string;
  trip_start_last_break?: string;
}

export interface TripCompletionResponse {
  success: boolean;
  message: string;
  hours_summary: {
    driving_hours: number;
    on_duty_hours: number;
    started_with_cycle_hours: number;
    started_with_driving_hours: number;
    started_with_on_duty_hours: number;
  };
  updated_driver_status: CurrentDriverStatus;
}

export interface DriverStatusFormData {
  total_cycle_hours: number;
  today_driving_hours: number;
  today_on_duty_hours: number;
  current_duty_status:
    | "off_duty"
    | "sleeper_berth"
    | "driving"
    | "on_duty_not_driving";
  current_status_start: string;
  last_30min_break_end?: string;
}

export interface DriverStatusUpdateRequest {
  current_duty_status:
    | "off_duty"
    | "sleeper_berth"
    | "driving"
    | "on_duty_not_driving";
  current_status_start?: string;
}

export interface DriverStatusUpdateResponse {
  success: boolean;
  message: string;
  current_status: CurrentDriverStatus;
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
  type: "LineString" | "combined_polylines";
  coordinates?: number[][];
  loaded_polyline?: string;
  deadhead_polyline?: string;
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
    | "fuel_and_break"
    | "required_break"
    | "fuel_stop"
    | "rest_break"
    | "sleeper_berth";
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
  driver_status_impact?: CurrentDriverStatus;
  eld_logs?: ELDLogResponse;
  error?: string;
}

export interface MyTripsResponse {
  success: boolean;
  trips: TripListItem[];
  count: number;
  driver_status?: CurrentDriverStatus;
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

export interface DriverCycleFormData {
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

export interface TripSettings {
  departure_datetime: string;
  max_fuel_distance_miles: number;
  pickup_duration_minutes: number;
  delivery_duration_minutes: number;
}

export interface ExpectedBreak {
  type: "30_minute" | "10_hour" | "34_hour";
  reason: string;
  estimatedTime: string;
  isRequired: boolean;
}

export interface GeolocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
}

export interface GeolocationResult {
  coordinates: LatLngExpression;
  accuracy: number;
  timestamp: number;
}

export interface RouteCoordinate {
  latitude: number;
  longitude: number;
  elevation?: number;
}

export interface ELDLogEntry {
  id: number;
  daily_log: string;
  hos_period?: number;
  start_time: string;
  end_time: string;
  duty_status: 'off_duty' | 'sleeper_berth' | 'driving' | 'on_duty_not_driving';
  duty_status_label: string;
  duty_status_symbol: number;
  duty_status_color: string;
  duration_minutes: number;
  duration_hours: number;
  start_location: string;
  end_location: string;
  location_type: 'trip_start' | 'pickup' | 'delivery' | 'fuel_stop' | 'rest_area' | 'intermediate_stop' | 'unknown';
  odometer_start: number;
  odometer_end: number;
  vehicle_miles: number;
  remarks: string;
  auto_generated_remarks: string;
  manual_remarks: string;
  grid_row: number;
  grid_column_start: number;
  grid_column_end: number;
  is_compliant: boolean;
  compliance_notes: string;
  was_manually_edited: boolean;
  original_auto_data: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ELDLocationRemark {
  id: number;
  daily_log: string;
  log_entry: number;
  time: string;
  location: string;
  location_type: 'trip_start' | 'pickup' | 'delivery' | 'fuel_stop' | 'rest_area' | 'state_line' | 'weigh_station' | 'intermediate_stop' | 'duty_status_change';
  location_type_display: string;
  odometer_reading: number;
  duty_status: 'off_duty' | 'sleeper_berth' | 'driving' | 'on_duty_not_driving';
  duty_status_display: string;
  remarks: string;
  auto_generated: boolean;
  is_duty_status_change: boolean;
  created_at: string;
}

export interface ELDComplianceViolation {
  id: number;
  daily_log: string;
  log_entry?: number; 
  violation_type: 'daily_driving_limit' | 'daily_on_duty_limit' | 'insufficient_off_duty' | 'missing_30min_break' | 'weekly_driving_limit' | 'daily_time_accounting' | 'missing_location_change' | 'invalid_duty_status';
  violation_type_display: string;
  severity: 'critical' | 'major' | 'minor' | 'warning';
  severity_display: string;
  description: string;
  actual_value?: number;
  limit_value?: number;
  violation_amount?: number;
  is_resolved: boolean;
  resolution_notes: string;
  resolved_at?: string;
  resolved_by?: string;
  resolved_by_name?: string;
  detected_at: string;
}

export interface ELDDailyLog {
  log_id: string;
  trip: string;
  log_date: string;
  driver: string;
  driver_name_display: string;
  
  driver_name: string;
  driver_license_number: string;
  driver_license_state: string;
  employee_id: string;
  
  carrier_name: string;
  carrier_address: string;
  dot_number: string;
  mc_number: string;
  
  vehicle_id: string;
  license_plate: string;
  vin: string;
  vehicle_make_model: string;
  
  total_off_duty_hours: number;
  total_sleeper_berth_hours: number;
  total_driving_hours: number;
  total_on_duty_not_driving_hours: number;
  total_on_duty_hours: number;
  total_distance_miles: number;
  

  bill_of_lading: string;
  manifest_number: string;
  pickup_number: string;
  delivery_receipt: string;
  commodity_description: string;
  cargo_weight: string;
  is_hazmat: boolean;
  
  is_compliant: boolean;
  compliance_score: number;
  compliance_grade: string;
  violation_count: number;
  warning_count: number;
  
  is_certified: boolean;
  certified_at?: string;
  certification_signature: string;
  certification_statement: string;
  
  auto_generated: boolean;
  manual_edits_count: number;
  last_edited_by?: string;
  last_edited_at?: string;
  generated_at: string;
  updated_at: string;
  
  log_entries: ELDLogEntry[];
  location_remarks: ELDLocationRemark[];
  compliance_violations: ELDComplianceViolation[];
}

export interface ELDDailyLogSummary {
  log_id: string;
  log_date: string;
  driver_name_display: string;
  trip_id: string;
  total_driving_hours: number;
  total_on_duty_hours: number;
  total_distance_miles: number;
  is_compliant: boolean;
  compliance_score: number;
  compliance_grade: string;
  violation_count: number;
  is_certified: boolean;
  certified_at?: string;
  auto_generated: boolean;
}

export interface ELDExportRecord {
  export_id: string;
  daily_logs: string[];
  trip?: string;
  export_format: 'pdf' | 'csv' | 'json' | 'xml' | 'dot_format';
  export_purpose: 'dot_inspection' | 'driver_record' | 'fleet_audit' | 'compliance_review' | 'backup' | 'other';
  date_range_start: string;
  date_range_end: string;
  file_name: string;
  file_size_bytes: number;
  file_checksum: string;
  exported_by: string;
  exported_at: string;
  notes: string;
  is_for_dot_inspection: boolean;
  inspection_reference: string;
}

// Request/Response types for API calls
export interface ELDLogGenerationRequest {
  save_to_database?: boolean;
  include_compliance_validation?: boolean;
  auto_certify?: boolean;
  export_format?: 'json' | 'pdf_data';
  generate_missing_only?: boolean;
}

export interface ELDLogGenerationResponse {
  success: boolean;
  trip_id: string;
  logs_generated: number;
  logs_updated: number;
  total_days: number;
  log_date_range: {
    start: string;
    end: string;
  };
  daily_logs: ELDDailyLog[];
  compliance_summary: {
    is_compliant: boolean;
    total_violations: number;
    total_warnings: number;
    daily_validations: Array<{
      log_date: string;
      is_compliant: boolean;
      violations: ELDComplianceViolation[];
      warnings: any[];
      totals_checked: Record<string, number>;
      compliance_score: number;
    }>;
  };
  warnings?: string[];
  error?: string;
  generated_at: string;
}

export interface ELDLogCertificationRequest {
  certification_signature?: string;
  certification_notes?: string;
}

export interface ELDLogCertificationResponse {
  success: boolean;
  message: string;
  certified_at: string;
  log_id: string;
}

export interface ELDLogEditRequest {
  log_entry_id: number;
  field_name: 'start_time' | 'end_time' | 'duty_status' | 'start_location' | 'end_location' | 'manual_remarks' | 'odometer_start' | 'odometer_end';
  new_value: string;
  edit_reason: string;
}

export interface ELDLogEditResponse {
  success: boolean;
  message: string;
  log_entry_id: number;
  field_updated: string;
  new_value: string;
}

export interface ELDExportRequest {
  export_format: 'pdf' | 'csv' | 'json' | 'xml' | 'dot_format';
  export_purpose: 'dot_inspection' | 'driver_record' | 'fleet_audit' | 'compliance_review' | 'backup' | 'other';
  date_range_start?: string;
  date_range_end?: string;
  include_violations?: boolean;
  include_location_remarks?: boolean;
  inspection_reference?: string;
  notes?: string;
}

export interface ELDExportResponse {
  success: boolean;
  export_id?: string;
  file_name?: string;
  file_size_bytes?: number;
  download_url?: string;
  export_format?: string;
  logs_exported?: number;
  date_range?: {
    start: string;
    end: string;
  };
  error?: string;
  expires_at?: string;
}

export interface ELDComplianceSummary {
  date_range: {
    start: string;
    end: string;
  };
  statistics: {
    total_logs: number;
    compliant_logs: number;
    compliance_rate: number;
    certified_logs: number;
    certification_rate: number;
    total_violations: number;
    average_compliance_score: number;
  };
  violation_breakdown: Record<string, number>;
  recent_logs: ELDDailyLogSummary[];
}

// Trip ELD Logs response type
export interface TripELDLogsResponse {
  success: boolean;
  trip_id: string;
  total_days: number;
  logs: ELDDailyLog[];
  summary: {
    total_driving_hours: number;
    total_on_duty_hours: number;
    total_distance_miles: number;
    compliance_rate: number;
    certification_rate: number;
    compliant_logs: number;
    certified_logs: number;
  };
}

// Paginated response type for ELD logs list
export interface ELDLogsPaginatedResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ELDDailyLogSummary[];
}

// Grid data type for ELD visualization
export interface ELDGridData {
  time: string;
  minute_of_day: number;
  duty_status: string;
  duty_status_label: string;
  duty_status_symbol: number;
  duty_status_color: string;
  grid_row: number;
  grid_column: number;
  entry_id?: number;
  location?: string;
}