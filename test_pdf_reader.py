# test_pdf_reader.py
import fitz # PyMuPDF
import os

# Coloque o PDF problemático na mesma pasta deste script
pdf_path = "CATALOGO GERAL 38.pdf" 

try:
    print(f"Tentando abrir o arquivo: {pdf_path}")
    if not os.path.exists(pdf_path):
        print("ERRO: Arquivo não encontrado!")
    else:
        # Tenta abrir o documento
        doc = fitz.open(pdf_path)
        print(f"Arquivo aberto com sucesso! Número de páginas: {doc.page_count}")

        # Tenta renderizar a primeira página
        page = doc.load_page(0)
        pix = page.get_pixmap()
        pix.save("output_page_0.png")
        print("Primeira página convertida para imagem com sucesso!")
        doc.close()

except Exception as e:
    print("!!!!!!!!!! OCORREU UM ERRO !!!!!!!!!!!")
    print(f"Tipo de exceção: {type(e).__name__}")
    print(f"Mensagem de erro: {e}")
    # Se você quiser o traceback completo:
    import traceback
    traceback.print_exc()