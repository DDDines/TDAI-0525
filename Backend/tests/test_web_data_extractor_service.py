"""Module test web data extractor service.

Contains backend logic related to test web data extractor service and documents its role in the OOP architecture.
"""

from Backend.testing.runtime_apis import web_extractor


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _search_workflow():
        """Run search workflow in this workflow."""
        return web_extractor.WebDataExtractorRuntime().search_workflow

    def test_url_deve_ser_ignorada_para_links_de_tracking():
        """Run test url deve ser ignorada para links de tracking in this workflow."""
        url = (
            "https://duckduckgo.com/y.js?ad_domain=foo.com&click_metadata=abc"
            "&u3=https://www.bing.com/aclick?x=1"
        )
        assert _search_workflow().url_deve_ser_ignorada_antes_da_coleta(url) is True

    def test_url_deve_ser_ignorada_para_pdf():
        """Run test url deve ser ignorada para pdf in this workflow."""
        url = "https://example.com/catalogo/produtos.pdf"
        assert _search_workflow().url_deve_ser_ignorada_antes_da_coleta(url) is False

    def test_url_valida_nao_deve_ser_ignorada():
        """Run test url valida nao deve ser ignorada in this workflow."""
        url = "https://produto.mercadolivre.com.br/MLB-123-peca-automotiva-_JM"
        assert _search_workflow().url_deve_ser_ignorada_antes_da_coleta(url) is False

    def test_normalizar_url_busca_descarta_link_tracking():
        """Run test normalizar url busca descarta link tracking in this workflow."""
        raw = "https://www.bing.com/aclick?u=https://example.com/produto"
        assert (
            _search_workflow().normalizar_url_busca(
                raw,
                "https://duckduckgo.com/html/?q=teste",
            )
            is None
        )

    def test_normalizar_url_busca_expande_uddg_para_url_final():
        """Run test normalizar url busca expande uddg para url final in this workflow."""
        raw = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fproduto-1"
        normalized = _search_workflow().normalizar_url_busca(
            raw,
            "https://duckduckgo.com/html/?q=teste",
        )
        assert normalized == "https://example.com/produto-1"

    def test_normalizar_url_busca_descarta_tracker_duckduckgo_yjs_com_u3():
        """Run test normalizar url busca descarta tracker duckduckgo yjs com u3 in this workflow."""
        raw = (
            "https://duckduckgo.com/y.js?ad_domain=foo.com"
            "&u3=https%3A%2F%2Fwww.bing.com%2Faclick%3Fu%3Dhttps%253A%252F%252Fexample.com%252Fproduto"
        )
        assert (
            _search_workflow().normalizar_url_busca(
                raw,
                "https://duckduckgo.com/html/?q=teste",
            )
            is None
        )

    def test_url_deve_ser_ignorada_para_host_baixa_relevancia_com_redirect():
        """Run test url deve ser ignorada para host baixa relevancia com redirect in this workflow."""
        url = "https://www.google.com/url?url=https%3A%2F%2Fexample.com%2Fproduto&id=1"
        assert _search_workflow().url_deve_ser_ignorada_antes_da_coleta(url) is True

_search_workflow = _TopLevelFunctionSurface._search_workflow
test_url_deve_ser_ignorada_para_links_de_tracking = _TopLevelFunctionSurface.test_url_deve_ser_ignorada_para_links_de_tracking
test_url_deve_ser_ignorada_para_pdf = _TopLevelFunctionSurface.test_url_deve_ser_ignorada_para_pdf
test_url_valida_nao_deve_ser_ignorada = _TopLevelFunctionSurface.test_url_valida_nao_deve_ser_ignorada
test_normalizar_url_busca_descarta_link_tracking = _TopLevelFunctionSurface.test_normalizar_url_busca_descarta_link_tracking
test_normalizar_url_busca_expande_uddg_para_url_final = _TopLevelFunctionSurface.test_normalizar_url_busca_expande_uddg_para_url_final
test_normalizar_url_busca_descarta_tracker_duckduckgo_yjs_com_u3 = _TopLevelFunctionSurface.test_normalizar_url_busca_descarta_tracker_duckduckgo_yjs_com_u3
test_url_deve_ser_ignorada_para_host_baixa_relevancia_com_redirect = _TopLevelFunctionSurface.test_url_deve_ser_ignorada_para_host_baixa_relevancia_com_redirect














