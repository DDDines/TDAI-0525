/**
 * Module text normalization.
 *
 * Shared helpers to repair mojibake and normalize noisy UI strings.
 */

const DEFAULT_REPLACEMENTS = [
  ['n??o', 'n\u00e3o'],
  ['N??o', 'N\u00e3o'],
  ['n?o', 'n\u00e3o'],
  ['p??de', 'p\u00f4de'],
  ['P??gina', 'P\u00e1gina'],
  ['P?gina', 'P\u00e1gina'],
  ['p??gina', 'p\u00e1gina'],
  ['p?gina', 'p\u00e1gina'],
  ['descri??o', 'descri\u00e7\u00e3o'],
  ['Descri??o', 'Descri\u00e7\u00e3o'],
  ['conte??do', 'conte\u00fado'],
  ['conte?do', 'conte\u00fado'],
  ['Conclu?do', 'Conclu\u00eddo'],
  ['conclu?do', 'conclu\u00eddo'],
  ['conclu?da', 'conclu\u00edda'],
  ['revis?o', 'revis\u00e3o'],
  ['extra??o', 'extra\u00e7\u00e3o'],
  ['extra??do', 'extra\u00eddo'],
  ['extra?do', 'extra\u00eddo'],
  ['extra??vel', 'extra\u00edvel'],
  ['extra?vel', 'extra\u00edvel'],
  ['cat??logo', 'cat\u00e1logo'],
  ['cat?logo', 'cat\u00e1logo'],
  ['situa??o', 'situa\u00e7\u00e3o'],
  ['configura??o', 'configura\u00e7\u00e3o'],
  ['Configura??o', 'Configura\u00e7\u00e3o'],
  ['poss??vel', 'poss\u00edvel'],
  ['poss?vel', 'poss\u00edvel'],
  ['dispon?veis', 'dispon\u00edveis'],
  ['cr??tico', 'cr\u00edtico'],
  ['cr?tico', 'cr\u00edtico'],
  ['cr??tica', 'cr\u00edtica'],
  ['cr?tica', 'cr\u00edtica'],
  ['m?dia', 'm\u00e9dia'],
  ['h?', 'h\u00e1'],
  ['Importa??o', 'Importa\u00e7\u00e3o'],
  ['importa??o', 'importa\u00e7\u00e3o'],
  ['Relat?rio', 'Relat\u00f3rio'],
  ['relat?rio', 'relat\u00f3rio'],
  ['n?o cr?ticos', 'n\u00e3o cr\u00edticos'],
  ['n?o dispon?veis', 'n\u00e3o dispon\u00edveis'],
];

function markerCount(candidate) {
  return (candidate.match(/[\u00c3\u00c2\u00e2\u0192\ufffd]/g) || []).length;
}

function hasMarkers(candidate) {
  return markerCount(candidate) > 0 || /[?]{2,}/.test(candidate);
}

function decodeMaybe(candidate) {
  try {
    return new TextDecoder('utf-8', { fatal: false }).decode(
      Uint8Array.from(Array.from(candidate).map((ch) => ch.charCodeAt(0) & 0xff))
    );
  } catch {
    return candidate;
  }
}

export function normalizeDisplayText(value, options = {}) {
  if (value === null || value === undefined) return '';

  const { maxDecodePasses = 5, replacements = DEFAULT_REPLACEMENTS } = options;
  let text = String(value);

  for (let i = 0; i < maxDecodePasses && hasMarkers(text); i += 1) {
    const decoded = decodeMaybe(text);
    if (!decoded || decoded === text) break;
    if (markerCount(decoded) > markerCount(text)) break;
    text = decoded;
  }

  text = text.replace(/\u00c2/g, '');

  replacements.forEach(([source, target]) => {
    text = text.replaceAll(source, target);
  });

  return text.replace(/\s+/g, ' ').trim();
}

export default normalizeDisplayText;
