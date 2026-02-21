import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
await page.getByLabel('Email:').fill('admin@example.com');
await page.getByLabel('Senha:').fill('adminpassword');
await Promise.all([
  page.waitForURL('**/dashboard'),
  page.getByRole('button', { name: 'Entrar' }).click(),
]);

await page.waitForLoadState('networkidle');
await page.screenshot({ path: 'tmp/manual-dashboard-light-2.png', fullPage: true });
await page.goto('http://localhost:5173/configuracoes', { waitUntil: 'networkidle' });
await page.screenshot({ path: 'tmp/manual-configuracoes-light.png', fullPage: true });
await page.goto('http://localhost:5173/plano', { waitUntil: 'networkidle' });
await page.screenshot({ path: 'tmp/manual-plano-light.png', fullPage: true });

await browser.close();
