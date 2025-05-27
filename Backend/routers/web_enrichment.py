# tdai_project/Backend/routers/web_enrichment.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import asyncio
import json # Mantido caso seja útil para logs futuros

# Imports de módulos no mesmo nível de Backend/ ou subpastas de Backend/
import crud #
import models #
import schemas #
from database import get_db, SessionLocal #

# Import de módulo no mesmo diretório (routers/)
from .auth_utils import get_current_active_user #

# CORREÇÃO APLICADA:
# 'services' é uma subpasta de 'Backend/'. Como o CWD é 'Backend/'
# e 'Backend/' está no sys.path, podemos importar 'services' diretamente.
from services import web_data_extractor_service as web_extractor #
# 'models' já foi importado acima, então usamos models.StatusEnriquecimentoEnum

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
    log_mensagens: List[str] = []
    status_final = models.StatusEnriquecimentoEnum.FALHOU
    dados_coletados_de_fontes_confiaveis = False
    
    db_produto_obj: Optional[models.Produto] = None

    try:
        user = crud.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuário ID {user_id} não encontrado na tarefa de fundo. Tarefa abortada.")
            print(log_mensagens[-1])
            return

        db_produto_obj = crud.get_produto(db, produto_id=produto_id)
        if not db_produto_obj:
            log_mensagens.append(f"ERRO FATAL: Produto ID {produto_id} não encontrado na tarefa de fundo. Tarefa abortada.")
            print(log_mensagens[-1])
            return

        log_inicial = {"mensagens": ["Iniciando processo de enriquecimento web..."]}
        crud.update_produto(db, db_produto=db_produto_obj, produto_update=schemas.ProdutoUpdate(
            status_enriquecimento_web=models.StatusEnriquecimentoEnum.EM_PROGRESSO,
            log_enriquecimento_web=log_inicial
        ))
        db.refresh(db_produto_obj)
        log_mensagens = log_inicial["mensagens"]

        log_mensagens.append(f"Iniciando enriquecimento para produto: '{db_produto_obj.nome_base}' (ID: {produto_id})")

        query_parts = [db_produto_obj.nome_base]
        if db_produto_obj.marca: query_parts.append(db_produto_obj.marca)
        if isinstance(db_produto_obj.dados_brutos, dict):
            codigo_original = db_produto_obj.dados_brutos.get("codigo_original") or db_produto_obj.dados_brutos.get("sku")
            if codigo_original: query_parts.append(str(codigo_original))
        
        query = termos_busca_override or (" ".join(query_parts) + " especificações técnicas detalhadas")
        log_mensagens.append(f"Termo de busca Google: '{query}'")

        urls_encontradas_brutas = await web_extractor.buscar_urls_google(query=query, num_results=3)
        
        urls_priorizadas = []
        if db_produto_obj.fornecedor and db_produto_obj.fornecedor.site_url:
            try:
                site_fornecedor_domain = db_produto_obj.fornecedor.site_url.split("//")[-1].split("/")[0].lower()
                for url_g in urls_encontradas_brutas:
                    if site_fornecedor_domain in url_g.lower():
                        urls_priorizadas.insert(0, url_g)
                    else:
                        urls_priorizadas.append(url_g)
            except Exception:
                urls_priorizadas = urls_encontradas_brutas
        else:
            urls_priorizadas = urls_encontradas_brutas
        
        urls_a_processar = urls_priorizadas[:2]

        if not urls_a_processar:
            log_mensagens.append(f"Nenhuma URL relevante encontrada ou selecionada (query: '{query}').")
            status_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
        else:
            log_mensagens.append(f"URLs selecionadas: {urls_a_processar}")
            
            dados_extraidos_agregados = db_produto_obj.dados_brutos.copy() if isinstance(db_produto_obj.dados_brutos, dict) else {}
            
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
                    dados_coletados_de_fontes_confiaveis = True
                    for k_meta, v_meta in metadados_normalizados.items():
                        dados_extraidos_agregados[f"meta_{k_meta}"] = v_meta
                
                texto_pagina = web_extractor.extrair_texto_principal_com_trafilatura(html_content)

                if (not texto_pagina or len(texto_pagina) < 50) and not metadados_normalizados:
                    log_mensagens.append(f"AVISO: Conteúdo insuficiente em {url}, pulando LLM.")
                    continue
                    
                dados_da_pagina_llm = await web_extractor.extrair_dados_produto_com_llm(
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
                    dados_coletados_de_fontes_confiaveis = True
                    for k_llm, v_llm in dados_da_pagina_llm.items():
                        dados_extraidos_agregados[f"llm_{k_llm}"] = v_llm
                elif dados_da_pagina_llm and dados_da_pagina_llm.get("erro_llm"):
                    log_mensagens.append(f"ERRO_LLM para URL {url}: {dados_da_pagina_llm['erro_llm']}")
                elif metadados_normalizados:
                     log_mensagens.append(f"INFO: LLM não retornou dados, usando apenas metadados normalizados de {url}")
                else:
                    log_mensagens.append(f"AVISO: Nenhum dado (metadados ou LLM) extraído de {url}")

                if url_idx < len(urls_a_processar) - 1: await asyncio.sleep(1)

            if dados_coletados_de_fontes_confiaveis:
                status_final = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
                log_mensagens.append(f"Produto ID {produto_id} atualizado com dados enriquecidos da web.")
            elif urls_a_processar:
                status_final = models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
                log_mensagens.append(f"Nenhum dado novo e significativo extraído da web para o produto ID {produto_id}.")
            
        dados_brutos_finais = db_produto_obj.dados_brutos.copy() if isinstance(db_produto_obj.dados_brutos, dict) else {}
        dados_brutos_finais.update(dados_extraidos_agregados)

        produto_update_schema = schemas.ProdutoUpdate(
            dados_brutos=dados_brutos_finais,
            status_enriquecimento_web=status_final,
            log_enriquecimento_web={"historico_mensagens": log_mensagens}
        )
        crud.update_produto(db, db_produto=db_produto_obj, produto_update=produto_update_schema)

    except Exception as e:
        import traceback
        error_full = traceback.format_exc()
        print(f"ERRO CRÍTICO na tarefa de enriquecimento para produto ID {produto_id}: {error_full}")
        log_mensagens.append(f"ERRO CRÍTICO NO PROCESSO: {str(e)}")
        status_final = models.StatusEnriquecimentoEnum.FALHOU
        if db_produto_obj:
             crud.update_produto(db, db_produto=db_produto_obj, produto_update=schemas.ProdutoUpdate(
                status_enriquecimento_web=status_final,
                log_enriquecimento_web={"historico_mensagens": log_mensagens, "erro_fatal": error_full}
            ))
    finally:
        print(f"Finalizando tarefa de enriquecimento para produto ID: {produto_id}. Status final: {status_final.value}")
        db.close()

@router.post("/produto/{produto_id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Msg)
async def iniciar_enriquecimento_produto_web_endpoint(
    produto_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    termos_busca_override: Optional[str] = Query(None, description="Opcional: Termos de busca específicos."),
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