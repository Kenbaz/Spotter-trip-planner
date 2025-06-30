import { Card, CardContent, CardHeader, CardTitle } from './Card';
import type { DriverCycleFormData, ExpectedBreak } from '../../types';
import { AlertTriangle } from 'lucide-react';


export default function BreakCompliancePreview({ driverCycle, estimatedDrivingTime }: {
    driverCycle: DriverCycleFormData;
    estimatedDrivingTime?: number;
}) {
    const expectedBreaks: ExpectedBreak[] = [];

    if (estimatedDrivingTime && estimatedDrivingTime > 0) {
      // Calculate when 30 min breaks are needed
      const currentDrivingHours = driverCycle.hours_driven_today;
      const totalDrivingTime = currentDrivingHours + estimatedDrivingTime;

      if (currentDrivingHours >= 8 || totalDrivingTime > 0) {
        expectedBreaks.push({
          type: "30_minute",
          reason: "30 minute break required after 8 hours of driving",
          estimatedTime: "After 8 hours of driving",
          isRequired: true,
        });
      }

      // Check if 10-hour break is needed
      if (totalDrivingTime > 11) {
        expectedBreaks.push({
          type: "10_hour",
          reason: "Required 10-hour break after 11 hours of driving",
          estimatedTime: "After reaching daily driving limit",
          isRequired: true,
        });
      }

      // Check if approaching 14-hour limit
      const currentOnDutyHours = driverCycle.hours_on_duty_today;
      const estimatedOnDutyTime = currentOnDutyHours + estimatedDrivingTime + 2; // Adding 2 hours for loading/unloading

      if (estimatedOnDutyTime > 14) {
        expectedBreaks.push({
          type: "10_hour",
          reason: "Required 10-hour break after 14-hour duty window",
          estimatedTime: "Before 14-hour limit",
          isRequired: true,
        });
      }

      // Check cycle limit
      const cycleHours =
        driverCycle.current_cycle_hours_used + estimatedOnDutyTime;
      if (cycleHours > 70) {
        expectedBreaks.push({
          type: "34_hour",
          reason: "Required 34-hour restart after 70-hour cycle",
          estimatedTime: "Before cycle limit",
          isRequired: true,
        });
      }
    }

    if (expectedBreaks.length === 0) { 
        return null;
    }


    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardHeader>
          <CardTitle className="text-yellow-800 flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5" />
            <span>Expected HOS Breaks</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <p className="text-sm text-yellow-700">
              Based on your current HOS status and trip duration, the following
              breaks will be automatically added to your route:
            </p>

            {expectedBreaks.map((breakItem, index) => (
              <div
                key={index}
                className="flex items-start space-x-3 p-3 bg-white rounded-lg border border-yellow-200"
              >
                <div
                  className={`w-3 h-3 rounded-full mt-1 ${
                    breakItem.isRequired ? "bg-red-500" : "bg-yellow-500"
                  }`}
                />
                <div className="flex-1">
                  <p className="font-medium text-gray-900">
                    {breakItem.type === "30_minute"
                      ? "30-Minute Break"
                      : breakItem.type === "10_hour"
                      ? "10-Hour Break"
                      : "34-Hour Restart"}
                  </p>
                  <p className="text-sm text-gray-600">{breakItem.reason}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {breakItem.estimatedTime}
                  </p>
                </div>
              </div>
            ))}

            <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> These breaks will be automatically
                inserted into your route during calculation to ensure HOS
                compliance.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
}