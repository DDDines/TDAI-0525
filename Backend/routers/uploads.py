# tdai_project/Backend/routers/uploads.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

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
from services import file_processing_service #

router = APIRouter(
    prefix="/upload",
    tags=["Upload e Processamento de Arquivos"],
    dependencies=[Depends(get_current_active_user)]
)

# Constantes para configuração de upload
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel", # .xlsx
    "application/vnd.ms-excel": "excel", # .xls
    "text/csv": "csv",
    "application/csv": "csv",
    "text/plain": "csv",
    "application/pdf": "pdf",
}

@router.post("/produtos-arquivo/", response_model=schemas.FileProcessResponse)
async def upload_arquivo_produtos(
    arquivo: UploadFile = File(..., description=f"Arquivo PDF, Excel (xlsx, xls) ou CSV contendo dados de produtos. Limite: {MAX_FILE_SIZE_MB}MB."),
    fornecedor_id: Optional[int] = Form(None, description="ID do fornecedor para associar os produtos extraídos (opcional)."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if not arquivo.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome do arquivo não fornecido.")

    if arquivo.size is not None and arquivo.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo '{arquivo.filename}' muito grande. Limite de {MAX_FILE_SIZE_MB}MB."
        )

    file_type = ALLOWED_CONTENT_TYPES.get(arquivo.content_type or "")
    if not file_type:
        filename_lower = arquivo.filename.lower()
        if filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
            file_type = "excel"
        elif filename_lower.endswith(".csv"):
            file_type = "csv"
        elif filename_lower.endswith(".pdf"):
            file_type = "pdf"
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Tipo de arquivo '{arquivo.content_type}' ou extensão do arquivo '{arquivo.filename}' não suportado. Permitidos: PDF, Excel (xlsx, xls), CSV."
            )

    db_fornecedor = None
    if fornecedor_id is not None:
        db_fornecedor = crud.get_fornecedor(db, fornecedor_id=fornecedor_id)
        if not db_fornecedor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fornecedor com id {fornecedor_id} não encontrado.")
        if db_fornecedor.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Não autorizado a associar produtos ao fornecedor com id {fornecedor_id}.")

    conteudo_arquivo = await arquivo.read()
    await arquivo.close()

    produtos_extraidos_raw: List[Dict[str, Any]] = []
    process_detail = schemas.FileProcessDetail(
        filename=arquivo.filename,
        content_type=arquivo.content_type or "application/octet-stream",
        status="processando",
    )

    try:
        if file_type == "excel":
            produtos_extraidos_raw = await file_processing_service.processar_arquivo_excel(conteudo_arquivo)
        elif file_type == "csv":
            produtos_extraidos_raw = await file_processing_service.processar_arquivo_csv(conteudo_arquivo)
        elif file_type == "pdf":
            produtos_extraidos_raw = await file_processing_service.processar_arquivo_pdf(conteudo_arquivo)
        
        if not produtos_extraidos_raw or (len(produtos_extraidos_raw) == 1 and "erro" in produtos_extraidos_raw[0]):
            process_detail.status = "erro_ao_ler"
            process_detail.mensagem = produtos_extraidos_raw[0].get("erro", "Nenhum dado de produto válido encontrado ou erro na leitura do arquivo.") if produtos_extraidos_raw else "Nenhum dado de produto válido encontrado no arquivo."
            return schemas.FileProcessResponse(message="Erro ao processar o arquivo.", details=[process_detail])

        produtos_salvos_count = 0
        
        for produto_data_raw in produtos_extraidos_raw:
            if not isinstance(produto_data_raw, dict):
                print(f"Item extraído não é um dicionário: {produto_data_raw}")
                continue
            if "erro" in produto_data_raw:
                print(f"Erro individual ao processar linha/item: {produto_data_raw['erro']}")
                continue
            if not produto_data_raw.get("nome_base"):
                print(f"Produto pulado por falta de 'nome_base': {produto_data_raw}")
                continue
            
            dados_brutos_para_schema = produto_data_raw.get("dados_brutos_adicionais") or \
                                     produto_data_raw.get("dados_brutos_originais") or \
                                     {k: v for k, v in produto_data_raw.items() if k not in ['nome_base', 'marca', 'categoria_original']}


            produto_schema_create = schemas.ProdutoCreate(
                nome_base=str(produto_data_raw.get("nome_base","Nome Padrão")),
                marca=str(produto_data_raw.get("marca")) if produto_data_raw.get("marca") else None,
                categoria_original=str(produto_data_raw.get("categoria_original")) if produto_data_raw.get("categoria_original") else None,
                dados_brutos=dados_brutos_para_schema,
                fornecedor_id=db_fornecedor.id if db_fornecedor else None
            )
            crud.create_produto(db=db, produto=produto_schema_create, user_id=current_user.id)
            produtos_salvos_count += 1

        if produtos_salvos_count > 0:
            process_detail.status = "sucesso"
            process_detail.produtos_encontrados = produtos_salvos_count
            process_detail.mensagem = f"{produtos_salvos_count} produto(s) processado(s) e salvo(s) com sucesso do arquivo '{arquivo.filename}'."
        else:
            process_detail.status = "nenhum_produto_valido_encontrado"
            process_detail.mensagem = f"Nenhum produto válido foi encontrado ou salvo do arquivo '{arquivo.filename}'."
        
        return schemas.FileProcessResponse(message="Processamento do arquivo concluído.", details=[process_detail])

    except Exception as e:
        import traceback
        print(f"Erro crítico durante o processamento do arquivo '{arquivo.filename}': {str(e)}\n{traceback.format_exc()}")
        process_detail.status = "erro_critico_no_servidor"
        process_detail.mensagem = f"Erro interno no servidor ao processar o arquivo. Por favor, tente novamente mais tarde ou contate o suporte."
        
        detail_dict = process_detail.model_dump() if hasattr(process_detail, 'model_dump') else process_detail.dict()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail_dict)