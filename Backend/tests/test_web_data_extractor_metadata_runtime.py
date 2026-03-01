from __future__ import annotations

from Backend.testing.runtime_apis import web_extractor


class _TopLevelFunctionSurface:

    def test_metadata_runtime_limpa_strings_e_listas():
        runtime = web_extractor.MetadataExtractionRuntime()
    
        cleaned = runtime.limpar_valor_metadado(["  a  ", None, "  b   c  "])
    
        assert cleaned == ["a", "b c"]

    def test_metadata_runtime_normaliza_json_ld_preferencial():
        runtime = web_extractor.MetadataExtractionRuntime()
        metadata = {
            "json-ld_product_candidate": {
                "name": "Produto X",
                "description": "Descricao X",
                "image": {"url": "https://img.test/x.png"},
                "brand": {"name": "Marca X"},
                "sku": "SKU123",
                "offers": {
                    "price": "199.90",
                    "priceCurrency": "BRL",
                    "availability": "https://schema.org/InStock",
                },
            }
        }
    
        result = runtime.normalizar_dados_de_metadados(metadata)
    
        assert result["nome"] == "Produto X"
        assert result["descricao_curta"] == "Descricao X"
        assert result["imagem_url"] == "https://img.test/x.png"
        assert result["marca"] == "Marca X"
        assert result["sku"] == "SKU123"
        assert result["preco"] == "199.90"
        assert result["moeda_preco"] == "BRL"
        assert result["disponibilidade"] == "InStock"

    def test_metadata_runtime_fallback_para_opengraph():
        runtime = web_extractor.MetadataExtractionRuntime()
        metadata = {
            "opengraph": {
                "og:title": "Titulo OG",
                "og:description": "Descricao OG",
                "og:image": "https://img.test/og.png",
                "og:site_name": "Site OG",
            }
        }
    
        result = runtime.normalizar_dados_de_metadados(metadata)
    
        assert result == {
            "nome": "Titulo OG",
            "descricao_curta": "Descricao OG",
            "imagem_url": "https://img.test/og.png",
            "marca": "Site OG",
        }

test_metadata_runtime_limpa_strings_e_listas = _TopLevelFunctionSurface.test_metadata_runtime_limpa_strings_e_listas
test_metadata_runtime_normaliza_json_ld_preferencial = _TopLevelFunctionSurface.test_metadata_runtime_normaliza_json_ld_preferencial
test_metadata_runtime_fallback_para_opengraph = _TopLevelFunctionSurface.test_metadata_runtime_fallback_para_opengraph






