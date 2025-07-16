import { Toaster, ToastBar, toast } from "react-hot-toast";
import React from "react";
import type { Toast } from "react-hot-toast";
import { X } from "lucide-react";


export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 3000,
        className: "toast",
        style: {
          background: "#fff",
          color: "#333",
          border: "1px solid #e2e8f0",
          borderRadius: "0.5rem",
          padding: "1rem",
          boxShadow:
            "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
          minWidth: "300px",
        },
        success: {
          iconTheme: {
            primary: "#059669",
            secondary: "#fff",
          },
        },
        error: {
          iconTheme: {
            primary: "#dc2626",
            secondary: "#fff",
          },
          duration: 4000,
        },
      }}
    >
      {(t: Toast) => (
        <ToastBar toast={t}>
          {({
            icon,
            message,
          }: {
            icon: React.ReactNode;
            message: React.ReactNode;
          }) => (
            <div className="flex items-center w-full gap-2 p-2">
              {icon}
              {message}
              {t.type !== "loading" && (
                <button
                  onClick={() => toast.dismiss(t.id)}
                  className="ml-auto p-1 rounded-full hover:bg-gray-100 transition-colors"
                  type="button"
                >
                  <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                </button>
              )}
            </div>
          )}
        </ToastBar>
      )}
    </Toaster>
  );
}
