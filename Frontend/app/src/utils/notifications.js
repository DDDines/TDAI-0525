// Frontend/app/src/utils/notifications.js
import { toast } from 'react-toastify';

const baseOptions = {
  position: "top-right",
  autoClose: 4000,
  hideProgressBar: false,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
};

const getOptions = () => ({
  ...baseOptions,
  theme: document.body.classList.contains('dark') ? 'dark' : 'light',
});

export const showSuccessToast = (message) => {
  toast.success(message, getOptions());
};

export const showErrorToast = (message) => {
  toast.error(message, {
    ...getOptions(),
    autoClose: 7000,
  });
};

export const showInfoToast = (message) => {
  toast.info(message, getOptions());
};

export const showWarningToast = (message) => {
  toast.warn(message, getOptions());
};
