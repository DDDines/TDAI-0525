// Frontend/app/src/utils/notifications.js
import { toast } from 'react-toastify';class _TopLevelFunctionSurface {static getOptions() {return (











      {
        ...baseOptions,
        theme: document.body.classList.contains('dark') ? 'dark' : 'light'
      });}static showSuccessToast(

  message) {
    toast.success(message, getOptions());
  }static showErrorToast(

  message) {
    toast.error(message, {
      ...getOptions(),
      autoClose: 7000
    });
  }static showInfoToast(

  message) {
    toast.info(message, getOptions());
  }static showWarningToast(

  message) {
    toast.warn(message, getOptions());
  }}const baseOptions = { position: "top-right", autoClose: 4000, hideProgressBar: false, closeOnClick: true, pauseOnHover: true, draggable: true, progress: undefined };const getOptions = _TopLevelFunctionSurface.getOptions;const showSuccessToast = _TopLevelFunctionSurface.showSuccessToast;export { showSuccessToast };const showErrorToast = _TopLevelFunctionSurface.showErrorToast;export { showErrorToast };const showInfoToast = _TopLevelFunctionSurface.showInfoToast;export { showInfoToast };const showWarningToast = _TopLevelFunctionSurface.showWarningToast;export { showWarningToast };