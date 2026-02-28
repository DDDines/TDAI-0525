from Backend.testing.runtime_apis import web_extractor


def test_url_deve_ser_ignorada_para_links_de_tracking():
    url = (
        "https://duckduckgo.com/y.js?ad_domain=foo.com&click_metadata=abc"
        "&u3=https://www.bing.com/aclick?x=1"
    )
    assert web_extractor.url_deve_ser_ignorada_antes_da_coleta(url) is True


def test_url_deve_ser_ignorada_para_pdf():
    url = "https://example.com/catalogo/produtos.pdf"
    assert web_extractor.url_deve_ser_ignorada_antes_da_coleta(url) is True


def test_url_valida_nao_deve_ser_ignorada():
    url = "https://produto.mercadolivre.com.br/MLB-123-peca-automotiva-_JM"
    assert web_extractor.url_deve_ser_ignorada_antes_da_coleta(url) is False


def test_normalizar_url_busca_descarta_link_tracking():
    raw = "https://www.bing.com/aclick?u=https://example.com/produto"
    assert (
        web_extractor.normalizar_url_busca(
            raw,
            "https://duckduckgo.com/html/?q=teste",
        )
        is None
    )


def test_normalizar_url_busca_expande_uddg_para_url_final():
    raw = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fproduto-1"
    normalized = web_extractor.normalizar_url_busca(
        raw,
        "https://duckduckgo.com/html/?q=teste",
    )
    assert normalized == "https://example.com/produto-1"


def test_normalizar_url_busca_descarta_tracker_duckduckgo_yjs_com_u3():
    raw = (
        "https://duckduckgo.com/y.js?ad_domain=foo.com"
        "&u3=https%3A%2F%2Fwww.bing.com%2Faclick%3Fu%3Dhttps%253A%252F%252Fexample.com%252Fproduto"
    )
    assert (
        web_extractor.normalizar_url_busca(
            raw,
            "https://duckduckgo.com/html/?q=teste",
        )
        is None
    )


def test_url_deve_ser_ignorada_para_host_baixa_relevancia_com_redirect():
    url = "https://www.google.com/url?url=https%3A%2F%2Fexample.com%2Fproduto&id=1"
    assert web_extractor.url_deve_ser_ignorada_antes_da_coleta(url) is True
