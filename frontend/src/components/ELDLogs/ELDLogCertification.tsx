import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../UI/Card";
import { Button } from "../UI/Button";
import {
  FileText,
  CheckCircle,
  AlertCircle,
  User,
  Calendar,
  Clock,
} from "lucide-react";

interface ELDLogCertificationProps {
  logId: string;
  logDate: string;
  driverName: string;
  isAlreadyCertified: boolean;
  certifiedAt?: string;
  certificationStatement: string;
  onCertify: (signature?: string, notes?: string) => Promise<void>;
  isCertifying?: boolean;
}

export function ELDLogCertification({
  logId,
  logDate,
  driverName,
  isAlreadyCertified,
  certifiedAt,
  certificationStatement,
  onCertify,
  isCertifying = false,
}: ELDLogCertificationProps) {
  const [notes, setNotes] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);

  const handleCertify = async () => {
    if (!acknowledged) return;

    try {
      await onCertify(undefined, notes);
    } catch (error) {
      console.error("Failed to certify log:", error);
    }
  };

  if (isAlreadyCertified) {
    return (
      <Card className="border-2 border-green-300 bg-green-50">
        <CardHeader>
          <CardTitle className="flex items-center text-green-800">
            <CheckCircle className="w-5 h-5 mr-2" />
            Log Certified
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-2">
                <User className="w-4 h-4 text-gray-500" />
                <span>Driver: {driverName}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Calendar className="w-4 h-4 text-gray-500" />
                <span>Date: {new Date(logDate).toLocaleDateString()}</span>
              </div>
              {certifiedAt && (
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <span>
                    Certified: {new Date(certifiedAt).toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            <div className="p-3 bg-white rounded border">
              <p className="text-sm text-gray-700">
                This log has been digitally certified by the driver and cannot
                be modified.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-2 border-blue-300 bg-blue-50">
      <CardHeader>
        <CardTitle className="flex items-center text-blue-800">
          <FileText className="w-5 h-5 mr-2" />
          Driver Certification Required
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Log Information */}
          <div className="flex items-center space-x-4 text-sm">
            <div className="flex items-center space-x-2">
              <User className="w-4 h-4 text-gray-500" />
              <span>Driver: {driverName}</span>
            </div>
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <span>Date: {new Date(logDate).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-gray-500" />
              <span>Log ID: {logId.slice(-8)}</span>
            </div>
          </div>

          {/* Certification Statement */}
          <div className="p-4 bg-white rounded border">
            <h4 className="font-semibold mb-2">Certification Statement:</h4>
            <p className="text-sm text-gray-700 italic">
              "{certificationStatement}"
            </p>
          </div>

          {/* Optional Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes (Optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Add any additional notes about this log..."
            />
          </div>

          {/* Acknowledgment */}
          <div className="flex items-start space-x-3">
            <input
              type="checkbox"
              id="acknowledge"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="acknowledge" className="text-sm text-gray-700">
              I acknowledge that I have reviewed this log and certify that my
              data entries and my record of duty status for this 24-hour period
              are true and correct.
            </label>
          </div>

          {/* Warning */}
          <div className="flex items-start space-x-3 p-3 bg-yellow-50 rounded border border-yellow-200">
            <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <strong>Important:</strong> Once certified, this log cannot be
              modified. Please ensure all information is accurate before
              proceeding.
            </div>
          </div>

          {/* Certification Button */}
          <div className="flex justify-end">
            <Button
              onClick={handleCertify}
              disabled={!acknowledged || isCertifying}
              isLoading={isCertifying}
              className="bg-blue-600 hover:bg-blue-700"
              leftIcon={<CheckCircle className="w-4 h-4" />}
            >
              {isCertifying ? "Certifying..." : "Certify Log"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
