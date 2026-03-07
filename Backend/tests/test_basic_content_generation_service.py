"""Module test basic content generation service.

Contains backend logic related to test basic content generation service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

from Backend.application.services.basic_content_generation_service import (
    BasicContentGenerationService,
)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @staticmethod
    def _build_service(produto):
        """Build service with a repository stub bound to a product fixture."""

        class _ProductRepositoryStub:
            """Repository stub exposing only the method used by the service."""

            def __init__(self, _session):
                """Initialize collaborators and configuration required by this component."""
                self._produto = produto

            def get_produto(self, *, produto_id):
                """Return the configured product fixture."""
                _ = produto_id
                return self._produto

        return BasicContentGenerationService(
            product_repository_factory=_ProductRepositoryStub
        )

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_respeita_limite():
        """Run test gerar titulos basicos respeita limite in this workflow."""
        produto = SimpleNamespace(
            id=10,
            nome_base="Filtro de Ar",
            marca="Bosch",
            modelo="X1",
            sku="ABC123",
            ean="7891234567890",
            categoria_original="Filtro",
            categoria_mapeada=None,
            fornecedor=SimpleNamespace(nome="Fornecedor A"),
            dynamic_attributes={},
            dados_brutos_web={},
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=10,
            user=SimpleNamespace(id=1),
            num_titulos=2,
        )

        assert len(titulos) == 2
        assert any("Filtro de Ar" in titulo for titulo in titulos)

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_inclui_campos_relevantes():
        """Run test gerar descricao basica inclui campos relevantes in this workflow."""
        produto = SimpleNamespace(
            id=20,
            nome_base="Pastilha de Freio",
            marca="MarcaX",
            modelo="PX-20",
            sku="PF20",
            ean="",
            categoria_original="Freios",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={
                "Material": "Ceramica",
                "Aplicacao": "Dianteira",
            },
            dados_brutos_web={
                "descricao_curta": "Composto com alta resistencia termica.",
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=20,
            user=SimpleNamespace(id=1),
            tamanho_palavras=80,
        )

        assert "Pastilha de Freio" in descricao
        assert "SKU: PF20" in descricao
        assert "Material: Ceramica" in descricao

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_padrao_entrega_cinco_opcoes():
        """Run test gerar titulos basicos padrao entrega cinco opcoes in this workflow."""
        produto = SimpleNamespace(
            id=30,
            nome_base="Paralama Dianteiro",
            marca="Pickup Parts",
            modelo="FD-2010",
            sku="PP-1081",
            ean="",
            categoria_original="Lataria",
            categoria_mapeada=None,
            fornecedor=SimpleNamespace(nome="Fornecedor B"),
            dynamic_attributes={},
            dados_brutos_web={
                "palavras_chave_seo_relevantes_lista": [
                    "paralama",
                    "ford cargo",
                    "linha pesada",
                ],
                "especificacoes_tecnicas_dict": {
                    "Aplicacao": "Ford Cargo",
                },
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=30,
            user=SimpleNamespace(id=1),
        )

        assert len(titulos) == 5
        assert any("Paralama Dianteiro" in titulo for titulo in titulos)

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_aproveita_contexto_web():
        """Run test gerar descricao basica aproveita contexto web in this workflow."""
        produto = SimpleNamespace(
            id=31,
            nome_base="Suporte de Fixacao",
            marca="Pickup Parts",
            modelo="SP1081",
            sku="SP1081",
            ean="7890000000000",
            categoria_original="Fixacao",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "descricao_detalhada_seo": "Suporte reforcado para linha pesada e alta durabilidade.",
                "lista_caracteristicas_beneficios_bullets": [
                    "Estrutura em metal resistente",
                    "Instalacao simplificada",
                ],
                "palavras_chave_seo_relevantes_lista": [
                    "suporte reforcado",
                    "linha pesada",
                ],
                "especificacoes_tecnicas_dict": {
                    "Material": "Metal",
                    "Aplicacao": "Caminhoes",
                },
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=31,
            user=SimpleNamespace(id=1),
            tamanho_palavras=160,
        )

        assert "Suporte reforcado para linha pesada" in descricao
        assert "Destaques:" in descricao
        assert "Palavras-chave:" in descricao
        assert "Material: Metal" in descricao

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_remove_historico_empresa_inferido():
        """Run test gerar descricao basica remove historico empresa inferido in this workflow."""
        produto = SimpleNamespace(
            id=32,
            nome_base="Paralama Externo",
            marca="Rodoplast",
            modelo="IV-FD",
            sku="900484",
            ean="",
            categoria_original="Lataria",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "descricao_detalhada_seo": (
                    "Paralama externo em plastico reforcado. "
                    "A Uouu iniciou suas atividades no ano de 2015 e segue no mercado."
                ),
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=32,
            user=SimpleNamespace(id=1),
            tamanho_palavras=120,
        )

        assert "Paralama externo em plastico reforcado" in descricao
        assert "iniciou suas atividades" not in descricao.lower()
        assert "ano de 2015" not in descricao.lower()

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_respeita_template_customizado():
        """Ensure custom title templates are applied in non-AI mode."""
        produto = SimpleNamespace(
            id=33,
            nome_base="Amortecedor Traseiro",
            marca="Monroe",
            modelo="M-889",
            sku="AM889",
            ean="",
            categoria_original="Suspensao",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "palavras_chave_seo_relevantes_lista": ["hidraulico"],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=33,
            user=SimpleNamespace(id=1),
            num_titulos=3,
            template_titulo="{marca} | {nome_base} | {sku}",
        )

        assert len(titulos) == 3
        assert titulos[0] == "Monroe | Amortecedor Traseiro | AM889"

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_remove_ruido_empresa_e_contato():
        """Ensure title generation strips company/contact artifacts from noisy web context."""
        produto = SimpleNamespace(
            id=35,
            nome_base="de AR 60 Litros Uouu Comercio Eletronico 986 345 430 8205",
            marca="",
            modelo="",
            sku="AR60",
            ean="",
            categoria_original="Climatizacao",
            categoria_mapeada=None,
            fornecedor=SimpleNamespace(nome="Uouu Comercio Eletronico"),
            dynamic_attributes={},
            dados_brutos_web={
                "nome": "de AR 60 Litros Uouu Comercio Eletronico 986 345 430 8205",
                "palavras_chave_seo_relevantes_lista": [
                    "favoritos",
                    "qualidade",
                    "seus",
                    "whatsapp 11 99888 7766",
                ],
                "especificacoes_tecnicas_dict": {
                    "Contato": "986 345 430 8205",
                },
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=35,
            user=SimpleNamespace(id=1),
            num_titulos=5,
        )

        assert len(titulos) == 5
        assert all("comercio" not in titulo.lower() for titulo in titulos)
        assert all("eletronico" not in titulo.lower() for titulo in titulos)
        assert all("whatsapp" not in titulo.lower() for titulo in titulos)
        assert all("favoritos" not in titulo.lower() for titulo in titulos)
        assert all("qualidade" not in titulo.lower() for titulo in titulos)
        assert all("seus" not in titulo.lower() for titulo in titulos)
        assert all(not re.search(r"\d{3}\s+\d{3}\s+\d{3}", titulo) for titulo in titulos)
        assert any("AR 60 Litros" in titulo for titulo in titulos)

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_aplica_template_customizado():
        """Ensure custom description templates are applied in non-AI mode."""
        produto = SimpleNamespace(
            id=34,
            nome_base="Bomba Dagua",
            marca="Pierburg",
            modelo="PD-10",
            sku="BD100",
            ean="7891111111111",
            categoria_original="Arrefecimento",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={"Material": "Aluminio"},
            dados_brutos_web={
                "descricao_curta": "Com rotor reforcado para alta durabilidade.",
                "palavras_chave_seo_relevantes_lista": ["bomba dagua", "motor diesel"],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=34,
            user=SimpleNamespace(id=1),
            tamanho_palavras=120,
            template_descricao=(
                "Produto: {nome_base} ({marca})\n"
                "Resumo: {descricao_web}\n"
                "Specs:\n{specs}\n"
                "Tags: {keywords}"
            ),
        )

        assert "Produto: Bomba Dagua (Pierburg)" in descricao
        assert "Specs:" in descricao
        assert "Material: Aluminio" in descricao
        assert "Tags: motor diesel" in descricao
        assert "bomba dagua, motor diesel" not in descricao

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_filtra_keywords_fracas_do_contexto_web():
        """Ensure weak promotional keywords do not leak into the description template."""
        produto = SimpleNamespace(
            id=36,
            nome_base="Reservatorio de Ar",
            marca="Rochepecas",
            modelo="",
            sku="RA-20",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={"Material": "Metalico"},
            dados_brutos_web={
                "descricao_curta": "Reservatorio de ar para linha pesada.",
                "palavras_chave_seo_relevantes_lista": [
                    "seguran",
                    "pol",
                    "sua",
                    "tranquilidade",
                    "reservatorio de ar",
                    "linha pesada",
                ],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=36,
            user=SimpleNamespace(id=1),
            tamanho_palavras=120,
        )

        lowered = descricao.lower()
        assert "palavras-chave:" in lowered
        assert "seguran" not in lowered
        assert "tranquilidade" not in lowered
        assert " sua" not in lowered
        assert "reservatorio de ar" in lowered
        assert "linha pesada" in lowered

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_ignora_keywords_fracas_do_contexto_web():
        """Ensure weak web keywords do not appear in generated title suggestions."""
        produto = SimpleNamespace(
            id=37,
            nome_base="Reservatorio de Ar 20 Litros",
            marca="Rochepecas",
            modelo="",
            sku="RA20",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "palavras_chave_seo_relevantes_lista": [
                    "seguran",
                    "pol",
                    "sua",
                    "tranquilidade",
                    "criptografia",
                    "reservatorio de ar",
                    "linha pesada",
                ],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=37,
            user=SimpleNamespace(id=1),
            num_titulos=5,
        )

        lowered_titles = [titulo.lower() for titulo in titulos]
        assert len(titulos) == 5
        assert all("seguran" not in titulo for titulo in lowered_titles)
        assert all("tranquilidade" not in titulo for titulo in lowered_titles)
        assert all("criptografia" not in titulo for titulo in lowered_titles)
        assert all(" sua " not in f" {titulo} " for titulo in lowered_titles)
        assert any("reservatorio de ar 20 litros" in titulo for titulo in lowered_titles)

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_filtra_specs_internas_e_promocionais():
        """Ensure internal dynamic attrs and promotional specs do not leak into the basic description."""
        produto = SimpleNamespace(
            id=38,
            nome_base="Reservatorio de Ar 20 Litros",
            marca="Rochepecas",
            modelo="",
            sku="RA20",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={
                "titulo_auto": "Reservatorio de Ar 20 Litros - ROCHEPECAS 3084307005",
                "Desc_Auto": "Descricao longa com ruido de loja.",
                "Material": "Metalico",
                "marca": "Mercadocar",
            },
            dados_brutos_web={
                "descricao_curta": "Reservatorio de ar para linha pesada.",
                "especificacoes_tecnicas_dict": {
                    "Contato": "5000. Sua compra online protegida. Criptografia e seguranca para garantir tranquilidade.",
                    "Aplicacao": "Mercedes Benz",
                },
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=38,
            user=SimpleNamespace(id=1),
            tamanho_palavras=140,
        )

        lowered = descricao.lower()
        assert "material: metalico" in lowered
        assert "aplicacao: mercedes benz" in lowered
        assert "titulo_auto" not in lowered
        assert "desc_auto" not in lowered
        assert "sua compra online" not in lowered
        assert "criptografia" not in lowered

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_remove_boilerplate_promocional_do_contexto_web():
        """Ensure contact/payment/policy boilerplate is stripped from the web description context."""
        produto = SimpleNamespace(
            id=39,
            nome_base="Reservatorio de Ar 20 Litros",
            marca="Rochepecas",
            modelo="",
            sku="RA20",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "descricao_detalhada_seo": (
                    "Reservatorio de ar para Mercedes Benz com alta performance. "
                    "Se surgirem duvidas, entre em contato conosco clicando aqui ou atraves do telefone 11 2206-5000. "
                    "Criptografia e seguranca para garantir tranquilidade. "
                    "Politica de troca e devolucao simples e transparente."
                ),
                "lista_caracteristicas_beneficios_bullets": [
                    "Aplicacao em linha pesada",
                    "Parcelamento em ate 10x sem juros",
                ],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=39,
            user=SimpleNamespace(id=1),
            tamanho_palavras=140,
        )

        lowered = descricao.lower()
        assert "reservatorio de ar para mercedes benz com alta performance" in lowered
        assert "entre em contato" not in lowered
        assert "telefone" not in lowered
        assert "criptografia" not in lowered
        assert "politica de troca" not in lowered
        assert "sem juros" not in lowered

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_remove_boilerplate_promocional_em_segmentos_com_ponto_e_virgula():
        """Ensure semicolon-separated promotional snippets are stripped from the web context."""
        produto = SimpleNamespace(
            id=42,
            nome_base="Reservatorio de Ar 20 Litros",
            marca="Rochepecas",
            modelo="",
            sku="RA20",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "descricao_detalhada_seo": (
                    "Reservatorio de ar para Mercedes Benz com alta performance. "
                    "Destaques: Se surgirem duvidas, entre em contato conosco clicando aqui; "
                    "Confira nossas politicas; Devolva se nao for a peca certa."
                ),
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=42,
            user=SimpleNamespace(id=1),
            tamanho_palavras=120,
        )

        lowered = descricao.lower()
        assert "reservatorio de ar para mercedes benz com alta performance" in lowered
        assert "entre em contato" not in lowered
        assert "confira nossas politicas" not in lowered
        assert "devolva" not in lowered

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_ignora_keywords_redundantes_da_identidade():
        """Ensure keywords that only repeat the product identity do not pollute title suggestions."""
        produto = SimpleNamespace(
            id=40,
            nome_base="Reservatorio de Ar 20 Litros",
            marca="Rochepecas",
            modelo="",
            sku="RA20",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "nome": "Reservatorio de Ar 20 Litros - ROCHEPECAS 3084307005",
                "palavras_chave_seo_relevantes_lista": [
                    "reservatorio",
                    "rochepecas",
                    "litros",
                    "mercedes benz",
                ],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=40,
            user=SimpleNamespace(id=1),
            num_titulos=5,
        )

        lowered_titles = [titulo.lower() for titulo in titulos]
        assert len(titulos) == 5
        assert all("rochepecas rochepecas" not in titulo for titulo in lowered_titles)
        assert "reservatorio de ar 20 litros rochepecas reservatorio" not in lowered_titles
        assert "reservatorio de ar 20 litros rochepecas rochepecas" not in lowered_titles
        assert "reservatorio de ar 20 litros rochepecas litros" not in lowered_titles
        assert any("reservatorio de ar 20 litros rochepecas" == titulo for titulo in lowered_titles)

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_recupera_keywords_do_texto_limpo():
        """Ensure clean description text can recover useful title hints when keyword list is weak."""
        produto = SimpleNamespace(
            id=41,
            nome_base="Reservatorio de Ar 20 Litros",
            marca="Rochepecas",
            modelo="",
            sku="",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "descricao_detalhada_seo": (
                    "Reservatorio de ar 20 litros para Mercedes Benz com alta performance "
                    "e aplicacao em freios e suspensao."
                ),
                "palavras_chave_seo_relevantes_lista": [
                    "seguran",
                    "pol",
                    "sua",
                    "tranquilidade",
                ],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=41,
            user=SimpleNamespace(id=1),
            num_titulos=5,
        )

        lowered_titles = [titulo.lower() for titulo in titulos]
        assert len(titulos) == 5
        assert any("mercedes" in titulo for titulo in lowered_titles)
        assert all("opcao" not in titulo for titulo in lowered_titles)

    @pytest.mark.asyncio
    async def test_geracao_basica_prefere_marca_do_nome_gerado_quando_marca_salva_parece_loja():
        """Prefer manufacturer hints from generated names over noisy store names saved in ``marca``."""
        produto = SimpleNamespace(
            id=43,
            nome_base="Reservatorio de AR 20 Litros",
            nome_chat_api="Reservatorio de Ar 20 Litros ROCHEPECAS 3084307005",
            descricao_original=(
                "Reservatorio de Ar 20 Litros ROCHEPECAS 3084307005 para Mercedes Benz. "
                "Aplicacao em freios e suspensao."
            ),
            descricao_chat_api=None,
            marca="Mercadocar",
            modelo="",
            sku="987 308 430 7005",
            ean="",
            categoria_original="Freio a Ar",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={
                "titulo_auto": "Reservatorio de Ar 20 Litros - ROCHEPECAS 3084307005",
                "Material": "Metalico",
            },
            dados_brutos_web={
                "descricao_detalhada_seo": (
                    "Reservatorio de ar para Mercedes Benz com aplicacao em freios e suspensao."
                ),
                "palavras_chave_seo_relevantes_lista": ["mercedes benz", "freios", "suspensao"],
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=43,
            user=SimpleNamespace(id=1),
            num_titulos=5,
        )
        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=43,
            user=SimpleNamespace(id=1),
            tamanho_palavras=120,
        )

        lowered_titles = [titulo.lower() for titulo in titulos]
        assert any("rochepecas" in titulo for titulo in lowered_titles)
        assert all("mercadocar" not in titulo for titulo in lowered_titles)
        assert "rochepecas" in descricao.lower()
        assert "marca mercadocar" not in descricao.lower()


_build_service = _TopLevelFunctionSurface._build_service
test_gerar_titulos_basicos_respeita_limite = _TopLevelFunctionSurface.test_gerar_titulos_basicos_respeita_limite
test_gerar_descricao_basica_inclui_campos_relevantes = _TopLevelFunctionSurface.test_gerar_descricao_basica_inclui_campos_relevantes
test_gerar_titulos_basicos_padrao_entrega_cinco_opcoes = _TopLevelFunctionSurface.test_gerar_titulos_basicos_padrao_entrega_cinco_opcoes
test_gerar_descricao_basica_aproveita_contexto_web = _TopLevelFunctionSurface.test_gerar_descricao_basica_aproveita_contexto_web
test_gerar_descricao_basica_remove_historico_empresa_inferido = _TopLevelFunctionSurface.test_gerar_descricao_basica_remove_historico_empresa_inferido
test_gerar_titulos_basicos_respeita_template_customizado = _TopLevelFunctionSurface.test_gerar_titulos_basicos_respeita_template_customizado
test_gerar_titulos_basicos_remove_ruido_empresa_e_contato = _TopLevelFunctionSurface.test_gerar_titulos_basicos_remove_ruido_empresa_e_contato
test_gerar_descricao_basica_aplica_template_customizado = _TopLevelFunctionSurface.test_gerar_descricao_basica_aplica_template_customizado
test_gerar_descricao_basica_filtra_keywords_fracas_do_contexto_web = _TopLevelFunctionSurface.test_gerar_descricao_basica_filtra_keywords_fracas_do_contexto_web
test_gerar_titulos_basicos_ignora_keywords_fracas_do_contexto_web = _TopLevelFunctionSurface.test_gerar_titulos_basicos_ignora_keywords_fracas_do_contexto_web
test_gerar_descricao_basica_filtra_specs_internas_e_promocionais = _TopLevelFunctionSurface.test_gerar_descricao_basica_filtra_specs_internas_e_promocionais
test_gerar_descricao_basica_remove_boilerplate_promocional_do_contexto_web = _TopLevelFunctionSurface.test_gerar_descricao_basica_remove_boilerplate_promocional_do_contexto_web
test_gerar_descricao_basica_remove_boilerplate_promocional_em_segmentos_com_ponto_e_virgula = _TopLevelFunctionSurface.test_gerar_descricao_basica_remove_boilerplate_promocional_em_segmentos_com_ponto_e_virgula
test_gerar_titulos_basicos_ignora_keywords_redundantes_da_identidade = _TopLevelFunctionSurface.test_gerar_titulos_basicos_ignora_keywords_redundantes_da_identidade
test_gerar_titulos_basicos_recupera_keywords_do_texto_limpo = _TopLevelFunctionSurface.test_gerar_titulos_basicos_recupera_keywords_do_texto_limpo
test_geracao_basica_prefere_marca_do_nome_gerado_quando_marca_salva_parece_loja = _TopLevelFunctionSurface.test_geracao_basica_prefere_marca_do_nome_gerado_quando_marca_salva_parece_loja
