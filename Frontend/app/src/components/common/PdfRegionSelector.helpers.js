/**
 * Module pdf region selector helpers.
 *
 * Shared helpers for PDF page rendering used by the common selector component.
 */

async function renderPdfPage(pdfDocument, pageNumber, canvasElement) {
  if (!pdfDocument || !canvasElement) return;

  const page = await pdfDocument.getPage(pageNumber);
  const viewport = page.getViewport({ scale: 1.5 });
  const context = canvasElement.getContext('2d');
  canvasElement.width = viewport.width;
  canvasElement.height = viewport.height;
  await page.render({ canvasContext: context, viewport }).promise;
}

export { renderPdfPage };
