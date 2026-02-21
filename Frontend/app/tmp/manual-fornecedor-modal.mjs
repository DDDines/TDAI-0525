import { chromium } from 'playwright';

const BASE_URL = 'http://127.0.0.1:5173';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

try {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email:').fill('admin@example.com');
  await page.getByLabel('Senha:').fill('adminpassword');
  await Promise.all([
    page.waitForURL('**/dashboard'),
    page.getByRole('button', { name: 'Entrar' }).click(),
  ]);

  await page.goto(`${BASE_URL}/fornecedores`, { waitUntil: 'networkidle' });
  const row = page.locator('table tbody tr').first();
  await row.click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp/manual-fornecedor-modal-info.png', fullPage: true });

  await page.getByRole('button', { name: 'Importar Catálogo' }).click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp/manual-fornecedor-modal-import.png', fullPage: true });

  await page.getByRole('button', { name: 'Arquivos' }).click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp/manual-fornecedor-modal-files.png', fullPage: true });

  console.log('[OK] Capturas do modal de fornecedor geradas');
} finally {
  await browser.close();
}
