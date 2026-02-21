import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const EMAIL = process.env.UI_ADMIN_EMAIL || 'admin@example.com';
const PASSWORD = process.env.UI_ADMIN_PASSWORD || 'adminpassword';

test('manual visual smoke: dashboard, configuracoes, plano', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });

  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email:').fill(EMAIL);
  await page.getByLabel('Senha:').fill(PASSWORD);
  await Promise.all([
    page.waitForURL('**/dashboard', { timeout: 20000 }),
    page.getByRole('button', { name: 'Entrar' }).click(),
  ]);

  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'tmp/manual-dashboard-light.png', fullPage: true });

  const themeToggle = page.getByRole('button', { name: /Alternar tema/i });
  await expect(themeToggle).toBeVisible();

  const themeToggleStyles = await themeToggle.evaluate((el) => {
    const cs = window.getComputedStyle(el);
    return {
      background: cs.backgroundColor,
      borderStyle: cs.borderStyle,
      borderWidth: cs.borderWidth,
      width: cs.width,
      height: cs.height,
    };
  });
  console.log('theme-toggle-styles', themeToggleStyles);

  await themeToggle.click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp/manual-dashboard-dark.png', fullPage: true });

  await page.goto(`${BASE_URL}/configuracoes`, { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Configurações' }).first()).toBeVisible();
  await page.screenshot({ path: 'tmp/manual-configuracoes.png', fullPage: true });

  await page.goto(`${BASE_URL}/plano`, { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Meu Plano' }).first()).toBeVisible();
  await page.screenshot({ path: 'tmp/manual-plano.png', fullPage: true });
});
