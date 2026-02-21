import { chromium } from 'playwright';

const routes = [
  '/dashboard',
  '/produtos',
  '/fornecedores',
  '/tipos-de-produto',
  '/enriquecimento',
  '/historico',
  '/plano',
  '/configuracoes',
];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
await page.getByLabel('Email:').fill('admin@example.com');
await page.getByLabel('Senha:').fill('adminpassword');
await Promise.all([
  page.waitForURL('**/dashboard'),
  page.getByRole('button', { name: 'Entrar' }).click(),
]);

for (const route of routes) {
  await page.goto(`http://localhost:5173${route}`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: `tmp/audit-${route.replace(/\//g, '_') || 'root'}.png`, fullPage: true });
}

await browser.close();
