"""Module test web data extractor metadata runtime.

Contains backend logic related to test web data extractor metadata runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations

from Backend.testing.runtime_apis import web_extractor


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_metadata_runtime_limpa_strings_e_listas():
        """Run test metadata runtime limpa strings e listas in this workflow."""
        runtime = web_extractor.MetadataExtractionRuntime()
    
        cleaned = runtime.limpar_valor_metadado(["  a  ", None, "  b   c  "])
    
        assert cleaned == ["a", "b c"]

    def test_metadata_runtime_normaliza_json_ld_preferencial():
        """Run test metadata runtime normaliza json ld preferencial in this workflow."""
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
        """Run test metadata runtime fallback para opengraph in this workflow."""
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

    def test_metadata_runtime_extracts_dom_fallback_for_supplier_catalog_pages():
        """Extract focused product facts from DOM when schema metadata is absent."""
        runtime = web_extractor.MetadataExtractionRuntime()
        html = """
        <html>
          <head><title>AMALCABURIO - RESERVATÓRIO DE AR 20 L</title></head>
          <body>
            <section id="produto-detalhe">
              <div class="breadcrumb">
                <a href="/">home</a>
                <a href="/Produtos">produtos</a>
                <a href="/Produtos/implementos">implementos</a>
                <a href="/Produtos/implementos/mercedes-benz">mercedes benz</a>
                <a href="/Produtos/implementos/mercedes-benz/ln-608-708">ln 608/708</a>
                <a href="/Produtos/implementos/mercedes-benz/ln-608-708/reservatorio-de-ar-20-l">987</a>
              </div>
              <div class="top">
                <span class="categoria">987</span>
                <span class="produto">RESERVATÓRIO DE AR 20 L</span>
              </div>
              <div class="right">
                <h3>N° original | similar</h3>
                <dl><dd></dd><dd>308 430 70 05 (MERCEDES BENZ)</dd></dl>
                <div>
                  <h4>Aplicação</h4>
                  <p>MERCEDES BENZ LN 608/708</p>
                </div>
                <img src="/Uploads/Product/exemplo_Detalhe.jpg" />
              </div>
            </section>
          </body>
        </html>
        """

        metadata = runtime.extrair_metadados_estruturados(
            html,
            "https://www.amalcaburio.com.br/Produtos/implementos/mercedes-benz/ln-608-708/reservatorio-de-ar-20-l",
        )
        result = runtime.normalizar_dados_de_metadados(metadata)

        assert result["nome"] == "RESERVATÓRIO DE AR 20 L"
        assert result["sku"] == "987"
        assert result["codigo_original"] == "308 430 70 05 (MERCEDES BENZ)"
        assert result["aplicacao"] == "MERCEDES BENZ LN 608/708"
        assert result["imagem_url"].endswith("/Uploads/Product/exemplo_Detalhe.jpg")
        assert "Aplicacao: MERCEDES BENZ LN 608/708" in result["texto_estruturado_produto"]
        assert result["especificacoes_tecnicas_dict"]["Codigo de catalogo"] == "987"

test_metadata_runtime_limpa_strings_e_listas = _TopLevelFunctionSurface.test_metadata_runtime_limpa_strings_e_listas
test_metadata_runtime_normaliza_json_ld_preferencial = _TopLevelFunctionSurface.test_metadata_runtime_normaliza_json_ld_preferencial
test_metadata_runtime_fallback_para_opengraph = _TopLevelFunctionSurface.test_metadata_runtime_fallback_para_opengraph
test_metadata_runtime_extracts_dom_fallback_for_supplier_catalog_pages = (
    _TopLevelFunctionSurface.test_metadata_runtime_extracts_dom_fallback_for_supplier_catalog_pages
)






