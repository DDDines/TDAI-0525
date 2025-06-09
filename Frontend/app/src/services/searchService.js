import apiClient from './apiClient';

const searchService = {
  async searchAll(term) {
    const params = term ? { q: term } : {};
    const response = await apiClient.get('/search', { params });
    return response.data;
  }
};

export default searchService;
