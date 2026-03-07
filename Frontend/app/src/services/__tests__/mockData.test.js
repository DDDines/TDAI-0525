import { mockProducts, mockUser } from '../mockData';

describe('mockData', () => {
  test('exports deterministic mock products', () => {
    expect(mockProducts).toHaveLength(2);
    expect(mockProducts[0]).toMatchObject({
      id: 1,
      sku: 'SAN_7766700014',
      status: 'Pendente',
    });
    expect(mockProducts[1].nome).toContain('TRUCK REFRIGERATOR');
  });

  test('exports mock user profile data', () => {
    expect(mockUser).toEqual({
      nome: 'Julio User',
      avatarInitials: 'JU',
    });
  });
});
