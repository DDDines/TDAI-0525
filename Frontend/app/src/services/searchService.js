import apiClient from './apiClient';

const searchService = {
  async searchAll(term) {
    const response = await apiClient.get('/search', { params: { q: term } });
    return response.data;
  }
};

export default searchService;
