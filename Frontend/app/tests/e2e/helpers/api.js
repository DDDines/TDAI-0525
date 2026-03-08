import { expect } from '@playwright/test';
import { e2eEmail, e2ePassword } from './runtime-env.js';

const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT || '8012';
const backendApiBaseUrl = `http://127.0.0.1:${backendPort}/api/v1/`;

async function parseJson(response) {
  const body = await response.text();
  return body ? JSON.parse(body) : null;
}

export function extractGeneratedTitles(product) {
  const directTitles = Array.isArray(product?.titulos_sugeridos) ? product.titulos_sugeridos : [];
  const rawTitles = Array.isArray(product?.dados_brutos_web?.titulos_sugeridos_gerados)
    ? product.dados_brutos_web.titulos_sugeridos_gerados
    : [];
  const merged = [...directTitles, ...rawTitles]
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  const seen = new Set();
  const unique = [];
  for (const item of merged) {
    const folded = item.toLowerCase();
    if (seen.has(folded)) continue;
    seen.add(folded);
    unique.push(item);
  }
  return unique.slice(0, 10);
}

export async function createAdminApiContext(playwright) {
  const bootstrapContext = await playwright.request.newContext();
  let tokenResponse = null;
  const deadline = Date.now() + 60_000;

  while (Date.now() < deadline) {
    tokenResponse = await bootstrapContext.post(`${backendApiBaseUrl}auth/token`, {
      form: {
        username: e2eEmail,
        password: e2ePassword,
      },
    });
    if (tokenResponse.ok()) {
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }

  expect(tokenResponse?.ok()).toBeTruthy();
  const tokenData = await parseJson(tokenResponse);
  expect(tokenData?.access_token).toBeTruthy();
  await bootstrapContext.dispose();

  return playwright.request.newContext({
    baseURL: backendApiBaseUrl,
    extraHTTPHeaders: {
      Authorization: `Bearer ${tokenData.access_token}`,
    },
  });
}

export async function findFornecedorByName(api, nome) {
  const response = await api.get('fornecedores/', {
    params: { skip: 0, limit: 100, termo_busca: nome },
  });
  expect(response.ok()).toBeTruthy();
  const data = await parseJson(response);
  return (data?.items || []).find((item) => item.nome === nome) || null;
}

export async function findProductTypeByName(api, friendlyName) {
  const response = await api.get('product-types/', {
    params: { skip: 0, limit: 500 },
  });
  expect(response.ok()).toBeTruthy();
  const data = await parseJson(response);
  return (Array.isArray(data) ? data : []).find((item) => item.friendly_name === friendlyName) || null;
}

export async function findProductByName(api, nome) {
  const response = await api.get('produtos/', {
    params: { search: nome, skip: 0, limit: 50 },
  });
  expect(response.ok()).toBeTruthy();
  const data = await parseJson(response);
  return (data?.items || []).find((item) => item.nome_base === nome) || null;
}

export async function getProductById(api, productId) {
  const response = await api.get(`produtos/${productId}`);
  expect(response.ok()).toBeTruthy();
  return parseJson(response);
}

export async function waitForProduct(api, productId, predicate, { timeout = 90_000, interval = 2_000 } = {}) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const product = await getProductById(api, productId);
    if (predicate(product)) {
      return product;
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
  throw new Error(`Timed out waiting for product ${productId}.`);
}

export async function deleteIfExists(api, resourcePath) {
  try {
    const normalizedPath = String(resourcePath || '').replace(/^\/+/, '');
    const response = await api.delete(normalizedPath);
    return response.ok() || response.status() === 404;
  } catch {
    return false;
  }
}
