/**
 * Pure helpers kept out of the component to keep the wizard testable.
 */

import { normalizeDisplayText } from '../../utils/textNormalization';

export function formatCellValue(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function getPreviewImageSrc(img) {
  if (typeof img === 'string') {
    if (!img.trim()) return null;
    return img.startsWith('data:image') ? img : `data:image/png;base64,${img}`;
  }
  if (img && typeof img === 'object' && img.image) return img.image;
  return null;
}

export function formatElapsed(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0s';
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export function normalizePayloadStrings(payload) {
  if (Array.isArray(payload)) return payload.map((item) => normalizePayloadStrings(item));
  if (payload && typeof payload === 'object') {
    return Object.fromEntries(
      Object.entries(payload).map(([k, v]) => [k, normalizePayloadStrings(v)])
    );
  }
  if (typeof payload === 'string') return normalizeDisplayText(payload);
  return payload;
}
