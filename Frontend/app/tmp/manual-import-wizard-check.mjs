import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const BASE_URL = 'http://127.0.0.1:5173';
const DOWNLOAD_PDF = 'C:/Users/Julio/Downloads/CATALOGO GERAL 38.pdf';
const PROJECT_PDF = 'C:/Users/Julio/Desktop/TDAI 2025/Project/CatalogAI.pdf';

const pickPdf = () => {
  if (fs.existsSync(DOWNLOAD_PDF)) return DOWNLOAD_PDF;
  if (fs.existsSync(PROJECT_PDF)) return PROJECT_PDF;
  throw new Error('Nenhum PDF de teste encontrado para o fluxo de importacao.');
};

const screenshot = async (page, name) => {
  const output = path.join('tmp', name);
  await page.screenshot({ path: output, fullPage: true });
  return output;
};

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1680, height: 1050 } });

try {
  const testPdf = pickPdf();
  console.log(`[INFO] PDF usado: ${testPdf}`);

  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email:').fill('admin@example.com');
  await page.getByLabel('Senha:').fill('adminpassword');
  await Promise.all([
    page.waitForURL('**/dashboard'),
    page.getByRole('button', { name: 'Entrar' }).click(),
  ]);

  await page.goto(`${BASE_URL}/fornecedores`, { waitUntil: 'networkidle' });
  await page.locator('table tbody tr').first().click();
  await page.getByText(/Editar fornecedor:/i).waitFor({ timeout: 10000 });

  await page.getByRole('button', { name: /Importar Cat/i }).first().click();
  await page.getByRole('button', { name: /^Importar Cat/i }).nth(1).click();
  await page.getByText('Passo 1: Enviar catálogo').waitFor({ timeout: 10000 });

  await screenshot(page, 'manual-import-step-1-upload.png');

  await page.locator('#wizard-file-input').setInputFiles(testPdf);
  await page.locator('#wizard-page-count').fill('1');
  await page.locator('#wizard-start-page').fill('12');
  await page.getByRole('button', { name: 'Gerar Preview' }).click();

  await page.getByText('Passo 2: Revisar e mapear dados').waitFor({ timeout: 180000 });
  await screenshot(page, 'manual-import-step-2-preview.png');

  await page.getByRole('button', { name: 'Definir mapeamento' }).click();
  await page.getByText('Mapear Colunas').waitFor({ timeout: 10000 });
  await screenshot(page, 'manual-import-step-3-mapping.png');

  await page.locator('.modal-header').filter({ hasText: 'Mapear Colunas' }).locator('.modal-close-button').click();

  const productTypeSelect = page.locator('#wizard-product-type');
  const optionsCount = await productTypeSelect.locator('option').count();
  if (optionsCount > 1) {
    await productTypeSelect.selectOption({ index: 1 });
  }

  await page.getByRole('button', { name: 'Iniciar Processamento' }).click();
  await page.getByText('Passo 3: Processando importação').waitFor({ timeout: 25000 });
  await screenshot(page, 'manual-import-step-4-processing.png');

  console.log('[OK] Fluxo de importacao validado e capturas geradas em Frontend/app/tmp.');
} finally {
  await browser.close();
}
