// import React, { useState } from "react";
import { Trash2, AlertTriangle, X } from "lucide-react";
import { Button } from "../UI/Button";

interface DeleteConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading?: boolean;
  tripTitle?: string;
}

export const DeleteConfirmationModal: React.FC<
  DeleteConfirmationModalProps
> = ({
  isOpen,
  onClose,
  onConfirm,
  isLoading = false,
  tripTitle = "this trip",
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-1">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Delete Trip</h3>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 md:p-5">
          <p className="text-gray-700 mb-4">
            Are you sure you want to delete <strong>{tripTitle}</strong>?
          </p>
          <div className="bg-red-50 border border-red-200 rounded-lg p-2 md:p-4 mb-6">
            <div className="flex items-center space-x-2 text-red-800">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm font-medium">Warning</span>
            </div>
            <p className="text-sm text-red-700 mt-1">
              This action cannot be undone. All trip data, including routes,
              stops, and logs will be permanently deleted.
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex space-x-3 px-6 pb-6">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={onConfirm}
            isLoading={isLoading}
            disabled={isLoading}
            leftIcon={<Trash2 className="w-4 h-4" />}
            className="flex-1"
          >
            {isLoading ? "Deleting..." : "Delete Trip"}
          </Button>
        </div>
      </div>
    </div>
  );
};
