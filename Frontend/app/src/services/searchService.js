import apiClient from './apiClient';

const searchService = {
  async searchAll(term) {
    const trimmed = term ? term.trim() : '';
    const params = trimmed ? { q: trimmed } : {};
    // Include trailing slash to avoid redirect that might drop auth headers
    const response = await apiClient.get('/search/', { params });
    return response.data;
  }
};

export default searchService;
