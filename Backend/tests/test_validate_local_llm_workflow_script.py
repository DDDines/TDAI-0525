"""Tests for the local LM Studio workflow validation script helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_local_llm_workflow.py"
SPEC = importlib.util.spec_from_file_location("validate_local_llm_workflow", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_validate_generated_text_flags_boilerplate_and_missing_identity():
    issues = MODULE.validate_generated_text(
        output_text="Compra online com entrega rapida. Ligue agora para 11 99999-0000.",
        required_tokens=("bosch", "bomba", "12v"),
        min_words=3,
        max_words=40,
    )

    assert "telefone ou bloco numerico suspeito" in issues
    assert any(issue.startswith("boilerplate comercial:") for issue in issues)
    assert "identidade do produto insuficiente" in issues


def test_validate_generated_text_flags_title_cta_and_generic_suffix():
    issues = MODULE.validate_generated_text(
        output_text="Exiba seus Tiers com o Tier Displayer Decor",
        required_tokens=("tier", "displayer"),
        min_words=3,
        max_words=20,
        check_title_style=True,
    )

    assert "cta/promocional indevido" in issues
    assert "complemento generico" in issues


def test_validate_generated_text_accepts_concrete_product_copy():
    issues = MODULE.validate_generated_text(
        output_text=(
            "Bomba de combustivel Bosch 12V com pressao estavel, baixo ruido "
            "e aplicacao em motores flex."
        ),
        required_tokens=("bosch", "bomba", "12v"),
        forbidden_terms=("man",),
        min_words=8,
        max_words=40,
    )

    assert issues == []


def test_validate_generated_text_flags_missing_sections_and_truncated_bullet():
    issues = MODULE.validate_generated_text(
        output_text=(
            "Resumo tecnico:\n"
            "Bomba de combustivel Bosch 12V para motores flex com baixo ruido.\n"
            "Aplicacao:\n"
            "- motores flex"
        ),
        required_tokens=("bosch", "bomba", "12v"),
        min_words=8,
        max_words=80,
        expected_headings=MODULE.DESCRIPTION_REQUIRED_HEADINGS,
    )

    assert "secao obrigatoria ausente: Referencia:" in issues
    assert "bullet final truncado" in issues


def test_validate_generated_text_flags_summary_that_repeats_full_product_name():
    issues = MODULE.validate_generated_text(
        output_text=(
            "Filtro de Ar Primario Mann C27010\n"
            "Resumo tecnico:\n"
            "Filtro de Ar Primario Mann C27010 Elemento filtrante primario para retencao de particulas em operacao severa.\n"
            "Aplicacao:\nlinha pesada\n"
            "Referencia:\nC27010\n"
            "Material:\nNao informado.\n"
            "Conteudo da embalagem:\nNao informado.\n"
            "Especificacoes tecnicas:\n- Referencia: C27010\n"
            "Destaques tecnicos:\n- Elemento filtrante primario."
        ),
        required_tokens=("filtro", "ar", "mann"),
        min_words=20,
        max_words=120,
        expected_headings=MODULE.DESCRIPTION_REQUIRED_HEADINGS,
    )

    assert "resumo repete o nome completo do produto" in issues


def test_validate_generated_text_flags_duplicate_spec_keys_in_structured_description():
    issues = MODULE.validate_generated_text(
        output_text=(
            "Kit de Embreagem Luk 62030847\n"
            "Resumo tecnico:\n"
            "Kit de embreagem para linha leve com acoplamento estavel.\n"
            "Aplicacao:\nlinha leve\n"
            "Referencia:\n62030847\n"
            "Material:\naco temperado\n"
            "Conteudo da embalagem:\ndisco, plato e rolamento\n"
            "Especificacoes tecnicas:\n"
            "- Material: aco temperado\n"
            "- material: aco\n"
            "- Temperatura Cor: 6500K\n"
            "Destaques tecnicos:\n"
            "- Acoplamento estavel."
        ),
        required_tokens=("kit", "embreagem", "luk"),
        min_words=20,
        max_words=120,
        expected_headings=MODULE.DESCRIPTION_REQUIRED_HEADINGS,
    )

    assert "chave duplicada em especificacoes tecnicas: material" in issues


def test_validate_generated_text_flags_semantic_duplicate_content_keys():
    issues = MODULE.validate_generated_text(
        output_text=(
            "Filtro de Oleo Mahle OC90\n"
            "Resumo tecnico:\n"
            "Filtro de oleo roscavel para lubrificacao de motores.\n"
            "Aplicacao:\nlubrificacao de motores\n"
            "Referencia:\nOC90\n"
            "Material:\ncarcaca metalica\n"
            "Conteudo da embalagem:\n1 filtro\n"
            "Especificacoes tecnicas:\n"
            "- Conteudo da embalagem: 1 filtro\n"
            "- Conteudo: 1 filtro\n"
            "Destaques tecnicos:\n"
            "- Retencao eficiente de impurezas."
        ),
        required_tokens=("filtro", "oleo", "mahle"),
        min_words=20,
        max_words=120,
        expected_headings=MODULE.DESCRIPTION_REQUIRED_HEADINGS,
    )

    assert "chave duplicada em especificacoes tecnicas: conteudo_da_embalagem" in issues


def test_validate_generated_text_flags_description_cta_when_not_title_mode():
    issues = MODULE.validate_generated_text(
        output_text="Estrutura resistente para exposicao. Adquira ja o seu display.",
        required_tokens=("display",),
        min_words=4,
        max_words=40,
    )

    assert "cta/promocional na descricao" in issues


def test_validate_generated_text_flags_low_value_placeholder_summary_in_description_mode():
    issues = MODULE.validate_generated_text(
        output_text=(
            "Tier Displayer\n"
            "Resumo tecnico:\n"
            "Tier Displayer e um componente para exibicao em camadas.\n"
            "Sua funcao especifica depende do contexto de uso nao automotivo.\n"
            "Aplicacao:\nNao informado.\n"
            "Referencia:\nNao informado.\n"
            "Material:\nNao informado.\n"
            "Conteudo da embalagem:\nNao informado.\n"
            "Especificacoes tecnicas:\n- Sem especificacoes tecnicas adicionais.\n"
            "Destaques tecnicos:\n- Exibicao em camadas."
        ),
        required_tokens=("tier", "displayer"),
        min_words=20,
        max_words=120,
        expected_headings=MODULE.DESCRIPTION_REQUIRED_HEADINGS,
    )

    assert "resumo generico/placeholder" in issues


def test_validate_generated_text_flags_forbidden_standalone_term():
    issues = MODULE.validate_generated_text(
        output_text="Kit de Embreagem Luk Cambio Manual Man Ref 62030847",
        required_tokens=("embreagem", "luk", "manual"),
        forbidden_terms=("man",),
        min_words=6,
        max_words=20,
        check_title_style=True,
    )

    assert "token proibido presente: man" in issues


def test_build_smoke_product_payload_contains_realistic_identity():
    payload = MODULE.build_smoke_product_payload(
        fornecedor_id=7,
        product_type_id=9,
        product_type_ids={"automotivo": 9, "eletronicos": 11, "vestuario": 12},
    )

    assert payload["fornecedor_id"] == 7
    assert payload["product_type_id"] == 9
    assert "bosch" in payload["nome_base"].lower()
    assert payload["dynamic_attributes"]["voltagem"] == "12V"
    assert payload["sku"].startswith("LLM-SMOKE-")


def test_build_smoke_product_cases_returns_diverse_suite():
    cases = MODULE.build_smoke_product_cases(
        fornecedor_id=7,
        product_type_id=9,
        product_type_ids={"automotivo": 9, "eletronicos": 11, "vestuario": 12},
    )

    assert [case["id"] for case in cases] == [
        "pump_bosch_flex",
        "lamp_philips_h7",
        "filter_mann_primary",
        "sensor_abs_delphi",
        "brake_pad_trw_front",
        "oil_filter_mahle_oc90",
        "wheel_bearing_skf_vkba",
        "clutch_kit_luk_manual",
        "spark_plug_ngk_bkr6e11",
        "timing_belt_contitech_ct1028",
        "wiper_bosch_aerofit_af26",
        "headphone_jbl_tune_510bt",
        "charger_baseus_gan_65w",
        "mouse_logitech_m170_preto",
        "teclado_redragon_kumara_k552",
        "smart_tv_samsung_50_4k",
        "camiseta_dryfit_unissex",
        "jaqueta_impermeavel_masculina",
        "calca_jeans_masculina_slim",
        "tenis_corrida_feminino_mesh",
        "moletom_canguru_unissex_cinza",
        "bermuda_tactel_masculina_preta",
    ]
    assert all(case["payload"]["fornecedor_id"] == 7 for case in cases)
    assert all(case["required_tokens"] for case in cases)
    assert all(case["expect_reference_variant"] is True for case in cases)
    assert all(any(char.isdigit() for char in case["payload"]["modelo"]) for case in cases)
    product_type_ids_by_case = {case["id"]: case["payload"]["product_type_id"] for case in cases}
    assert product_type_ids_by_case["pump_bosch_flex"] == 9
    assert product_type_ids_by_case["spark_plug_ngk_bkr6e11"] == 9
    assert product_type_ids_by_case["headphone_jbl_tune_510bt"] == 11
    assert product_type_ids_by_case["smart_tv_samsung_50_4k"] == 11
    assert product_type_ids_by_case["camiseta_dryfit_unissex"] == 12
    assert product_type_ids_by_case["bermuda_tactel_masculina_preta"] == 12
    forbidden_by_id = {case["id"]: tuple(case.get("forbidden_terms") or ()) for case in cases}
    assert forbidden_by_id["filter_mann_primary"] == ("man",)
    assert forbidden_by_id["clutch_kit_luk_manual"] == ("man",)


def test_validate_title_set_flags_incomplete_reference_and_low_diversity():
    issues = MODULE.validate_title_set(
        titles=[
            "Bomba de combustivel Bosch 12V flex",
            "Bomba de combustivel Bosch 12V Ref",
            "Bomba de combustivel Bosch 12V flex",
        ],
        required_tokens=("bomba", "bosch", "12v"),
        expect_reference_variant=True,
    )

    assert "titulos duplicados" in issues
    assert any("referencia incompleta no titulo" in issue for issue in issues)
    assert any("baixa diversidade de variacoes de titulo" in issue for issue in issues)


def test_validate_title_set_flags_low_value_variant_and_forbidden_term():
    issues = MODULE.validate_title_set(
        titles=[
            "Jogo de Pastilhas de Freio TRW Dianteira",
            "Jogo de Pastilhas de Freio TRW Dianteira Ref GDB242",
            "Jogo de Pastilhas de Freio TRW Dianteira TRW",
        ],
        required_tokens=("pastilhas", "freio", "trw", "dianteira"),
        expect_reference_variant=True,
    )

    assert any("variacao sem ganho semantico" in issue for issue in issues)

    generic_material_issues = MODULE.validate_title_set(
        titles=[
            "Bomba de combustivel Bosch 12V flex",
            "Bomba de combustivel Bosch 12V flex Ref 0580454094",
            "Bomba de combustivel Bosch 12V flex Aco",
        ],
        required_tokens=("bomba", "bosch", "12v"),
        expect_reference_variant=True,
    )
    assert any("variacao material generica" in issue for issue in generic_material_issues)

    composite_material_issues = MODULE.validate_title_set(
        titles=[
            "Kit de Embreagem Luk Cambio Manual",
            "Kit de Embreagem Luk Cambio Manual Ref 62030847",
            "Kit de Embreagem Luk Cambio Manual aco e composto de friccao",
        ],
        required_tokens=("embreagem", "luk", "manual"),
        expect_reference_variant=True,
    )
    assert any("variacao material generica" in issue for issue in composite_material_issues)

    forbidden_issues = MODULE.validate_title_set(
        titles=[
            "Kit de Embreagem Luk Cambio Manual",
            "Kit de Embreagem Luk Cambio Manual Ref 62030847",
            "Kit de Embreagem Luk Cambio Manual Man Ref 62030847",
        ],
        required_tokens=("embreagem", "luk", "manual"),
        forbidden_terms=("man",),
        expect_reference_variant=True,
    )
    assert any("token proibido presente: man" in issue for issue in forbidden_issues)


def test_validate_title_set_accepts_diverse_identity_preserving_titles():
    issues = MODULE.validate_title_set(
        titles=[
            "Bomba de combustivel Bosch 12V flex",
            "Bomba de combustivel Bosch 12V Ref F000TE1773",
            "Bomba de combustivel Bosch 12V motores flex",
        ],
        required_tokens=("bomba", "bosch", "12v"),
        expect_reference_variant=True,
    )

    assert issues == []


def test_validate_title_set_allows_technical_linha_leve_variant():
    issues = MODULE.validate_title_set(
        titles=[
            "Jogo de Pastilhas de Freio TRW Dianteira",
            "Jogo de Pastilhas de Freio TRW Dianteira Ref GDB242",
            "Jogo de Pastilhas de Freio TRW Dianteira linha leve",
        ],
        required_tokens=("pastilhas", "freio", "trw", "dianteira"),
        expect_reference_variant=True,
    )

    assert issues == []


def test_compute_quality_score_and_summary_metrics():
    title_score = MODULE.compute_quality_score(
        issues=["falha 1", "falha 2"],
        penalty_per_issue=18,
    )
    description_score = MODULE.compute_quality_score(
        issues=["falha 1"],
        penalty_per_issue=12,
    )
    summary = MODULE.summarize_quality_scores(
        [
            {
                "id": "ok-case",
                "ok": True,
                "title_quality": {"score": 100},
                "description_quality": {"score": 88},
                "case_score": 94.0,
            },
            {
                "id": "bad-case",
                "ok": False,
                "title_quality": {"score": title_score},
                "description_quality": {"score": description_score},
                "case_score": 76.0,
            },
        ]
    )

    assert title_score == 64
    assert description_score == 88
    assert summary == {
        "total_cases": 2,
        "passed_cases": 1,
        "failed_cases": 1,
        "failed_case_ids": ["bad-case"],
        "title_score_avg": 82.0,
        "description_score_avg": 88.0,
        "case_score_avg": 85.0,
        "case_score_min": 76.0,
    }


def test_contains_suspicious_contact_number_ignores_reference_code_context():
    assert (
        MODULE.contains_suspicious_contact_number(
            "Modelo F000TE1773 referencia 0580454094 com pressao estavel."
        )
        is False
    )
    assert MODULE.contains_suspicious_contact_number("Ligue agora para 11 99999-0000.") is True
