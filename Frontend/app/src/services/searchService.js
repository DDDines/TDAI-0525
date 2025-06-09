import apiClient from './apiClient';

const searchService = {
  async searchAll(term) {
    const params = term ? { q: term } : {};
    // Include trailing slash to avoid redirect that might drop auth headers
    const response = await apiClient.get('/search/', { params });
    return response.data;
  }
};

export default searchService;
