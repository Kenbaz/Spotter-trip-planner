import { clsx } from "clsx";

interface LoadingSpinnerProps {
  size?: "small" | "medium" | "large";
  className?: string;
  text?: string;
}

export function LoadingSpinner({
  size = "medium",
  className,
  text,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    small: "h-4 w-4",
    medium: "h-8 w-8",
    large: "h-12 w-12",
  };

  return (
    <div
      className={clsx("flex flex-col items-center justify-center", className)}
    >
      <div
        className={clsx(
          "animate-spin rounded-full border-t-[3px] border-blue-600",
          sizeClasses[size]
        )}
      />
      {text && <p className="mt-2 text-sm text-gray-600">{text}</p>}
    </div>
  );
}
