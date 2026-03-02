/**
 * Module notifications.
 *
 * Defines responsibilities and integration points for utils.
 */

// Frontend/app/src/utils/notifications.js
import { toast } from 'react-toastify';

function getOptions() {return (


      {
        ...baseOptions,
        theme: document.body.classList.contains('dark') ? 'dark' : 'light'
      });}

function showSuccessToast(

  message) {
    toast.success(message, getOptions());
  }

function showErrorToast(

  message) {
    toast.error(message, {
      ...getOptions(),
      autoClose: 7000
    });
  }

function showInfoToast(

  message) {
    toast.info(message, getOptions());
  }

function showWarningToast(

  message) {
    toast.warn(message, getOptions());
  }
const baseOptions = { position: "top-right", autoClose: 4000, hideProgressBar: false, closeOnClick: true, pauseOnHover: true, draggable: true, progress: undefined };export { showSuccessToast };export { showErrorToast };export { showInfoToast };export { showWarningToast };