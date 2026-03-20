import { expect, test } from '@playwright/test';
import {
  createProduct,
  createApiContext,
  createUser,
  createAdminApiContext,
  deleteCredential,
  deleteIfExists,
  extractGeneratedTitles,
  findFornecedorByName,
  findProductByName,
  findProductTypeByName,
  getCurrentUser,
  getProductById,
  upsertCredential,
  updateCurrentUser,
  waitForProduct,
} from './helpers/api.js';
import { e2eEmail, e2ePassword } from './helpers/runtime-env.js';

const uniqueSuffix = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
const fornecedorName = `E2E Fornecedor ${uniqueSuffix}`;
const productTypeName = `E2E Tipo ${uniqueSuffix}`;
const productDescription = `Descricao do tipo ${uniqueSuffix}`;
const attributeLabel = `Material ${uniqueSuffix}`;
const attributeKey = `material_${uniqueSuffix}`;
const productName = `E2E Produto ${uniqueSuffix}`;
const productSku = `SKU-${uniqueSuffix}`;
const seededProductPrefix = `E2E Seed ${uniqueSuffix}`;
const failedFilterPrefix = `E2E Failed ${uniqueSuffix}`;
const basicUserEmail = `e2e-basic-${uniqueSuffix}@example.com`;
const basicUserPassword = `Senha-${uniqueSuffix}-Segura123`;
const companyCredentialSecret = `sk-company-${uniqueSuffix}`;
const personalCredentialSecret = `sk-user-${uniqueSuffix}`;
const largeCatalogPath =
  'C:/Users/Julio/Desktop/TDAI 2025/Project/Backend/static/uploads/catalogs/45667a97e5744dc785308437e682a54e.pdf';

test.describe.configure({ mode: 'serial' });

