import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE_URL = process.env.UI_BASE_URL || 'http://127.0.0.1:5173';
const EMAIL = process.env.UI_ADMIN_EMAIL || 'admin@example.com';
const PASSWORD = process.env.UI_ADMIN_PASSWORD || 'adminpassword';
const FILE_PATH = process.env.UI_IMPORT_FILE || path.resolve('tmp/smoke-import.csv');

if (!fs.existsSync(FILE_PATH)) {
  console.error(`[FAIL] Arquivo de teste não encontrado: ${FILE_PATH}`);
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const report = [];

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

try {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email:').fill(EMAIL);
  await page.getByLabel('Senha:').fill(PASSWORD);
  await Promise.all([
    page.waitForURL('**/dashboard', { timeout: 30000 }),
    page.getByRole('button', { name: 'Entrar' }).click(),
  ]);
  report.push('[OK] Login');

  await page.goto(`${BASE_URL}/fornecedores`, { waitUntil: 'networkidle' });
  report.push('[OK] Fornecedores aberto');

  const firstFornecedorCell = page.locator('table tbody tr td').nth(1);
  await firstFornecedorCell.click({ timeout: 10000 });
  await page.waitForSelector('text=Editar fornecedor', { timeout: 15000 });
  report.push('[OK] Modal editar fornecedor aberto');

  await page.getByRole('button', { name: /Importar Catálogo/i }).first().click();
  const importOpenButton = page.locator('#edit-forn-modal .form-section button').filter({ hasText: /Importar Catálogo/i }).first();
  await importOpenButton.click({ timeout: 10000 });

  await page.waitForSelector('text=Passo 1: Enviar catálogo', { timeout: 15000 });
  await page.screenshot({ path: 'tmp/manual-import-step1.png', fullPage: true });
  report.push('[OK] Wizard passo 1 aberto');

  await page.locator('#wizard-file-input').setInputFiles(FILE_PATH);
  await page.getByRole('button', { name: /Gerar Preview/i }).click();
  await page.waitForSelector('text=Passo 2: Revisar e mapear dados', { timeout: 45000 });
  await page.screenshot({ path: 'tmp/manual-import-step2-preview.png', fullPage: true });
  report.push('[OK] Preview gerado (passo 2)');

  await page.getByRole('button', { name: /Definir mapeamento/i }).click({ timeout: 10000 });
  await page.waitForSelector('text=Mapear Colunas', { timeout: 10000 });

  const mappingByHeader = {
    sku_original: 'SKU',
    nome_base: 'Nome Base',
    descricao_original: 'Descrição',
    preco_original: 'Preço',
  };

  const mapRows = page.locator('.mapping-table tbody tr');
  const rowCount = await mapRows.count();
  for (let i = 0; i < rowCount; i += 1) {
    const row = mapRows.nth(i);
    const header = (await row.locator('td').first().innerText()).trim();
    const target = mappingByHeader[header];
    if (target) {
      await row.locator('select').selectOption({ label: target });
    }
  }

  const productTypeSelectInModal = page.locator('#column-mapping-product-type-select');
  if (await productTypeSelectInModal.count()) {
    const options = await productTypeSelectInModal.locator('option').count();
    if (options > 1) {
      await productTypeSelectInModal.selectOption({ index: 1 });
    }
  }

  await page.screenshot({ path: 'tmp/manual-import-step2-mapping.png', fullPage: true });
  await page.getByRole('button', { name: /Confirmar mapeamento/i }).click();
  report.push('[OK] Mapeamento confirmado');

  const scopeProductTypeSelect = page.locator('.wizard-scope-card select').first();
  if (await scopeProductTypeSelect.count()) {
    const options = await scopeProductTypeSelect.locator('option').count();
    if (options > 1) {
      await scopeProductTypeSelect.selectOption({ index: 1 });
    }
  }

  const startButton = page.getByRole('button', { name: /Iniciar Processamento/i }).first();
  await startButton.click({ timeout: 10000 });

  await page.waitForSelector('text=Passo 3: Processando importação', { timeout: 15000 });
  await page.screenshot({ path: 'tmp/manual-import-step3-processing.png', fullPage: true });

  const endAt = Date.now() + 45000;
  let terminal = null;
  while (Date.now() < endAt) {
    const panelText = await page.locator('.wizard-panel').first().innerText().catch(() => '');
    const statusMatch = panelText.match(/Status:\s*([A-Z_]+)/i);
    const normalized = String(statusMatch?.[1] || '').toUpperCase().trim();
    if (['IMPORTED', 'DONE', 'PARTIAL', 'FAILED'].includes(normalized)) {
      const hasResult = await page.getByRole('heading', { name: 'Resultado' }).count();
      if (hasResult > 0) {
        terminal = normalized;
        break;
      }
    }
    await wait(1000);
  }

  if (!terminal) {
    throw new Error('Fluxo não chegou a status terminal com resultado em até 60s');
  }

  await page.screenshot({ path: 'tmp/manual-import-step3-final.png', fullPage: true });
  report.push(`[OK] Processamento finalizado com status ${terminal}`);

  const timelineText = await page.locator('.wizard-timeline-lines').innerText().catch(() => '');
  const doneMatches = (timelineText.match(/Status:\s*(DONE|IMPORTED)\s*\|/gi) || []).length;
  if (doneMatches > 5) {
    throw new Error(`Possível loop de status terminal detectado (${doneMatches} repetições)`);
  }
  report.push('[OK] Sem loop excessivo de status terminal na timeline');

  console.log(report.join('\n'));
} catch (err) {
  console.error('[FAIL] Import wizard smoke', err);
  process.exitCode = 1;
} finally {
  await browser.close();
}
