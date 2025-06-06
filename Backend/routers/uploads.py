from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional
import shutil
import os
from core.config import logger
from pathlib import Path
import imghdr # Para detectar o tipo MIME de imagem
import magic # Para detectar o tipo MIME de forma mais robusta (requer python-magic)

# --- IMPORTS ALTERADOS ---
from database import get_db
from auth import get_current_active_user
from models import User
from schemas import FileProcessResponse
from sqlalchemy.orm import Session
# --- FIM DOS IMPORTS ALTERADOS ---

router = APIRouter()

# O UPLOAD_DIRECTORY DEVE SER O MESMO MONTADO EM main.py /static
# E DEVE SER RELATIVO AO DIRETÓRIO RAIZ DO BACKEND
UPLOAD_DIRECTORY = Path("static") # Alterado para 'static' para corresponder a main.py e ser público

# Instalar python-magic: pip install python-magic (ou python-magic-bin no Windows se der problema)
# Se magic.from_buffer falhar, pode-se usar imghdr para imagens ou verificar extensões.
try:
    import magic
except ImportError:
    magic = None
    logger.warning(
        "python-magic não encontrado. A detecção de MIME type pode ser menos robusta."
    )


def get_file_mimetype(file_content: bytes, filename: str) -> str:
    """Tenta determinar o MIME type de um arquivo."""
    if magic:
        try:
            return magic.from_buffer(file_content, mime=True)
        except Exception:
            pass # Fallback para imghdr ou extensão se python-magic falhar

    # Fallback para imghdr para imagens
    img_type = imghdr.what(None, h=file_content)
    if img_type:
        return f"image/{img_type}"
    
    # Fallback básico para extensões de arquivo
    ext = Path(filename).suffix.lower()
    if ext == ".jpg" or ext == ".jpeg":
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".gif":
        return "image/gif"
    elif ext == ".webp":
        return "image/webp"
    elif ext == ".mp4":
        return "video/mp4"
    elif ext == ".webm":
        return "video/webm"
    elif ext == ".ogg":
        return "video/ogg"
    elif ext == ".pdf":
        return "application/pdf"
    elif ext == ".csv":
        return "text/csv"
    elif ext == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/octet-stream" # Tipo genérico para arquivos desconhecidos


@router.post("/upload-image-product/", response_model=FileProcessResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    file: UploadFile = File(..., description="Arquivo de imagem do produto a ser carregado."),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Carrega uma única imagem de produto e retorna sua URL pública e metadados.
    A imagem é salva no diretório 'static' e acessível via /static/.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome do arquivo não fornecido.")

    # Gerar um nome de arquivo único para evitar colisões
    # Ex: nome_original.jpg -> unique_id_nome_original.jpg
    file_extension = Path(file.filename).suffix
    unique_filename = f"{os.urandom(16).hex()}{file_extension}"
    file_location = UPLOAD_DIRECTORY / unique_filename

    # Garante que o diretório de upload existe
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

    file_content = await file.read() # Lê o conteúdo do arquivo
    
    # Tenta determinar o MIME type e o tamanho
    detected_mimetype = get_file_mimetype(file_content, file.filename)
    file_size = len(file_content)

    # Verifica se é um tipo de imagem aceitável (opcional, pode ser expandido)
    if not detected_mimetype.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Tipo de arquivo não suportado: {detected_mimetype}. Apenas imagens são permitidas.")

    try:
        with open(file_location, "wb") as f_out:
            f_out.write(file_content)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Não foi possível salvar o arquivo: {e}")
    finally:
        await file.close() # Garante que o UploadFile seja fechado

    # A URL pública será /static/nome_do_arquivo_unico.ext
    public_url = f"/static/{unique_filename}"
    
    # Retorna as informações necessárias para o frontend criar um ImageSchema
    return FileProcessResponse(
        filename=unique_filename,
        original_filename=file.filename, # Adiciona o nome original para referência
        url=public_url,
        message="Imagem do produto carregada com sucesso!",
        mimetype=detected_mimetype,
        size_bytes=file_size
    )

@router.post("/upload-video-product/", response_model=FileProcessResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_video(
    file: UploadFile = File(..., description="Arquivo de vídeo do produto a ser carregado."),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Carrega um único vídeo de produto e retorna sua URL pública e metadados.
    O vídeo é salvo no diretório 'static' e acessível via /static/.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome do arquivo não fornecido.")

    file_extension = Path(file.filename).suffix
    unique_filename = f"{os.urandom(16).hex()}{file_extension}"
    file_location = UPLOAD_DIRECTORY / unique_filename

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

    file_content = await file.read()
    
    detected_mimetype = get_file_mimetype(file_content, file.filename)
    file_size = len(file_content)

    if not detected_mimetype.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Tipo de arquivo não suportado: {detected_mimetype}. Apenas vídeos são permitidos.")

    try:
        with open(file_location, "wb") as f_out:
            f_out.write(file_content)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Não foi possível salvar o arquivo: {e}")
    finally:
        await file.close()

    public_url = f"/static/{unique_filename}"
    
    return FileProcessResponse(
        filename=unique_filename,
        original_filename=file.filename,
        url=public_url,
        message="Vídeo do produto carregado com sucesso!",
        mimetype=detected_mimetype,
        size_bytes=file_size
    )

# Endpoints de upload genéricos (mantidos, mas os acima são específicos para produto)
@router.post("/uploadfile/", status_code=status.HTTP_201_CREATED)
async def create_upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a single file. (Generic endpoint, not product-specific)
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome do arquivo não fornecido.")

    # Usa o nome original do arquivo ou um nome único se houver risco de colisão
    file_extension = Path(file.filename).suffix
    unique_filename = f"{os.urandom(16).hex()}{file_extension}" if file_extension else os.urandom(16).hex() # Gerar nome único também para genérico
    file_location = UPLOAD_DIRECTORY / unique_filename # Alterado para usar nome único
    
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not upload file: {e}")
    finally:
        file.file.close()
    # Retorna a URL pública usando o nome único gerado
    return {"info": f"file '{unique_filename}' (original: '{file.filename}') saved at '{file_location}'", "url": f"/static/{unique_filename}"}

@router.post("/uploadfiles/", status_code=status.HTTP_201_CREATED)
async def create_upload_files(
    files: List[UploadFile],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple files. (Generic endpoint, not product-specific)
    """
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    responses = []
    for file in files:
        if not file.filename:
            responses.append({"error": "Nome do arquivo não fornecido para um dos arquivos."})
            continue
        file_extension = Path(file.filename).suffix
        unique_filename = f"{os.urandom(16).hex()}{file_extension}" if file_extension else os.urandom(16).hex() # Gerar nome único também para genérico
        file_location = UPLOAD_DIRECTORY / unique_filename # Alterado para usar nome único
        try:
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            responses.append({"info": f"file '{unique_filename}' (original: '{file.filename}') saved at '{file_location}'", "url": f"/static/{unique_filename}"}) # Retorna URL pública
        except Exception as e:
            responses.append({"error": f"Could not upload file '{file.filename}': {e}"})
        finally:
            file.file.close()
    return responses
