/**
 * Shared helpers for extracting displayable API error messages.
 */

function formatValidationDetail(detail) {
  if (!Array.isArray(detail)) {
    return '';
  }

  return detail
    .map((entry) => {
      const prefix = Array.isArray(entry?.loc) && entry.loc.length > 0
        ? `${entry.loc.join('.')}: `
        : '';
      return `${prefix}${entry?.msg || ''}`.trim();
    })
    .filter(Boolean)
    .join('; ');
}

export function extractErrorMessage(error, fallback) {
  if (!error) {
    return fallback;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (typeof error?.detail === 'string') {
    return error.detail;
  }

  const validationMessage = formatValidationDetail(error?.detail);
  if (validationMessage) {
    return validationMessage;
  }

  if (error?.detail && typeof error.detail === 'object') {
    return JSON.stringify(error.detail);
  }

  if (typeof error?.message === 'string') {
    return error.message;
  }

  return fallback;
}

export default extractErrorMessage;
