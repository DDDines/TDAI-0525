import productTypeService from '../productTypeService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

describe('productTypeService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('gets product types and details from the expected endpoints', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: { items: [{ id: 1 }], total_items: 1 } })
      .mockResolvedValueOnce({ data: { id: 2, friendly_name: 'Pecas' } });

    await expect(productTypeService.getProductTypes({ search: 'peca' })).resolves.toEqual({
      items: [{ id: 1 }],
      total_items: 1,
    });
    await expect(productTypeService.getProductTypeDetails(2)).resolves.toEqual({
      id: 2,
      friendly_name: 'Pecas',
    });

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/product-types/', {
      params: { search: 'peca' },
    });
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/product-types/2');
  });

  test('creates, updates and deletes product types', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { id: 3 } });
    apiClient.put.mockResolvedValueOnce({ data: { id: 3, friendly_name: 'Atualizado' } });
    apiClient.delete.mockResolvedValueOnce({ data: { deleted: true } });

    await expect(
      productTypeService.createProductType({ friendly_name: 'Novo Tipo' })
    ).resolves.toEqual({ id: 3 });
    await expect(
      productTypeService.updateProductType(3, { friendly_name: 'Atualizado' })
    ).resolves.toEqual({
      id: 3,
      friendly_name: 'Atualizado',
    });
    await expect(productTypeService.deleteProductType(3)).resolves.toEqual({ deleted: true });

    expect(apiClient.post).toHaveBeenCalledWith('/product-types/', {
      friendly_name: 'Novo Tipo',
    });
    expect(apiClient.put).toHaveBeenCalledWith('/product-types/3', {
      friendly_name: 'Atualizado',
    });
    expect(apiClient.delete).toHaveBeenCalledWith('/product-types/3');
  });

  test('manages attributes inside a product type', async () => {
    apiClient.post
      .mockResolvedValueOnce({ data: { id: 10 } })
      .mockResolvedValueOnce({ data: { ok: true } });
    apiClient.put.mockResolvedValueOnce({ data: { id: 11, label: 'Cor' } });
    apiClient.delete.mockResolvedValueOnce({ data: { removed: true } });

    await expect(
      productTypeService.addAttributeToType(7, { label: 'Cor' })
    ).resolves.toEqual({ id: 10 });
    await expect(
      productTypeService.updateAttributeInType(7, 11, { label: 'Cor' })
    ).resolves.toEqual({
      id: 11,
      label: 'Cor',
    });
    await expect(productTypeService.removeAttributeFromType(7, 11)).resolves.toEqual({
      removed: true,
    });
    await expect(productTypeService.reorderAttributeInType(7, 11, 'down')).resolves.toEqual({
      ok: true,
    });

    expect(apiClient.post).toHaveBeenNthCalledWith(1, '/product-types/7/attributes/', {
      label: 'Cor',
    });
    expect(apiClient.put).toHaveBeenCalledWith('/product-types/7/attributes/11', {
      label: 'Cor',
    });
    expect(apiClient.delete).toHaveBeenCalledWith('/product-types/7/attributes/11');
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/product-types/7/attributes/11/reorder',
      { direction: 'down' }
    );
  });
});
