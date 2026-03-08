import { expect, test } from '@playwright/test';
import {
  createProduct,
  createAdminApiContext,
  deleteIfExists,
  extractGeneratedTitles,
  findFornecedorByName,
  findProductByName,
  findProductTypeByName,
  getProductById,
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

test.describe.configure({ mode: 'serial' });

test.describe('Catalog critical flow', () => {
  let api;
  let fornecedorId;
  let productTypeId;
  let productId;
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
  });

  test.afterAll(async () => {
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

  async function login(page) {
    await page.goto('/login');
    await page.locator('#email').fill(e2eEmail);
    await page.locator('#password').fill(e2ePassword);
    await page.getByRole('button', { name: 'Entrar' }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
  }

  test('shows process chips and keeps content navigation moving across the full list', async ({ page }) => {
    await login(page);
    await page.goto('/produtos');

    const rows = page.locator('.product-table tbody tr');
    await expect(rows).toHaveCount(10, { timeout: 30_000 });

    const firstRow = rows.first();
    await expect(firstRow.getByText('Web')).toBeVisible();
    await expect(firstRow.getByText('Tit')).toBeVisible();
    await expect(firstRow.getByText('Desc')).toBeVisible();

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
    expect(firstPageIds).not.toContain(nextId);

    await page.getByRole('button', { name: /Produto Anterior/i }).click();
    await expect(page).toHaveURL(new RegExp(`/produtos/${currentId}/conteudo$`));
  });

  test('creates discardable supplier/type/product and validates enrichment and generation isolation', async ({ page }) => {
    await login(page);

    await page.goto('/fornecedores');
    await page.getByRole('button', { name: 'Novo Fornecedor' }).click();
    await page.locator('#new-forn-nome').fill(fornecedorName);
    await page.locator('#new-forn-siteurl').fill('example.com');
    await page.locator('#new-forn-modal').getByRole('button', { name: /^Salvar$/ }).click();
    await page.getByLabel(/Buscar fornecedores/i).fill(fornecedorName);
    await expect(page.getByText(fornecedorName)).toBeVisible({ timeout: 30_000 });

    const fornecedor = await findFornecedorByName(api, fornecedorName);
    expect(fornecedor?.id).toBeTruthy();
    fornecedorId = fornecedor.id;

    await page.goto('/tipos-de-produto');
    await page.getByRole('button', { name: /\+ Novo Tipo de Produto/i }).click();
    await page.locator('#new-type-friendly-name').fill(productTypeName);
    await page.getByRole('button', { name: /Salvar Tipo/i }).click();
    await expect(page.getByText(`Atributos para: ${productTypeName}`)).toBeVisible({ timeout: 30_000 });

    const typeRow = page.locator('.type-list-panel li', { hasText: productTypeName });
    await typeRow.getByTitle('Editar tipo').click();
    await page.locator('#edit-type-description').fill(productDescription);
    await page.getByRole('button', { name: /^Salvar$/ }).click();
    await typeRow.getByTitle('Editar tipo').click();
    await expect(page.locator('#edit-type-description')).toHaveValue(productDescription);
    await page.getByRole('button', { name: /Cancelar/i }).click();

    await page.getByRole('button', { name: /\+ Novo Atributo/i }).click();
    await page.locator('#label').fill(attributeLabel);
    await page.locator('#attribute_key').fill(attributeKey);
    await page.getByRole('button', { name: /Salvar Atributo/i }).click();
    await expect(page.getByText(attributeLabel)).toBeVisible({ timeout: 30_000 });

    const productType = await findProductTypeByName(api, productTypeName);
    expect(productType?.id).toBeTruthy();
    productTypeId = productType.id;

    await page.goto('/produtos');
    await page.getByRole('button', { name: /\+ Novo Produto/i }).click();
    await page.getByRole('combobox', { name: /Fornecedor/i }).selectOption({ label: fornecedorName });
    await page.getByRole('combobox', { name: /Tipo de Produto/i }).selectOption({ label: productTypeName });
    await page.getByLabel(/Nome Base/i).fill(productName);
    await page.getByLabel(/SKU/i).fill(productSku);
    await page.getByRole('button', { name: /Salvar Produto/i }).click();

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
});
