module.exports = {
  testEnvironment: 'jsdom',
  setupFiles: ['<rootDir>/jest.setup.js'],
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/**/__tests__/**',
    '!src/**/*.test.{js,jsx}',
    '!src/main.jsx',
  ],
  coverageThreshold: {
    global: {
      statements: 37,
      branches: 37,
      functions: 36,
      lines: 37,
    },
    './src/services/apiClient.js': {
      statements: 100,
      branches: 80,
      functions: 100,
      lines: 100,
    },
    './src/services/configService.js': {
      statements: 100,
      branches: 75,
      functions: 100,
      lines: 100,
    },
    './src/services/productService.js': {
      statements: 75,
      branches: 35,
      functions: 100,
      lines: 75,
    },
    './src/services/fornecedorService.js': {
      statements: 50,
      branches: 10,
      functions: 100,
      lines: 50,
    },
    './src/contexts/AuthContext.jsx': {
      statements: 85,
      branches: 60,
      functions: 100,
      lines: 85,
    },
    './src/contexts/AppExperienceContext.jsx': {
      statements: 90,
      branches: 65,
      functions: 85,
      lines: 90,
    },
    './src/pages/ProdutosPage.jsx': {
      statements: 70,
      branches: 60,
      functions: 65,
      lines: 70,
    },
  },
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest'
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(png|jpg|jpeg|gif|svg)$': '<rootDir>/__mocks__/fileMock.js'
  }
};
