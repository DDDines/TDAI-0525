import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';

const PROJECT_ROOT = path.resolve(process.cwd(), '..', '..');
const FRONTEND_DIR = path.resolve(PROJECT_ROOT, 'Frontend', 'app');
const BACKEND_DIR = PROJECT_ROOT;
const REPORT_PATH = path.resolve(PROJECT_ROOT, 'tmp', 'ui_audit_report.json');
const TEST_PDF = path.resolve(PROJECT_ROOT, 'Backend', 'tests', 'test_assets', 'scanned.pdf');

const BASE_URL = 'http://127.0.0.1:5173';
const API_URL = 'http://127.0.0.1:8000';
const ADMIN_EMAIL = 'admin@example.com';
const ADMIN_PASSWORD = 'adminpassword';

const results = [];
const consoleErrors = [];
const pageErrors = [];
const networkErrors = [];
const backgroundLogs = [];
const spawned = [];

function record(name, ok, details = '') {
  results.push({ name, ok, details });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHttp(url, timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok || [401, 403].includes(res.status)) return true;
    } catch {
      // ignore and retry
    }
    await sleep(1000);
  }
  return false;
}

async function isServerUp(url) {
  try {
    const res = await fetch(url);
    return res.ok || [401, 403].includes(res.status);
  } catch {
    return false;
  }
}

function spawnLogged(command, args, cwd, label, extraEnv = {}) {
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, ...extraEnv },
    shell: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.on('data', (data) => {
    backgroundLogs.push(`[${label}:stdout] ${String(data).trimEnd()}`);
  });
  child.stderr.on('data', (data) => {
    backgroundLogs.push(`[${label}:stderr] ${String(data).trimEnd()}`);
  });
  spawned.push({ child, label });
  return child;
}

async function ensureServers() {
  const backendReady = await isServerUp(`${API_URL}/api/v1/auth/social/config`);
  if (!backendReady) {
    spawnLogged(
      '..\\.venv\\Scripts\\python',
      ['run_backend.py', '--reload', 'false', '--host', '127.0.0.1', '--port', '8000'],
      BACKEND_DIR,
      'backend',
      { BACKEND_RELOAD: 'False' }
    );
  }

  const frontendReady = await isServerUp(`${BASE_URL}/login`);
  if (!frontendReady) {
    spawnLogged('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173'], FRONTEND_DIR, 'frontend');
  }

  const backendUp = await waitForHttp(`${API_URL}/api/v1/auth/social/config`, 120000);
  const frontendUp = await waitForHttp(`${BASE_URL}/login`, 120000);
  record('Backend online', backendUp, backendUp ? 'API respondeu' : 'Timeout aguardando API');
  record('Frontend online', frontendUp, frontendUp ? 'Vite respondeu' : 'Timeout aguardando frontend');
  if (!backendUp || !frontendUp) {
    throw new Error('Servidores não iniciaram a tempo.');
  }
}

async function safeStep(name, fn) {
  try {
    await fn();
    record(name, true, 'OK');
  } catch (err) {
    record(name, false, err?.message || String(err));
  }
}

async function clickIfVisible(locator, timeout = 8000) {
  await locator.first().waitFor({ state: 'visible', timeout });
  await locator.first().click();
}

async function closeModalsIfAny(page) {
  const closeByAria = page.getByRole('button', { name: /fechar|close/i });
  if (await closeByAria.first().isVisible().catch(() => false)) {
    await closeByAria.first().click();
  }
  const closeX = page.locator('.modal-close-button, .modal-close, button[aria-label="Fechar"]');
  if (await closeX.first().isVisible().catch(() => false)) {
    await closeX.first().click();
  }
}

