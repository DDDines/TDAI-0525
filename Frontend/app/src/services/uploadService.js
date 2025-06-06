// Frontend/app/src/services/uploadService.js
import apiClient from './apiClient';

/**
 * Envia um arquivo de imagem para o endpoint de upload do backend.
 * @param {File} file O objeto de arquivo de imagem a ser carregado.
 * @returns {Promise<object>} Uma promessa que resolve para os dados da resposta da API,
 * contendo a URL pública e outros metadados do arquivo.
 */
export const uploadProductImage = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
        // O apiClient já tem o prefixo /api/v1
        // O backend espera um POST em /uploads/upload-image-product/
        const response = await apiClient.post('/uploads/upload-image-product/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    } catch (error) {
        console.error("Erro no serviço de upload de imagem:", error.response?.data || error.message);
        // Lança o erro para que o componente que chama possa tratá-lo
        throw error.response?.data || new Error('Falha no upload da imagem.');
    }
};
