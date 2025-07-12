import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";

interface ELDComplianceIndicatorProps {
  isCompliant: boolean;
  complianceScore: number;
  violationCount: number;
  warningCount?: number;
  size?: "sm" | "md" | "lg";
  showDetails?: boolean;
}

// Helper function to safely convert to number with fallback
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

export function ELDComplianceIndicator({
  isCompliant,
  complianceScore,
  violationCount,
  warningCount = 0,
  size = "md",
  showDetails = true,
}: ELDComplianceIndicatorProps) {
  const getComplianceGrade = (score: number): string => {
    if (score >= 95) return "A+";
    if (score >= 90) return "A";
    if (score >= 85) return "B+";
    if (score >= 80) return "B";
    if (score >= 75) return "C+";
    if (score >= 70) return "C";
    if (score >= 65) return "D";
    return "F";
  };

  const getStatusColor = () => {
    if (isCompliant && violationCount === 0)
      return "text-green-600 bg-green-50 border-green-200";
    if (violationCount > 0) return "text-red-600 bg-red-50 border-red-200";
    return "text-yellow-600 bg-yellow-50 border-yellow-200";
  };

  const getStatusIcon = () => {
    const iconSize =
      size === "sm" ? "w-4 h-4" : size === "lg" ? "w-6 h-6" : "w-5 h-5";

    if (isCompliant && violationCount === 0) {
      return <CheckCircle className={`${iconSize} text-green-600`} />;
    }
    if (violationCount > 0) {
      return <XCircle className={`${iconSize} text-red-600`} />;
    }
    return <AlertTriangle className={`${iconSize} text-yellow-600`} />;
  };

  const safeComplianceScore = safeNumberValue(complianceScore);
  const grade = getComplianceGrade(safeComplianceScore);

  return (
    <div
      className={`inline-flex items-center space-x-2 px-3 py-2 rounded-lg border ${getStatusColor()}`}
    >
      {getStatusIcon()}

      <div className={`${size === "sm" ? "text-sm" : "text-base"}`}>
        <div className="font-semibold">
          {isCompliant ? "Compliant" : "Non-Compliant"}
        </div>

        {showDetails && (
          <div
            className={`${size === "sm" ? "text-xs" : "text-sm"} opacity-80`}
          >
            Grade: {grade} ({safeComplianceScore.toFixed(1)}%)
            {violationCount > 0 && ` • ${violationCount} violations`}
            {warningCount > 0 && ` • ${warningCount} warnings`}
          </div>
        )}
      </div>
    </div>
  );
}
