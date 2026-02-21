import { chromium } from 'playwright';

const BASE_URL = 'http://127.0.0.1:5173';
const EMAIL = process.env.UI_ADMIN_EMAIL || 'admin@example.com';
const PASSWORD = process.env.UI_ADMIN_PASSWORD || 'adminpassword';

async function safeClick(locator, description) {
  const count = await locator.count();
  if (count > 0) {
    await locator.first().click();
    return `[OK] ${description}`;
  }
  return `[SKIP] ${description} (elemento nao encontrado)`;
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const report = [];

try {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email:').fill(EMAIL);
  await page.getByLabel('Senha:').fill(PASSWORD);
  await Promise.all([
    page.waitForURL('**/dashboard', { timeout: 30000 }),
    page.getByRole('button', { name: 'Entrar' }).click(),
  ]);
  await page.waitForLoadState('networkidle');
  report.push('[OK] Login');

  report.push(await safeClick(page.getByRole('button', { name: /Alternar tema/i }), 'Toggle tema'));
  await page.waitForTimeout(250);

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

  for (const route of routes) {
    await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle' });
    await page.screenshot({
      path: `tmp/manual-smoke-${route.replace(/\//g, '_') || 'root'}.png`,
      fullPage: true,
    });
    report.push(`[OK] Navegou ${route}`);
  }

  await page.goto(`${BASE_URL}/produtos`, { waitUntil: 'networkidle' });
  const editProduto = page.locator('button[title="Editar produto"]');
  if ((await editProduto.count()) > 0) {
    await editProduto.first().click();
    await page.waitForTimeout(300);
    await page.keyboard.press('Escape');
    report.push('[OK] Abriu/fechou modal de edicao de produto');
  } else {
    report.push('[SKIP] Modal de edicao de produto (sem linha na tabela)');
  }

  await page.goto(`${BASE_URL}/fornecedores`, { waitUntil: 'networkidle' });
  report.push(await safeClick(page.getByRole('button', { name: 'Novo Fornecedor' }), 'Abrir modal Novo Fornecedor'));
  await page.waitForTimeout(250);
  await page.keyboard.press('Escape');

  await page.goto(`${BASE_URL}/tipos-de-produto`, { waitUntil: 'networkidle' });
  const firstType = page.locator('.type-list-panel li');
  if ((await firstType.count()) > 0) {
    await firstType.first().click();
    report.push('[OK] Selecionou tipo de produto');
  } else {
    report.push('[SKIP] Selecao de tipo de produto (lista vazia)');
  }

  await page.goto(`${BASE_URL}/configuracoes`, { waitUntil: 'networkidle' });
  report.push(await safeClick(page.getByRole('button', { name: 'Alterar Senha' }), 'Abrir modal Alterar Senha'));
  await page.waitForTimeout(250);
  await page.keyboard.press('Escape');

  console.log(report.join('\n'));
} finally {
  await browser.close();
}