async function runUiAudit() {
  await ensureServers();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => {
    pageErrors.push(String(err));
  });
  page.on('response', (response) => {
    const req = response.request();
    const resourceType = req.resourceType();
    const url = response.url();
    const status = response.status();
    if ((resourceType === 'xhr' || resourceType === 'fetch') && status >= 400) {
      networkErrors.push({ url, status, method: req.method() });
    }
  });

  await safeStep('Login com admin', async () => {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill(ADMIN_EMAIL);
    await page.locator('#password').fill(ADMIN_PASSWORD);
    await page.getByRole('button', { name: /^entrar$/i }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
  });

  await safeStep('Dashboard carregou', async () => {
    await page.getByRole('heading', { name: /dashboard/i }).first().waitFor({ state: 'visible' });
  });

  await safeStep('Theme toggle alterna claro/escuro', async () => {
    const body = page.locator('body');
    const beforeDark = await body.evaluate((el) => el.classList.contains('dark'));
    await page.getByRole('button', { name: /alternar tema/i }).click();
    await sleep(300);
    const afterDark = await body.evaluate((el) => el.classList.contains('dark'));
    if (beforeDark === afterDark) throw new Error('Tema não alternou no primeiro clique');
    await page.getByRole('button', { name: /alternar tema/i }).click();
    await sleep(300);
    const finalDark = await body.evaluate((el) => el.classList.contains('dark'));
    if (finalDark !== beforeDark) throw new Error('Tema não retornou ao estado original');
  });

  await safeStep('Abrir menu do usuário e navegar para Configurações', async () => {
    await page.locator('.user-avatar').click();
    await page.getByRole('button', { name: /configurações/i }).click();
    await page.waitForURL(/\/configuracoes/, { timeout: 15000 });
    await page.getByRole('heading', { name: /configurações/i }).first().waitFor({ state: 'visible' });
  });

  await safeStep('Salvar perfil em Configurações', async () => {
    await page.getByRole('button', { name: /salvar alterações do perfil/i }).click();
    await sleep(1500);
  });

  await safeStep('Abrir modal de alteração de senha e fechar', async () => {
    await page.getByRole('button', { name: /alterar senha/i }).click();
    await sleep(500);
    await closeModalsIfAny(page);
  });

  const navTargets = [
    { name: 'Dashboard', url: /\/dashboard/ },
    { name: 'Produtos', url: /\/produtos/ },
    { name: 'Fornecedores', url: /\/fornecedores/ },
    { name: 'Tipos de Produto', url: /\/tipos-de-produto/ },
    { name: 'Enriquecimento', url: /\/enriquecimento/ },
    { name: 'Histórico', url: /\/historico/ },
    { name: 'Meu Plano', url: /\/plano/ },
    { name: 'Configurações', url: /\/configuracoes/ },
  ];

  for (const item of navTargets) {
    await safeStep(`Navegação sidebar: ${item.name}`, async () => {
      await page.locator('aside').getByRole('link', { name: new RegExp(item.name, 'i') }).click();
      await page.waitForURL(item.url, { timeout: 15000 });
    });
  }

  await safeStep('Produtos: atualizar lista', async () => {
    await page.goto(`${BASE_URL}/produtos`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: /atualizar lista/i }).click();
    await sleep(1000);
  });

  await safeStep('Produtos: abrir novo produto e fechar modal', async () => {
    await page.getByRole('button', { name: /\+ novo produto/i }).click();
    await sleep(500);
    await closeModalsIfAny(page);
  });

  await safeStep('Produtos: abrir edição do primeiro item e fechar modal', async () => {
    const editBtn = page.locator('button[title="Editar produto"]').first();
    await clickIfVisible(editBtn);
    await sleep(600);
    await closeModalsIfAny(page);
  });

  await safeStep('Produtos: iniciar enriquecimento em lote (1 item)', async () => {
    const firstCheckbox = page.locator('table tbody tr input[type="checkbox"]').first();
    await clickIfVisible(firstCheckbox);
    const enrichBtn = page.getByRole('button', { name: /enriquecer web/i }).first();
    await clickIfVisible(enrichBtn);
    await sleep(2000);
  });

  await safeStep('Enriquecimento: selecionar e iniciar enriquecimento', async () => {
    await page.goto(`${BASE_URL}/enriquecimento`, { waitUntil: 'domcontentloaded' });
    const firstCheckbox = page.locator('table tbody tr input[type="checkbox"]').first();
    await clickIfVisible(firstCheckbox);
    await page.getByRole('button', { name: /enriquecer web/i }).first().click();
    await sleep(2000);
  });

  await safeStep('Fornecedores: abrir modal de edição na primeira linha', async () => {
    await page.goto(`${BASE_URL}/fornecedores`, { waitUntil: 'domcontentloaded' });
    const firstRow = page.locator('#forn-table tbody tr').first();
    await clickIfVisible(firstRow);
    await page.getByRole('heading', { name: /editar fornecedor/i }).waitFor({ state: 'visible' });
  });

  await safeStep('Fornecedor info: salvar alterações', async () => {
    await page.getByRole('button', { name: /salvar alterações/i }).click();
    await sleep(1500);
  });

  await safeStep('Fornecedor importação: abrir wizard', async () => {
    await page.getByRole('button', { name: /importar cat/i }).first().click();
    await page.getByRole('button', { name: /^importar catálogo$/i }).first().click();
    await page.getByRole('heading', { name: /passo 1/i }).waitFor({ state: 'visible' });
  });

  await safeStep('Wizard passo 1->2: upload + gerar preview', async () => {
    await page.locator('#wizard-file-input').setInputFiles(TEST_PDF);
    await page.getByRole('button', { name: /gerar preview/i }).click();
    await page.getByRole('heading', { name: /passo 2/i }).waitFor({ state: 'visible', timeout: 60000 });
  });

  await safeStep('Wizard passo 2: abrir mapeamento e confirmar', async () => {
    await page.getByRole('button', { name: /definir mapeamento/i }).click();
    await page.getByRole('heading', { name: /mapear colunas/i }).waitFor({ state: 'visible' });

    const productTypeSelect = page.locator('#column-mapping-product-type-select');
    if (await productTypeSelect.isVisible().catch(() => false)) {
      const values = await productTypeSelect.locator('option').evaluateAll((opts) =>
        opts.map((o) => o.value).filter((v) => v)
      );
      if (values.length > 0) {
        await productTypeSelect.selectOption(values[0]);
      }
    }

    const mappingSelects = page.locator('.mapping-table tbody tr td select');
    const total = await mappingSelects.count();
    if (total > 0) {
      await mappingSelects.nth(0).selectOption('auto:sku_nome').catch(async () => {
        await mappingSelects.nth(0).selectOption('nome_base');
      });
    }
    if (total > 1) {
      await mappingSelects.nth(1).selectOption('descricao_original').catch(() => {});
    }

    await page.getByRole('button', { name: /confirmar mapeamento/i }).click();
    await sleep(500);
  });

  await safeStep('Wizard passo 2->3: iniciar processamento', async () => {
    const typeSelect = page.locator('#wizard-product-type');
    if (await typeSelect.isVisible().catch(() => false)) {
      const values = await typeSelect.locator('option').evaluateAll((opts) =>
        opts.map((o) => o.value).filter((v) => v)
      );
      if (values.length > 0) {
        await typeSelect.selectOption(values[0]);
      }
    }
    await page.getByRole('button', { name: /iniciar processamento/i }).click();
    await page.getByRole('heading', { name: /passo 3/i }).waitFor({ state: 'visible', timeout: 30000 });
  });

  await safeStep('Wizard processamento: aguardar status terminal', async () => {
    const statusLine = page.locator('.wizard-processing-header');
    await statusLine.waitFor({ state: 'visible', timeout: 10000 });
    const start = Date.now();
    let terminal = false;
    while (Date.now() - start < 90000) {
      const text = (await statusLine.innerText()).toUpperCase();
      if (text.includes('IMPORTED') || text.includes('FAILED') || text.includes('PARTIAL') || text.includes('DONE')) {
        terminal = true;
        break;
      }
      await sleep(2000);
    }
    if (!terminal) throw new Error('Status terminal não alcançado em 90s');
  });

  await safeStep('Fechar wizard e modal de fornecedor', async () => {
    const closeBtns = page.getByRole('button', { name: /^fechar$/i });
    if (await closeBtns.count()) {
      await closeBtns.first().click().catch(() => {});
    }
    await sleep(500);
    await closeModalsIfAny(page);
  });

  await safeStep('Tipos de Produto: abrir modal novo tipo e fechar', async () => {
    await page.goto(`${BASE_URL}/tipos-de-produto`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: /\+ novo tipo de produto/i }).click();
    await sleep(500);
    await closeModalsIfAny(page);
  });

  await safeStep('Tipos de Produto: selecionar tipo e abrir modal de atributo', async () => {
    const firstType = page.locator('.type-list-panel ul li').first();
    await clickIfVisible(firstType);
    await page.getByRole('button', { name: /\+ novo atributo/i }).click();
    await sleep(500);
    await closeModalsIfAny(page);
  });

  await safeStep('Meu Plano: clique em ações de assinatura', async () => {
    await page.goto(`${BASE_URL}/plano`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: /upgrade de plano/i }).click();
    await sleep(300);
    await page.getByRole('button', { name: /cancelar assinatura/i }).click();
    await sleep(300);
  });

  await safeStep('Logout pelo botão Sair', async () => {
    await page.getByRole('button', { name: /sair/i }).first().click();
    await page.waitForURL(/\/login/, { timeout: 15000 });
  });

  await browser.close();
}

async function cleanup() {
  for (const { child, label } of spawned.reverse()) {
    if (!child.killed) {
      child.kill('SIGTERM');
      await sleep(500);
      if (!child.killed) child.kill('SIGKILL');
    }
    backgroundLogs.push(`[${label}] finalizado`);
  }
}

async function main() {
  try {
    await runUiAudit();
  } catch (err) {
    record('Execução geral do auditor', false, err?.message || String(err));
  } finally {
    await cleanup();
  }

  const passed = results.filter((r) => r.ok).length;
  const failed = results.filter((r) => !r.ok).length;

  const report = {
    generated_at: new Date().toISOString(),
    totals: { passed, failed, steps: results.length },
    steps: results,
    console_errors: consoleErrors,
    page_errors: pageErrors,
    network_errors: networkErrors,
    background_logs_tail: backgroundLogs.slice(-200),
  };

  await fs.mkdir(path.dirname(REPORT_PATH), { recursive: true });
  await fs.writeFile(REPORT_PATH, JSON.stringify(report, null, 2), 'utf-8');

  console.log(`REPORT_PATH=${REPORT_PATH}`);
  console.log(`PASSED=${passed}`);
  console.log(`FAILED=${failed}`);
}

main();
