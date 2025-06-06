// Frontend/app/src/utils/notifications.js
import { toast } from 'react-toastify';

const defaultToastOptions = {
  position: "top-right",
  autoClose: 4000,
  hideProgressBar: false,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
  theme: "light",
};

export const showSuccessToast = (message) => {
  toast.success(message, defaultToastOptions);
};

export const showErrorToast = (message) => {
  toast.error(message, {
    ...defaultToastOptions,
    autoClose: 7000, 
  });
};

export const showInfoToast = (message) => {
  toast.info(message, defaultToastOptions);
};

export const showWarningToast = (message) => {
  toast.warn(message, defaultToastOptions);
};
