# Backend/services/validator_crew.py
import os
import json
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from fastapi import HTTPException, status
import logging

from Backend.core.config import settings

logger = logging.getLogger(__name__)

class ProductDataValidatorCrew:
    """
    Uma crew de agentes de IA para validar, limpar e padronizar dados de produtos.
    """

    def __init__(self, raw_product_data: dict):
        self.raw_product_data = raw_product_data
        self.llm = self._setup_llm()

    def _setup_llm(self):
        if not settings.OPENAI_API_KEY:
            logger.error("A chave da API da OpenAI não foi configurada.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A chave da API para o serviço de validação não está configurada no servidor."
            )
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model_name="gpt-4-turbo-preview",
            temperature=0.1
        )

    def run(self) -> dict:
        """
        Executa a crew de validação.
        """
        auditor_agent = Agent(
            role='Auditor de Qualidade de Dados de E-commerce',
            goal="""Analisar meticulosamente os dados brutos de um produto, identificar e corrigir inconsistências,
            erros de OCR e problemas de formatação para garantir que os dados estejam prontos para um banco de dados de e-commerce.""",
            backstory="""Você é um assistente de IA especializado, treinado para ser o guardião da qualidade dos dados em catálogos de produtos.
            Com vasta experiência em lidar com dados vindos de fontes não estruturadas como PDFs e OCR, você é perito em detectar
            erros sutis, como a troca de 'O' por '0' ou 'l' por '1', padronizar formatos de preço e garantir a consistência lógica
            dos atributos de um produto. Seu trabalho é crucial para manter a integridade do catálogo.""",
            allow_delegation=False,
            verbose=True,
            llm=self.llm
        )

        validation_task = Task(
            description=f"""
            Analise o seguinte dicionário de dados brutos de um produto. Sua tarefa é limpar, padronizar e validar esses dados.

            Dados Brutos:
            ```json
            {json.dumps(self.raw_product_data, indent=2, ensure_ascii=False)}
            ```

            Instruções:
            1.  **Correção de OCR**: Verifique todos os campos, especialmente 'sku_original' e valores em 'dados_brutos_adicionais',
                em busca de erros comuns de OCR (ex: 'O'/'o' por '0', 'I'/'i'/'l' por '1', 'S'/'s' por '5'). Corrija-os.
            2.  **Padronização de Preços**: Se o campo 'preco_original' existir, converta-o para um número de ponto flutuante (float).
                Remova símbolos como 'R$', ',', etc. O formato de saída deve ser, por exemplo, 123.45.
            3.  **Consistência de Nomes**: Padronize o 'nome_base' para ter a primeira letra de cada palavra em maiúscula (Title Case),
                a menos que seja um acrônimo. Mantenha SKUs e códigos em maiúsculo.
            4.  **Estrutura de Saída**: Retorne um JSON ÚNICO contendo todos os campos do dicionário original, mas com os valores
                corrigidos e padronizados. Se um campo não precisou de alteração, retorne-o como estava. Mantenha a estrutura
                original do dicionário, incluindo `dados_brutos_adicionais`.

            Exemplo de Saída Esperada (para um produto diferente):
            {{
              "nome_base": "Parafuso Sextavado Rosca Inteira",
              "sku_original": "SKU-00123",
              "descricao_original": "parafuso de aco carbono com acabamento zincado",
              "preco_original": 1.50,
              "dados_brutos_adicionais": {{
                "diametro": "M6",
                "comprimento": "20mm"
              }}
            }}
            """,
            agent=auditor_agent,
            expected_output="Um único e válido objeto JSON contendo a versão limpa e padronizada dos dados do produto."
        )

        crew = Crew(
            agents=[auditor_agent],
            tasks=[validation_task],
            process=Process.sequential,
            verbose=2
        )

        result_str = crew.kickoff()

        try:
            # O LLM pode retornar o JSON dentro de um bloco de código markdown
            if result_str.strip().startswith("```json"):
                result_str = result_str.strip()[7:-4]
            
            cleaned_data = json.loads(result_str)
            return cleaned_data
        except json.JSONDecodeError:
            logger.error(f"Falha ao decodificar o JSON retornado pela Audit Crew. Resultado: {result_str}")
            # Em caso de falha, retorna os dados originais para não quebrar o pipeline
            return self.raw_product_data
        except Exception:
            logger.exception(f"Erro inesperado ao processar o resultado da Audit Crew.")
            return self.raw_product_data


def run_validation_crew(product_data: dict) -> dict:
    """
    Inicializa e executa a crew de validação para um único produto.
    """
    try:
        crew_instance = ProductDataValidatorCrew(raw_product_data=product_data)
        cleaned_data = crew_instance.run()
        return cleaned_data
    except HTTPException:
         # Repassa a exceção se a API key não estiver configurada
        raise
    except Exception as e:
        logger.error(f"Erro ao executar a Audit Crew: {e}")
        # Retorna os dados originais em caso de qualquer outro erro na execução da crew
        return product_data

if __name__ == '__main__':
    # Exemplo de como usar o serviço
    sample_data = {
        "nome_base": "parafuso sextavado rosca inteira",
        "sku_original": "SKU-O0123", # 'O' em vez de '0'
        "descricao_original": "parafuso de aco carbono com acabamento zincado",
        "preco_original": "R$ 1,5O", # 'O' em vez de '0'
        "dados_brutos_adicionais": {
            "diametro": "M6",
            "comprimento": "2Omm" # 'O' em vez de '0'
        }
    }

    print("\n--- Dados Brutos ---")
    print(json.dumps(sample_data, indent=2, ensure_ascii=False))

    validated_product = run_validation_crew(sample_data)
    
    print("\n--- Dados Validados ---")
    print(json.dumps(validated_product, indent=2, ensure_ascii=False))
