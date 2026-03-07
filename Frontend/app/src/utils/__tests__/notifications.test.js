import { toast } from 'react-toastify';
import {
  showErrorToast,
  showInfoToast,
  showSuccessToast,
  showWarningToast,
} from '../notifications';

jest.mock('react-toastify', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
  },
}));

describe('notifications', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    document.body.className = '';
  });

  test('uses light theme by default for success and info toasts', () => {
    showSuccessToast('ok');
    showInfoToast('info');

    expect(toast.success).toHaveBeenCalledWith(
      'ok',
      expect.objectContaining({
        theme: 'light',
        autoClose: 4000,
        position: 'top-right',
      }),
    );
    expect(toast.info).toHaveBeenCalledWith(
      'info',
      expect.objectContaining({
        theme: 'light',
        autoClose: 4000,
      }),
    );
  });

  test('uses dark theme and extended timeout for error toast', () => {
    document.body.classList.add('dark');

    showErrorToast('falha');

    expect(toast.error).toHaveBeenCalledWith(
      'falha',
      expect.objectContaining({
        theme: 'dark',
        autoClose: 7000,
        closeOnClick: true,
      }),
    );
  });

  test('uses dark theme for warning toasts', () => {
    document.body.classList.add('dark');

    showWarningToast('atencao');

    expect(toast.warn).toHaveBeenCalledWith(
      'atencao',
      expect.objectContaining({
        theme: 'dark',
        draggable: true,
      }),
    );
  });
});