test.describe('Catalog critical flow', () => {
  let api;
  let basicUserApi;
  let fornecedorId;
  let productTypeId;
  let productId;
  let originalAdminCompanyName = '';
  let adminCompanyName = '';
  let adminCompanyPatched = false;
  const seededProductIds = [];

  test.beforeAll(async ({ playwright }) => {
    api = await createAdminApiContext(playwright);
    for (let index = 1; index <= 11; index += 1) {
      const seededProduct = await createProduct(api, {
        nome_base: `${seededProductPrefix} ${index}`,
        sku: `SEED-${uniqueSuffix}-${index}`,
        descricao_original: `Produto seed ${index} para smoke E2E`,
      });
      seededProductIds.push(seededProduct.id);
    }
    const failedSeedProducts = [
      {
        nome_base: `${failedFilterPrefix} API`,
        sku: `FAILED-API-${uniqueSuffix}`,
        status_enriquecimento_web: 'FALHA_API_EXTERNA',
      },
      {
        nome_base: `${failedFilterPrefix} Fonte`,
        sku: `FAILED-FONTE-${uniqueSuffix}`,
        status_enriquecimento_web: 'NENHUMA_FONTE_ENCONTRADA',
      },
      {
        nome_base: `${failedFilterPrefix} OK`,
        sku: `FAILED-OK-${uniqueSuffix}`,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      },
    ];
    for (const produto of failedSeedProducts) {
      const created = await createProduct(api, produto);
      seededProductIds.push(created.id);
    }
  });

  test.afterAll(async () => {
    if (basicUserApi) {
      await deleteCredential(basicUserApi, 'user', 'openai');
      await basicUserApi.dispose();
    }
    await deleteCredential(api, 'company', 'openai');
    if (adminCompanyPatched) {
      await updateCurrentUser(api, { nome_empresa: originalAdminCompanyName });
    }
    if (productId) {
      await deleteIfExists(api, `/produtos/${productId}`);
    }
    if (fornecedorId) {
      await deleteIfExists(api, `/fornecedores/${fornecedorId}`);
    }
    if (productTypeId) {
      await deleteIfExists(api, `/product-types/${productTypeId}`);
    }
    for (const seededProductId of seededProductIds) {
      await deleteIfExists(api, `/produtos/${seededProductId}`);
    }
    if (api) {
      await api.dispose();
    }
  });

  async function login(page, credentials = { email: e2eEmail, password: e2ePassword }) {
    await page.goto('/login');
    await page.locator('#email').fill(credentials.email);
    await page.locator('#password').fill(credentials.password);
    await page.getByRole('button', { name: 'Entrar' }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
  }

  async function ensureAdminCompanyIdentifier() {
    if (adminCompanyName) {
      return adminCompanyName;
    }
    const currentAdmin = await getCurrentUser(api);
    originalAdminCompanyName = currentAdmin?.nome_empresa || '';
    adminCompanyName = currentAdmin?.nome_empresa || '';
    if (!adminCompanyName) {
      adminCompanyName = `Empresa E2E ${uniqueSuffix}`;
      await updateCurrentUser(api, { nome_empresa: adminCompanyName });
      adminCompanyPatched = true;
    }
    return adminCompanyName;
  }

  test('loads the admin dashboard shell with the operational layout and the products list without regressions', async ({ page }) => {
    await login(page);

    await page.goto('/dashboard');
    await expect(page.locator('.pro-card-metric').first()).toBeVisible();
    await expect(page.locator('.dashboard-command-card')).toBeVisible();
    await expect(page.getByText('Painel administrativo')).toBeVisible();
    await expect(page.getByText('Prioridades do dia')).toBeVisible();
    await expect(page.getByText('Acoes rapidas')).toHaveCount(0);
    await expect(page.getByText('Busca rapida do sistema')).toHaveCount(0);
    await expect(page.getByText('Visao geral', { exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /Abrir busca rápida/i })).toBeVisible();

    await page.getByRole('button', { name: /Abrir busca rápida/i }).click();
    await page.getByPlaceholder('Buscar no sistema').fill('Healing Prayer');
    await expect(page.getByRole('button', { name: /Healing Prayer/i }).first()).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: /Healing Prayer/i }).first().click();
    await expect(page).toHaveURL(/\/produtos(?:\?.*)?$/);
    await expect(page.locator('.loading-popup-content')).toHaveCount(0);

    await expect(page.locator('.error-message')).toHaveCount(0);
    await expect(page.locator('.product-table')).toBeVisible();
    await expect(page.locator('.product-table tbody tr')).toHaveCount(10, { timeout: 30_000 });
  });

  test('deletes a selected product without showing a success toast popup', async ({ page }) => {
    const disposableDeleteName = `E2E Delete ${uniqueSuffix}`;
    const created = await createProduct(api, {
      nome_base: disposableDeleteName,
      sku: `DELETE-${uniqueSuffix}`,
      descricao_original: 'Produto descartavel para validar exclusao sem toast',
    });
    try {
      await login(page);
      await page.goto('/produtos');
      await page.getByPlaceholder('Buscar por nome, SKU, EAN...').fill(disposableDeleteName);
      await expect(page.getByText(disposableDeleteName)).toBeVisible();

      page.once('dialog', async (dialog) => {
        await dialog.accept();
      });

      await page.locator('.product-table tbody tr').first().getByRole('checkbox').click();
      await page.getByRole('button', { name: 'Ocultar' }).click();

      await expect(page.getByText(disposableDeleteName)).toHaveCount(0);
      await expect(page.locator('.Toastify__toast--success')).toHaveCount(0);
    } finally {
      await deleteIfExists(api, `/produtos/${created.id}`);
    }
  });

  test('keeps the sidebar usable on mobile with a drawer width and backdrop', async ({ page }) => {
    await login(page);
    await page.setViewportSize({ width: 390, height: 844 });

    await page.goto('/dashboard');
    await expect(page.locator('.sidebar-backdrop')).toHaveCount(0);

    await page.getByRole('button', { name: /Alternar menu/i }).click();
    const mobileSidebar = page.locator('.sidebar.mobile.open');
    await expect(mobileSidebar).toBeVisible();
    await expect(page.locator('.sidebar-backdrop')).toBeVisible();

    const box = await mobileSidebar.boundingBox();
    expect(box).toBeTruthy();
    expect(box.width).toBeLessThanOrEqual(320);
    expect(box.x).toBeLessThanOrEqual(1);

    await page.locator('.sidebar-backdrop').click({ position: { x: 10, y: 10 } });
    await expect(page.locator('.sidebar-backdrop')).toHaveCount(0);
    await expect(page.locator('.sidebar.mobile.open')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('defaults enrichment to enriched items and clears bulk selection when the list changes', async ({ page }) => {
    await login(page);

    await page.goto('/enriquecimento');
    const scopeSelect = page.locator('main select').first();
    await expect(scopeSelect).toHaveValue('enriched');
    await expect(page.locator('.product-table tbody tr').first()).toBeVisible();

    await page.getByLabel(/Opções de seleção/i).click();
    await page.getByRole('menuitem', { name: /Selecionar página atual/i }).click();
    await expect(page.getByText(/item\(ns\) selecionado\(s\) \(página atual\)/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Enriquecer Web/i })).toBeEnabled();
    await page.getByLabel(/Opções de seleção/i).click();
    await page.getByRole('menuitem', { name: /Selecionar todos os resultados da pesquisa/i }).click();
    await expect(page.getByText(/item\(ns\) selecionado\(s\) \(todos os resultados\)/i)).toBeVisible();
    await expect(
      page.getByText(/item\(ns\) selecionado\(s\) em todos os resultados filtrados\./i)
    ).toHaveCount(0);

    await page.getByLabel(/Buscar produtos para enriquecer/i).fill('Healing Prayer');
    await expect(page.getByText(/item\(ns\) selecionado\(s\)/i)).toHaveCount(0);
    await expect(page.getByRole('button', { name: /Enriquecer Web/i })).toHaveCount(0);

    await scopeSelect.selectOption('all');
    await expect(page.locator('.product-table tbody tr').first()).toBeVisible();
  });

  test('shows process chips and keeps content navigation moving across the full list', async ({ page }) => {
    await login(page);
    await page.goto('/produtos');

    const rows = page.locator('.product-table tbody tr');
    await expect(rows).toHaveCount(10, { timeout: 30_000 });

    const firstRow = rows.first();
    await expect(firstRow.getByLabel(/Enriquecimento web:/i)).toBeVisible();
    await expect(firstRow.getByLabel(/Títulos:/i)).toBeVisible();
    await expect(firstRow.getByLabel(/Descrição:/i)).toBeVisible();

    const firstPageIds = [];
    const rowCount = await rows.count();
    for (let index = 0; index < rowCount; index += 1) {
      firstPageIds.push((await rows.nth(index).locator('td').nth(1).innerText()).trim());
    }

    const lastRow = rows.last();
    const currentId = (await lastRow.locator('td').nth(1).innerText()).trim();
    await lastRow.getByTitle(/Ver conte/i).click();

    await expect(page).toHaveURL(new RegExp(`/produtos/${currentId}/conteudo$`));
    await page.getByRole('button', { name: /Pr[oó]ximo Produto/i }).click();
    await expect.poll(() => page.url()).not.toContain(`/produtos/${currentId}/conteudo`);

    const nextId = page.url().match(/\/produtos\/(\d+)\/conteudo$/)?.[1];
    expect(nextId).toBeTruthy();
    expect(nextId).not.toBe(currentId);

    await page.getByRole('button', { name: /Produto Anterior/i }).click();
    await expect(page).toHaveURL(new RegExp(`/produtos/${currentId}/conteudo$`));
  });

  test('filters grouped failed web statuses when the user selects Falha', async ({ page }) => {
    await login(page);
    await page.goto('/produtos');

    await page.getByPlaceholder('Buscar por nome, SKU, EAN...').fill(failedFilterPrefix);
    await page.locator('main select').first().selectOption('FALHA');

    const rows = page.locator('.product-table tbody tr');
    await expect(rows).toHaveCount(2, { timeout: 30_000 });
    await expect(page.getByText(`${failedFilterPrefix} API`)).toBeVisible();
    await expect(page.getByText(`${failedFilterPrefix} Fonte`)).toBeVisible();
    await expect(page.getByText(`${failedFilterPrefix} OK`)).toHaveCount(0);
  });

  test('opens the history hub with IA and system tabs in the browser', async ({ page }) => {
    await login(page);
    await page.goto('/historico');

    await expect(page.getByText('Registros IA')).toBeVisible();
    await expect(page.getByRole('tab', { name: /Uso de IA/i })).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('.historico-table tbody tr').first()).toBeVisible({ timeout: 30_000 });

    await page.getByRole('button', { name: /^Ver$/ }).first().click();
    await expect(page.getByText(/Custo estimado/i)).toBeVisible();

    await page.getByRole('tab', { name: /Eventos do sistema/i }).click();
    await expect(page.getByRole('tab', { name: /Eventos do sistema/i })).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('.historico-table tbody tr').first()).toBeVisible({ timeout: 30_000 });

    await page.getByRole('button', { name: /^Ver$/ }).first().click();
    await expect(page.getByText(/Detalhes registrados/i)).toBeVisible();
  });

  test('supports direct generation on the dedicated content page and returns to the same paginated list', async ({ page }) => {
    await login(page);
    await page.goto('/produtos?page=2&limit=10&sort_by=id&sort_order=desc');

    const seededRow = page.locator('.product-table tbody tr', { hasText: seededProductPrefix }).first();
    await expect(seededRow).toBeVisible({ timeout: 30_000 });
    const seededProductId = Number((await seededRow.locator('td').nth(1).innerText()).trim());
    expect(seededProductId).toBeGreaterThan(0);

    await seededRow.getByTitle(/Ver conte/i).click();
    await expect(page).toHaveURL(new RegExp(`/produtos/${seededProductId}/conteudo$`));
    await expect(page.getByRole('button', { name: /Gerar t[ií]tulos com IA/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Gerar t[ií]tulos no b[aá]sico/i })).toBeVisible();

    await page.getByRole('button', { name: /Gerar t[ií]tulos no b[aá]sico/i }).click();
    await expect(page.getByText(/Geração básica de títulos iniciada/i)).toHaveCount(0);

    const updatedProduct = await waitForProduct(
      api,
      seededProductId,
      (product) => extractGeneratedTitles(product).length > 0,
      { timeout: 60_000, interval: 2_000 }
    );
    expect(extractGeneratedTitles(updatedProduct).length).toBeGreaterThan(0);

    await page.getByRole('button', { name: /Fechar conteúdo do produto/i }).click();
    await expect(page).toHaveURL(/\/produtos\?page=2&limit=10&sort_by=id&sort_order=desc$/);
    await expect(page.locator('.product-table tbody tr', { hasText: seededProductPrefix }).first()).toBeVisible();
  });

  test('starts batch description generation from products without showing an info toast popup', async ({ page }) => {
    await login(page);
    await page.goto('/produtos');

    const seededRow = page.locator('.product-table tbody tr', { hasText: seededProductPrefix }).first();
    await expect(seededRow).toBeVisible({ timeout: 30_000 });

    await seededRow.getByRole('checkbox').click();
    await page.getByRole('button', { name: /Gerar Descri/i }).click();

    await expect(page.getByText(/Geração de descrições iniciada para/i)).toHaveCount(0);
    await expect(page.locator('.Toastify__toast--info')).toHaveCount(0);
  });

  test('creates discardable supplier/type/product and validates enrichment and generation isolation', async ({ page }) => {
    await login(page);

    await page.goto('/fornecedores');
    await expect(page.getByRole('heading', { name: 'Fornecedores' })).toBeVisible();
    await expect(page.getByLabel(/Buscar fornecedores/i)).toBeVisible();
    await page.getByRole('button', { name: 'Novo Fornecedor' }).click();
    const novoFornecedorDialog = page.getByRole('dialog', { name: 'Novo Fornecedor' });
    await novoFornecedorDialog.locator('#new-forn-nome').fill(fornecedorName);
    await novoFornecedorDialog.locator('#new-forn-siteurl').fill('example.com');
    await novoFornecedorDialog.getByRole('button', { name: /^Salvar$/ }).click();
    await page.getByLabel(/Buscar fornecedores/i).fill(fornecedorName);
    await expect(page.getByText(fornecedorName)).toBeVisible({ timeout: 30_000 });

    const fornecedor = await findFornecedorByName(api, fornecedorName);
    expect(fornecedor?.id).toBeTruthy();
    fornecedorId = fornecedor.id;

    await page.goto('/tipos-de-produto');
    await page.getByRole('button', { name: /Novo Tipo/i }).click();
    await page.locator('#new-type-friendly-name').fill(productTypeName);
    await page.getByRole('button', { name: /Salvar Tipo/i }).click();
    await expect(
      page.locator('.tipos-produto-detail-panel').getByRole('heading', { name: productTypeName })
    ).toBeVisible({ timeout: 30_000 });

    const typeRow = page.locator('.tipos-produto-list li', { hasText: productTypeName });
    await typeRow.getByRole('button', { name: 'Editar' }).click();
    await page.locator('#edit-type-description').fill(productDescription);
    await page.getByRole('button', { name: /^Salvar$/ }).click();
    await typeRow.getByRole('button', { name: 'Editar' }).click();
    await expect(page.locator('#edit-type-description')).toHaveValue(productDescription);
    await page.getByRole('button', { name: /Cancelar/i }).click();

    await page.getByRole('button', { name: /Novo Atributo/i }).click();
    await page.locator('#label').fill(attributeLabel);
    await page.locator('#attribute_key').fill(attributeKey);
    await page.getByRole('button', { name: /Salvar Atributo/i }).click();
    await expect(page.getByText(attributeLabel)).toBeVisible({ timeout: 30_000 });

    const productType = await findProductTypeByName(api, productTypeName);
    expect(productType?.id).toBeTruthy();
    productTypeId = productType.id;

    await page.goto('/produtos');
    await page.getByRole('button', { name: /Novo Produto/i }).click();
    const newProductModal = page.locator('.modal-overlay').last();
    await newProductModal.getByRole('combobox', { name: /Fornecedor/i }).selectOption({ label: fornecedorName });
    await newProductModal.getByRole('combobox', { name: /Tipo de Produto/i }).selectOption({ label: productTypeName });
    await newProductModal.getByLabel(/Nome Base/i).fill(productName);
    await newProductModal.getByLabel(/SKU/i).fill(productSku);
    await newProductModal.getByRole('button', { name: /Salvar Produto/i }).click();

    await page.reload();
    await page.getByPlaceholder('Buscar por nome, SKU, EAN...').fill(productName);
    await expect(page.getByText(productName)).toBeVisible({ timeout: 30_000 });

    const createdProduct = await findProductByName(api, productName);
    expect(createdProduct?.id).toBeTruthy();
    productId = createdProduct.id;

    const productRow = page.locator('.product-table tbody tr', { hasText: productName });
    await productRow.getByTitle(/Editar produto/i).click();
    const productModal = page.locator('.modal-overlay').last();
    await productModal.getByRole('button', { name: /^Conte/i }).click();

    await productModal.getByRole('button', { name: /Enriquecer Web/i }).click();
    const enrichedProduct = await waitForProduct(
      api,
      productId,
      (product) => {
        const status = String(product?.status_enriquecimento_web || '').toUpperCase();
        return Boolean(status) && status !== 'EM_PROGRESSO' && status !== 'PENDENTE';
      },
      { timeout: 120_000, interval: 3_000 }
    );
    expect(enrichedProduct.status_enriquecimento_web).toBeTruthy();

    await productModal.getByRole('button', { name: /Gerar T/i }).click();
    const productWithTitles = await waitForProduct(
      api,
      productId,
      (product) => extractGeneratedTitles(product).length > 0,
      { timeout: 60_000 }
    );
    const titlesBeforeDescription = extractGeneratedTitles(productWithTitles);
    expect(titlesBeforeDescription.length).toBeGreaterThan(0);

    await productModal.getByRole('button', { name: /Gerar D/i }).click();
    const productWithDescription = await waitForProduct(
      api,
      productId,
      (product) => typeof product?.descricao_chat_api === 'string' && product.descricao_chat_api.trim().length > 0,
      { timeout: 60_000 }
    );
    expect(extractGeneratedTitles(productWithDescription)).toEqual(titlesBeforeDescription);

    await productModal.getByRole('button', { name: /Tela Dedicada/i }).click();
    await expect(page).toHaveURL(new RegExp(`/produtos/${productId}/conteudo$`));
    await page.reload();
    await expect(page.getByRole('heading', { name: /5 T[ií]tulos Sugeridos/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Descri/i })).toBeVisible();

    const titleCards = page.locator('.produto-conteudo-title-card');
    await expect(titleCards.first()).toContainText(titlesBeforeDescription[0], { timeout: 30_000 });

    const generatedContent = [
      await page.locator('.produto-conteudo-title-list').innerText(),
      await page.locator('.produto-conteudo-description').innerText(),
    ].join('\n');
    expect(generatedContent).not.toMatch(/\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4,}\b/);
    expect(generatedContent).not.toMatch(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
    expect(generatedContent).not.toMatch(/com[eé]rcio eletr[oô]nico/i);
    expect(generatedContent).not.toMatch(/pol[ií]tica/i);

    const finalProduct = await getProductById(api, productId);
    expect(finalProduct.descricao_chat_api).toBeTruthy();
    expect(extractGeneratedTitles(finalProduct)).toEqual(titlesBeforeDescription);
  });

  test('renders supplier logos in the list when logo_url is available', async ({ page }) => {
    const supplierLogoName = `E2E Logo ${uniqueSuffix}`;
    const logoSvg = encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96"><rect width="96" height="96" rx="20" fill="#111827"/><text x="48" y="58" text-anchor="middle" font-size="32" fill="#ffffff">LG</text></svg>'
    );
    const logoDataUrl = `data:image/svg+xml;utf8,${logoSvg}`;

    const response = await api.post('fornecedores/', {
      data: {
        nome: supplierLogoName,
        site_url: 'https://logo.example',
        logo_url: logoDataUrl,
      },
    });
    expect(response.ok()).toBeTruthy();
    const createdSupplier = await response.json();

    try {
      await login(page);
      await page.goto('/fornecedores');
      await page.getByLabel(/Buscar fornecedores/i).fill(supplierLogoName);
      await expect(page.getByText(supplierLogoName, { exact: true })).toBeVisible({
        timeout: 30_000,
      });
      await expect(page.getByAltText(`Logo de ${supplierLogoName}`)).toBeVisible();
    } finally {
      await deleteIfExists(api, `/fornecedores/${createdSupplier.id}`);
    }
  });

  test('allows previewing a catalog PDF above the old 25 MB limit', async ({ page }) => {
    await login(page);
    await page.goto('/fornecedores');

    const supplierName = page.locator('.fornecedor-table tbody tr').first().locator('td').nth(1);
    await expect(supplierName).toBeVisible({ timeout: 30_000 });
    await supplierName.click();

    const fornecedorModal = page.locator('.modal-overlay').last();
    await expect(page.getByRole('dialog', { name: /Editar Fornecedor/i })).toBeVisible();

    await fornecedorModal.getByRole('button', { name: /Importar Cat[aá]logo/i }).click();

    await page.setInputFiles('#wizard-file-input', largeCatalogPath);
    await expect(page.locator('.wizard-file-name.is-selected')).toContainText(
      '45667a97e5744dc785308437e682a54e.pdf'
    );

    await page.getByRole('button', { name: 'Gerar Preview' }).click();

    await expect(page.getByRole('heading', { name: 'Revisar e mapear dados' })).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.getByText(/FILE_TOO_LARGE/i)).toHaveCount(0);
    await expect(page.getByText(/Arquivo excede o limite configurado/i)).toHaveCount(0);
  });

  test('shows the basic dashboard and personal credential overrides for a non-admin user', async ({ page, playwright }) => {
    const companyName = await ensureAdminCompanyIdentifier();
    await upsertCredential(api, {
      scope_type: 'company',
      provider: 'openai',
      secret_value: companyCredentialSecret,
      description: 'Credencial de empresa para smoke E2E',
      is_active: true,
    });

    await createUser(playwright, {
      email: basicUserEmail,
      password: basicUserPassword,
      nome_completo: `Usuario Basico ${uniqueSuffix}`,
      nome_empresa: companyName,
    });
    basicUserApi = await createApiContext(playwright, {
      email: basicUserEmail,
      password: basicUserPassword,
    });

    await login(page, {
      email: basicUserEmail,
      password: basicUserPassword,
    });

    await page.goto('/dashboard');
    await expect(page.locator('.dashboard-command-badge')).toHaveCount(0);
    await expect(page.locator('.dashboard-side-stat')).toHaveCount(0);
    await expect(page.getByText('Painel do cliente')).toBeVisible();
    await expect(page.getByText('Visão geral', { exact: true })).toHaveCount(0);
    await expect(page.getByText('Busca rápida do sistema')).toHaveCount(0);
    await expect(page.locator('.pro-card-metric').first()).toBeVisible();

    await page.goto('/produtos');
    await expect(page.locator('.error-message')).toHaveCount(0);
    await expect(page.locator('.product-table')).toBeVisible();

    await page.goto('/plano');
    await expect(page.getByText('Capacidade do plano')).toBeVisible();
    await expect(page.getByText('Cobertura incluida')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Gratuito' })).toBeVisible();

    await page.goto('/configuracoes');
    await expect(page.getByRole('heading', { name: /Credenciais e Integrações/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Credenciais da Empresa/i })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: /Minhas Credenciais Pessoais/i })).toBeVisible();
    await expect(page.getByText(/Modo ativo para esta sessão:/i)).toBeVisible();
    await expect(page.getByText(/Básico \(sem IA\)/i)).toBeVisible();

    const openAiCard = page.locator('form', {
      has: page.getByRole('heading', { name: 'OpenAI' }),
    }).first();
    await expect(openAiCard.getByText(/Origem efetiva em uso:/i)).toContainText(/Empresa/i);

    await openAiCard.locator('#user-openai-secret_value').fill(personalCredentialSecret);
    await openAiCard.getByRole('button', { name: /^Salvar$/ }).click();
    await expect(page.getByText(/Credencial salva com sucesso/i)).toBeVisible();
    await expect(openAiCard.getByText(/Origem efetiva em uso:/i)).toContainText(/Pessoal/i);
  });
});
