import { toast } from "react-hot-toast";

export const showToast = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  loading: (message: string) => toast.loading(message),
  dismiss: (toastId?: string) => toast.dismiss(toastId),
  promise: <T>(
    promise: Promise<T>,
    messages: {
      success: string | ((data: T) => string);
      error: string | ((error: Error) => string);
      loading: string;
    }
  ) => {
    return toast.promise(promise, messages);
  },
};
