import { Card, CardContent } from "../UI/Card";
import {
  CheckCircle,
} from "lucide-react";
// import { ELDComplianceIndicator } from "./ELDComplianceIndicator";
import type { ELDDailyLog } from "../../types";

interface ELDLogViewerProps {
  dailyLog: ELDDailyLog;
  className?: string;
}

const safeNumberValue = (value: unknown, fallback: number = 0): number => {
  if (typeof value === "number" && !isNaN(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? fallback : parsed;
  }
  return fallback;
};

export function ELDLogViewer({
  dailyLog,
  className = "",
}: ELDLogViewerProps) {

  return (
    <div className={`space-y-6 ${className}`}>
      {/* DOT-Compliant Header */}
      <Card className="border-2 border-gray-900">
        <CardContent className="p-2 border-b border-gray-900">
          <div className="text-center">
            <h1 className="text-xl font-bold text-gray-900">
              DRIVER'S DAILY LOG
            </h1>
            <h2 className="text-lg font-semibold text-gray-800">
              (ONE CALENDAR DAY - 24 HOURS)
            </h2>
          </div>

          {/* Date and Status */}
          <div className="flex justify-between items-center mt-4">
            <div className="grid items-center space-x-2 w-full">
              <div className="text-gray-900 text-sm">
                US DEPARTMENT OF TRANSPORTATION
              </div>
              <div className="flex w-full items-center justify-between space-x-8">
                <div className="">
                  <div className="flex items-center space-x-8">
                    <span className="text-base text-center text-gray-900 font-semibold">
                      {new Date(dailyLog.log_date).toLocaleDateString("en-US", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })}
                      <hr className="border border-gray-900" />
                      <div className="h-[1.2rem]"></div>
                    </span>
                    <span className="text-sm text-gray-600 text-center">
                      {safeNumberValue(dailyLog.total_distance_miles).toFixed(
                        0
                      )}
                      <hr className="border border-gray-900" />
                      <strong className="text-xs">
                        (TOTAL MILES DRIVEN TODAY)
                      </strong>
                    </span>
                  </div>
                </div>
                <div>
                  <div>
                    <div className="font-medium text-center text-gray-900">
                      {dailyLog.vehicle_id}
                      <hr className="border border-gray-900" />
                    </div>
                    <strong className="text-gray-600 text-xs">
                      VEHICLE NUMBERS-(SHOW EACH UNIT)
                    </strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              
              {dailyLog.is_certified && (
                <div className="flex items-center space-x-2 text-green-600">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium">Certified</span>
                </div>
              )}
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 mt-6 mb-6">
            {/* Carrier Information */}
            <div className="space-y-3">
              <div className="font-medium text-center text-gray-900">
                {dailyLog.carrier_name}
                <hr className="border border-gray-900" />
              </div>
              <strong className="text-gray-600 relative left-[25%] text-xs">
                (NAME OF CARRIER OR CARRIERS)
              </strong>
            </div>

            {/* Driver Information */}
            <div className="space-y-3">
              <div className="font-medium text-center text-gray-900">
                {dailyLog.driver_name}
                <hr className="border border-gray-900" />
              </div>
              <strong className="text-gray-600 relative left-[25%] text-xs">
                (DRIVER'S SIGNATURE IN FULL)
              </strong>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 mt-6 mb-6">
            {/* Office Information */}
            <div className="space-y-3">
              <div className="font-medium text-center text-gray-900">
                {dailyLog.carrier_address}
                <hr className="border border-gray-900" />
              </div>
              <strong className="text-gray-600 relative left-[25%] text-xs">
                (MAIN OFFICE ADDRESS)
              </strong>
            </div>

            {/* Driver Information */}
            <div className="space-y-3">
              <div className="font-medium text-center text-gray-900">
                N/A
                <hr className="border border-gray-900" />
              </div>
              <strong className="text-gray-600 relative left-[25%] text-xs">
                (NAME OF CO_DRIVER)
              </strong>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ELD Grid - The main 24-hour duty status chart */}
      {/* <Card className="border-2 border-gray-900">
        <CardHeader>
          <CardTitle className="text-center text-lg font-bold">
            24-HOUR DUTY STATUS RECORD
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ELDGrid
            logEntries={dailyLog.log_entries}
            onEditEntry={canEdit ? handleStartEdit : undefined}
            className="border-2 border-gray-900"
          />
        </CardContent>
      </Card> */}
    </div>
  );
}