# tdai_project/Backend/routers/web_enrichment.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import asyncio
import json

import crud
import models
import schemas
from database import get_db, SessionLocal

from .auth_utils import get_current_active_user

from services import web_data_extractor_service as web_extractor
from core.config import settings # Importar settings

router = APIRouter(
    prefix="/enriquecimento-web",
    tags=["Enriquecimento de Produto via Web"],
    dependencies=[Depends(get_current_active_user)]
)

async def _tarefa_enriquecer_produto_web(
    db_session_factory,
    produto_id: int,
    user_id: int,
    termos_busca_override: Optional[str] = None
):
    db: Session = db_session_factory()
    log_mensagens: List[str] = ["Iniciando tarefa de enriquecimento web..."]
    status_final = models.StatusEnriquecimentoEnum.FALHOU # Default
    db_produto_obj: Optional[models.Produto] = None
    dados_extraidos_agregados: Dict[str, Any] = {}
    
    try:
        user = crud.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuário ID {user_id} não encontrado. Tarefa abortada.")
            # (Opcional) Atualizar produto para falha se encontrado
            temp_produto = crud.get_produto(db, produto_id=produto_id)
            if temp_produto:
                crud.update_produto(db, db_produto=temp_produto, produto_update=schemas.ProdutoUpdate(
                    status_enriquecimento_web=models.StatusEnriquecimentoEnum.FALHOU,
                    log_enriquecimento_web={"historico_mensagens": log_mensagens, "erro_fatal": "Usuário não encontrado."}
                ))
            return

        db_produto_obj = crud.get_produto(db, produto_id=produto_id)
        if not db_produto_obj:
            log_mensagens.append(f"ERRO FATAL: Produto ID {produto_id} não encontrado. Tarefa abortada.")
            return

        dados_extraidos_agregados = db_produto_obj.dados_brutos.copy() if isinstance(db_produto_obj.dados_brutos, dict) else {}

        crud.update_produto(db, db_produto=db_produto_obj, produto_update=schemas.ProdutoUpdate(
            status_enriquecimento_web=models.StatusEnriquecimentoEnum.EM_PROGRESSO,
            log_enriquecimento_web={"historico_mensagens": log_mensagens} # Log inicial
        ))
        db.refresh(db_produto_obj)
        log_mensagens.append(f"Produto ID {produto_id} marcado como EM_PROGRESSO.")

        # VERIFICAÇÃO DE CHAVES API ESSENCIAIS PARA O PROCESSO
        google_api_configurada = bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_ID)
        openai_api_configurada = bool(user.chave_openai_pessoal or settings.OPENAI_API_KEY)

        # Se for depender criticamente da busca Google E ela não estiver configurada
        # OU se for depender da LLM para extração E OpenAI não estiver configurada
        # (Aqui, vamos assumir que a LLM é uma parte crucial se as URLs forem encontradas)

        if not google_api_configurada:
            log_mensagens.append("AVISO: Chaves Google CSE não configuradas. Busca no Google será pulada.")
        
        # Se a intenção é usar LLM em algum ponto e a chave não existe
        # (Vamos considerar que queremos usar LLM se encontrarmos URLs ou tivermos texto)
        # Esta verificação pode ser mais granular dentro do loop de URLs
        
        # --- Lógica de busca e processamento de URLs ---
        query_parts = [db_produto_obj.nome_base]
        # ... (resto da montagem da query como antes) ...
        if db_produto_obj.marca: query_parts.append(db_produto_obj.marca)
        if isinstance(db_produto_obj.dados_brutos, dict):
            codigo_original = db_produto_obj.dados_brutos.get("codigo_original") or db_produto_obj.dados_brutos.get("sku_original")
            if codigo_original: query_parts.append(str(codigo_original))
        query = termos_busca_override or (" ".join(query_parts) + " especificações técnicas detalhadas")
        log_mensagens.append(f"Termo de busca Google: '{query}'")

        urls_encontradas_brutas = []
        if google_api_configurada:
            urls_encontradas_brutas = await web_extractor.buscar_urls_google(query=query, num_results=3)
        else: # Se não há API do Google, não há URLs do Google
            log_mensagens.append("Busca Google pulada devido à falta de configuração de API.")

        # ... (lógica de priorização de URLs como antes) ...
        urls_priorizadas = []
        if db_produto_obj.fornecedor and db_produto_obj.fornecedor.site_url:
            try:
                site_fornecedor_str = str(db_produto_obj.fornecedor.site_url)
                site_fornecedor_domain = site_fornecedor_str.split("//")[-1].split("/")[0].lower()
                for url_g in urls_encontradas_brutas: # urls_encontradas_brutas pode estar vazia
                    if site_fornecedor_domain in url_g.lower():
                        urls_priorizadas.insert(0, url_g)
                    else:
                        urls_priorizadas.append(url_g)
            except Exception as e_url_forn:
                log_mensagens.append(f"AVISO: Erro ao processar URL do fornecedor para priorização: {e_url_forn}")
                urls_priorizadas = urls_encontradas_brutas # Mantém as brutas se a priorização falhar
        else:
            urls_priorizadas = urls_encontradas_brutas
        
        urls_a_processar = urls_priorizadas[:2]

        dados_coletados_nesta_tarefa = False # Flag para saber se algo útil foi coletado

        if not urls_a_processar:
            log_mensagens.append(f"Nenhuma URL relevante encontrada ou selecionada para '{query}'.")
            # Se não há URLs E não temos chave OpenAI para tentar extrair de dados brutos (se essa fosse uma lógica)
            # podemos definir o status aqui. Mas a LLM é chamada por URL.
            status_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            # Mesmo sem URLs, se a OpenAI não estiver configurada, e quisermos logar isso como falha de config:
            if not openai_api_configurada:
                log_mensagens.append("AVISO CRÍTICO: Chave OpenAI não configurada. Extração de dados com LLM não será possível.")
                status_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
                # Registra no histórico de uso IA a tentativa falha por config
                crud.create_uso_ia(db=db, uso_ia=schemas.UsoIACreate(
                    produto_id=produto_id,
                    tipo_geracao="enriquecimento_web_extracao_llm_config_faltante",
                    modelo_ia_usado="N/A",
                    resultado_gerado="Falha: Chave API OpenAI não configurada para extração de dados web.",
                    prompt_utilizado="N/A - Configuração API pendente"
                ), user_id=user.id)
        else: # Temos URLs para processar
            log_mensagens.append(f"URLs selecionadas para processamento: {urls_a_processar}")

            for url_idx, url in enumerate(urls_a_processar):
                log_mensagens.append(f"Processando URL ({url_idx+1}/{len(urls_a_processar)}): {url}")
                html_content = await web_extractor.coletar_conteudo_pagina_playwright(url)

                if not html_content:
                    log_mensagens.append(f"AVISO: Falha ao coletar HTML da URL: {url}")
                    continue

                metadados_brutos = web_extractor.extrair_metadados_estruturados(html_content, url=url)
                metadados_normalizados = {}
                if metadados_brutos:
                    log_mensagens.append(f"INFO: Metadados estruturados encontrados em {url}.")
                    metadados_normalizados = web_extractor._normalizar_dados_de_metadados(metadados_brutos)
                    dados_coletados_nesta_tarefa = True
                    for k_meta, v_meta in metadados_normalizados.items():
                        dados_extraidos_agregados[f"meta_{k_meta}"] = v_meta

                texto_pagina = web_extractor.extrair_texto_principal_com_trafilatura(html_content)
                resultado_extracao_llm_str = "LLM não utilizada (sem API Key ou conteúdo insuficiente)."
                modelo_ia_usado_extracao = "N/A"

                tentativa_llm_feita = False

                if openai_api_configurada:
                    if (texto_pagina and len(texto_pagina) >= 50) or metadados_normalizados:
                        log_mensagens.append(f"INFO: Tentando extração com LLM para {url}")
                        modelo_ia_usado_extracao = "openai_gpt-3.5-turbo" # Modelo usado para extração
                        tentativa_llm_feita = True

                        dados_da_pagina_llm = await web_extractor.extrair_dados_produto_com_llm(
                            # ... (argumentos como antes) ...
                            texto_pagina=texto_pagina,
                            metadados_normalizados=metadados_normalizados.copy(),
                            campos_desejados=[
                                "nome_completo_produto", "marca_identificada", "modelo_especifico", "sku_codigo",
                                "descricao_detalhada_paragrafos", "lista_caracteristicas_beneficios_bullets",
                                "especificacoes_tecnicas_dict", "categoria_sugerida_hierarquia",
                                "cor_principal", "material_predominante"
                            ],
                            produto_nome_base=db_produto_obj.nome_base,
                            user=user
                        )

                        if dados_da_pagina_llm and not dados_da_pagina_llm.get("erro_llm"):
                            dados_coletados_nesta_tarefa = True
                            log_mensagens.append(f"INFO: Dados extraídos com LLM de {url}.")
                            for k_llm, v_llm in dados_da_pagina_llm.items():
                                dados_extraidos_agregados[f"llm_{k_llm}"] = v_llm
                            resultado_extracao_llm_str = json.dumps(dados_da_pagina_llm)
                        elif dados_da_pagina_llm and dados_da_pagina_llm.get("erro_llm"):
                            log_mensagens.append(f"ERRO_LLM_EXTRACAO para URL {url}: {dados_da_pagina_llm['erro_llm']}")
                            resultado_extracao_llm_str = f"Falha na extração LLM: {dados_da_pagina_llm['erro_llm']}"
                            status_final = models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA # Falha da API
                        # ... (outros else ifs)
                    else:
                        log_mensagens.append(f"AVISO: Conteúdo textual insuficiente ou sem metadados claros em {url} para LLM.")
                else: # openai_api_configurada é False
                    log_mensagens.append(f"AVISO: Chave OpenAI não configurada. Extração LLM para {url} pulada.")
                    resultado_extracao_llm_str = "Falha: Chave API OpenAI não configurada para extração."
                    # Definir status aqui se a LLM era crucial e não pôde ser chamada por falta de config
                    status_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
                    tentativa_llm_feita = True # Consideramos uma tentativa, mesmo que falhe por config

                if tentativa_llm_feita: # Se tentamos usar LLM (ou falhou por config ou chamou a API)
                    crud.create_uso_ia(db=db, uso_ia=schemas.UsoIACreate(
                        produto_id=produto_id,
                        tipo_geracao=f"extracao_dados_web_openai_url",
                        modelo_ia_usado=modelo_ia_usado_extracao,
                        resultado_gerado=resultado_extracao_llm_str[:10000],
                        prompt_utilizado=f"Extração de dados da URL: {url} para produto: {db_produto_obj.nome_base}"
                    ), user_id=user.id)
                    log_mensagens.append(f"INFO: Tentativa de extração LLM para {url} registrada no histórico de uso da IA.")

                if url_idx < len(urls_a_processar) - 1: await asyncio.sleep(1)
            # Fim do loop de URLs

            if status_final not in [models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA, models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA]:
                if dados_coletados_nesta_tarefa:
                    status_final = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
                elif urls_a_processar: # Processou URLs mas nada significativo
                    status_final = models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
        # Fim do else (temos URLs)

        # Se o status_final ainda for o default FALHOU e não foi atualizado por um erro específico de config/API
        # mas NENHUMA_FONTE_ENCONTRADA foi setado, respeita NENHUMA_FONTE_ENCONTRADA.
        if status_final == models.StatusEnriquecimentoEnum.FALHOU and \
           models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA in [s.value for s in models.StatusEnriquecimentoEnum if s.name in str(log_mensagens)]: # heuristic
             pass # Mantém o status que foi setado antes (e.g. NENHUMA_FONTE_ENCONTRADA)


        produto_update_schema = schemas.ProdutoUpdate(
            dados_brutos=dados_extraidos_agregados,
            status_enriquecimento_web=status_final,
            log_enriquecimento_web={"historico_mensagens": log_mensagens}
        )
        crud.update_produto(db, db_produto=db_produto_obj, produto_update=produto_update_schema)
        log_mensagens.append(f"Produto ID {produto_id} atualizado com status final: {status_final.value}")

    except Exception as e:
        import traceback
        error_full = traceback.format_exc()
        log_mensagens.append(f"ERRO CRÍTICO NO PROCESSO: {str(e)}")
        # O status_final já é FALHOU por default, mas podemos adicionar mais detalhes
        print(f"ERRO CRÍTICO na tarefa de enriquecimento para produto ID {produto_id}: {error_full}")
        if db_produto_obj:
             crud.update_produto(db, db_produto=db_produto_obj, produto_update=schemas.ProdutoUpdate(
                status_enriquecimento_web=models.StatusEnriquecimentoEnum.FALHOU, # Garante que é FALHOU
                log_enriquecimento_web={"historico_mensagens": log_mensagens, "erro_fatal_traceback": error_full}
            ))
    finally:
        final_status_value = status_final.value if isinstance(status_final, models.StatusEnriquecimentoEnum) else str(status_final)
        print(f"Finalizando tarefa de enriquecimento para produto ID: {produto_id}. Status final: {final_status_value}")
        log_mensagens.append(f"Tarefa finalizada com status: {final_status_value}")
        # Assegura que o log final seja salvo, especialmente se um erro ocorreu após a última atualização do produto
        if db_produto_obj and db.is_active and not db.is_closed():
            try:
                current_log = db_produto_obj.log_enriquecimento_web or {}
                if isinstance(current_log, dict) and current_log.get("historico_mensagens") != log_mensagens:
                    crud.update_produto(db, db_produto=db_produto_obj, produto_update=schemas.ProdutoUpdate(
                        log_enriquecimento_web={"historico_mensagens": log_mensagens}
                    ))
            except Exception as e_final_log:
                print(f"ERRO ao tentar salvar log final para produto {produto_id}: {e_final_log}")
        db.close()


@router.post("/produto/{produto_id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Msg)
async def iniciar_enriquecimento_produto_web_endpoint(
    produto_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    termos_busca_override: Optional[str] = Query(None, description="Opcional: Termos de busca específicos para o Google Search."),
):
    db_temp = SessionLocal()
    try:
        db_produto_check = crud.get_produto(db_temp, produto_id=produto_id)
        if not db_produto_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
        if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a enriquecer este produto")
        if db_produto_check.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Processo de enriquecimento já está em andamento para este produto.")
    finally:
        db_temp.close()

    background_tasks.add_task(
        _tarefa_enriquecer_produto_web,
        db_session_factory=SessionLocal,
        produto_id=produto_id,
        user_id=current_user.id,
        termos_busca_override=termos_busca_override
    )
    return {"message": f"Processo de enriquecimento web para o produto ID {produto_id} iniciado em segundo plano."}