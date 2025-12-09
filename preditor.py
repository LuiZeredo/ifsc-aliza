import os
import re
import pdfplumber 
import pandas as pd
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# --- Configs Iniciais ---
# Caminho da pasta que contém os PDFs
PASTA_PDFS = r'C:'

ARQUIVO_SAIDA_EXCEL = 'dados_extrator_tcc.xlsx'
ARQUIVO_LOG = 'processamento_tcc.log'

# --- Configuração do Log ---
logging.basicConfig(
    filename=ARQUIVO_LOG,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# --- REGRAS DE EXTRAÇÃO (REGEX) ---
# Regras otimizadas para o layout dos históricos do IFSC
REGEX_DADOS = {
    'Matricula': r'Matrícula\s+(\d+)',
    'Status': r'Status:\s+([A-Z ]+?)\s+',
    'CAA': r'\*CAA:\s+([0-9.]+)',
    'Cidade_Nascimento': r'Local de Nascimento:\s+([A-ZÁÉÍÓÚÇÃÕ ]+?)\s+UF:',
    'UF_Nascimento': r'UF:\s+([A-Z]{2})',
    'Nacionalidade': r'Nacionalidade:\s+([A-ZÁÉÍÓÚÇÃÕ ]+?)\s+',
    'Data_Nascimento': r'Data de Nascimento:\s+(\d{2}/\d{2}/\d{4})',
    'Qtd_Trancamentos': r'Trancamentos:\s+(\w+)',
    'Periodo_Letivo_Atual': r'Período Letivo Atual:\s+(\d+)'
}

# Regex p/ tabela: Captura (Semestre, Num1, Num2, Situação)
REGEX_DISCIPLINAS = re.compile(
    r'(\d{4}\.\d)\s+.*?\s+([\d.,]+)\s+([\d.,]+)\s+(APROVADO|REPROVADO|REP\. FALTA)',
    re.IGNORECASE | re.DOTALL
)

def extrair_texto_pdf(caminho_pdf):
    """Extrai texto do PDF de forma limpa usando pdfplumber."""
    texto_completo = ""
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages:
                texto_completo += page.extract_text() + "\n"
        return texto_completo
    except Exception as e:
        logging.error(f"Erro ao ler o PDF: {caminho_pdf} -> {e}")
        return None

def extrair_dado(texto, regra, padrao_nao_encontrado='N/A'):
    """Busca um único dado no texto usando Regex."""
    match = re.search(regra, texto)
    if match:
        return match.group(1).strip()
    return padrao_nao_encontrado

def calcular_idade(data_nasc_str):
    """Calcula idade a partir da data de nascimento (dd/mm/aaaa)."""
    try:
        data_nasc = datetime.strptime(data_nasc_str, '%d/%m/%Y')
        hoje = datetime.now()
        # Cálculo preciso
        idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
        return idade
    except:
        return 'N/A'

def _calcular_metricas_semestre(lista_disciplinas):
    """(Func Auxiliar) Calcula médias e contagens para um semestre."""
    total_notas, total_freq, aprovadas, reprovadas = 0, 0, 0, 0
    
    if not lista_disciplinas:
        return {'media_nota': 0, 'media_freq': 0, 'aprovadas': 0, 'reprovadas': 0}

    for d in lista_disciplinas:
        total_notas += d['nota']
        total_freq += d['freq']
        if d['status'] == 'APROVADO':
            aprovadas += 1
        elif d['status'].startswith('REP'):
            reprovadas += 1
            
    count = len(lista_disciplinas)
    
    return {
        'media_nota': round(total_notas / count, 2) if count > 0 else 0,
        'media_freq': round(total_freq / count, 2) if count > 0 else 0,
        'aprovadas': aprovadas,
        'reprovadas': reprovadas
    }

def calcular_metricas_recentes(disciplinas):
    """Calcula métricas separadas para o último, penúltimo e antepenúltimo semestre."""
    
    metricas_finais = {}
    semestres_unicos = sorted(list(disciplinas.keys()))
    
    for i, nome_sem in enumerate(['Ultimo', 'Penultimo', 'Antepenultimo']):
        if len(semestres_unicos) >= (i + 1):
            sem_chave = semestres_unicos[-(i + 1)]
            metricas = _calcular_metricas_semestre(disciplinas[sem_chave])
        else:
            metricas = _calcular_metricas_semestre([]) # Semestre vazio = zeros
        
        metricas_finais.update({
            f'Media_Nota_{nome_sem}_Sem': metricas['media_nota'],
            f'Media_Freq_{nome_sem}_Sem': metricas['media_freq'],
            f'Aprov_{nome_sem}_Sem': metricas['aprovadas'],
            f'Reprov_{nome_sem}_Sem': metricas['reprovadas']
        })
    return metricas_finais

def processar_historico_pdf(caminho_pdf):
    """Extrai todos os dados de UM histórico."""
    
    texto_pdf = extrair_texto_pdf(caminho_pdf)
    if not texto_pdf:
        return None

    # 1. Extrai dados estáticos
    dados_aluno = {}
    for chave, regra in REGEX_DADOS.items():
        dados_aluno[chave] = extrair_dado(texto_pdf, regra)

    # Calcula Idade
    dados_aluno['Idade'] = calcular_idade(dados_aluno.get('Data_Nascimento', 'N/A'))
    
    # 2. Extrai dados das disciplinas (tabela)
    disciplinas_por_semestre = defaultdict(list)
    matches = REGEX_DISCIPLINAS.findall(texto_pdf)
    
    for match in matches:
        try:
            semestre = match[0]
            # Converte números capturados, lidando com vírgula (,)
            num1, num2 = float(match[1].replace(',', '.')), float(match[2].replace(',', '.'))
            
            # Lógica de separação: Nota <= 10.0, Frequência > 10.0
            if num1 <= 10.0 and num2 > 10.0:
                nota, freq = num1, num2
            elif num2 <= 10.0 and num1 > 10.0:
                nota, freq = num2, num1
            elif num1 >= 70.0 and num2 <= 10.0: # Fallback p/ (7.0 e 80.0)
                freq, nota = num1, num2
            elif num2 >= 70.0 and num1 <= 10.0:
                freq, nota = num2, num1
            else:
                logging.warning(f"Não deu p/ determinar nota/freq (ambiguidade) em {caminho_pdf.name}")
                continue
            
            disciplinas_por_semestre[semestre].append({
                'freq': freq, 'nota': nota, 'status': match[3].upper()
            })
        except Exception as e:
            logging.warning(f"Erro ao processar linha disciplina em {caminho_pdf.name}: {e}")

    # 3. Calcula métricas recentes
    metricas_recentes = calcular_metricas_recentes(disciplinas_por_semestre)
    dados_aluno.update(metricas_recentes)
    
    return dados_aluno

def main():
    """Lê todos os PDFs e salva os dados no Excel."""
    
    pasta = Path(PASTA_PDFS)
    if not pasta.is_dir():
        logging.critical(f"Pasta de PDFs não encontrada: {PASTA_PDFS}")
        return

    logging.info(f"--- INÍCIO DA EXTRAÇÃO (TCC) ---")
    todos_os_dados = []

    # Ordem das colunas para o Excel final
    colunas_excel = [
        'Matricula', 'Status', 'CAA', 'Nacionalidade', 'Cidade_Nascimento', 'UF_Nascimento',
        'Idade', 'Periodo_Letivo_Atual', 'Qtd_Trancamentos', 'Ano_Periodo_Conclusao',
        'Media_Nota_Ultimo_Sem', 'Media_Freq_Ultimo_Sem', 'Aprov_Ultimo_Sem', 'Reprov_Ultimo_Sem',
        'Media_Nota_Penultimo_Sem', 'Media_Freq_Penultimo_Sem', 'Aprov_Penultimo_Sem', 'Reprov_Penultimo_Sem',
        'Media_Nota_Antepenultimo_Sem', 'Media_Freq_Antepenultimo_Sem', 'Aprov_Antepenultimo_Sem', 'Reprov_Antepenultimo_Sem',
        'Arquivo_Origem' 
    ]

    arquivos_pdf = list(pasta.glob('*.pdf'))
    
    if not arquivos_pdf:
        logging.warning(f"Nenhum PDF encontrado em {PASTA_PDFS}")
        return

    for caminho_pdf in arquivos_pdf:
        dados_aluno = processar_historico_pdf(caminho_pdf)
        
        if dados_aluno:
            dados_aluno['Arquivo_Origem'] = caminho_pdf.name
            todos_os_dados.append(dados_aluno)
            logging.info(f"Sucesso ao processar {caminho_pdf.name} (Matrícula: {dados_aluno.get('Matricula')})")
        else:
            logging.warning(f"Falha ao extrair dados de {caminho_pdf.name}")
                
    # 3. Salva no Excel usando pandas
    if not todos_os_dados:
        logging.warning("Processamento concluído, mas nenhum dado foi extraído.")
        return

    try:
        df = pd.DataFrame(todos_os_dados)
        
        # Filtra e reordena colunas
        df_final = pd.DataFrame(columns=colunas_excel)
        df_final = pd.concat([df_final, df[df.columns.intersection(colunas_excel)]], ignore_index=True)
        df_final = df_final.reindex(columns=colunas_excel, fill_value='N/A')

        df_final.to_excel(ARQUIVO_SAIDA_EXCEL, index=False, engine='openpyxl')
        logging.info(f"Sucesso! {len(todos_os_dados)} históricos salvos em '{ARQUIVO_SAIDA_EXCEL}'.")
        
    except Exception as e:
        logging.error(f"Erro ao salvar arquivo Excel: {e}")

    logging.info("--- FIM DA EXTRAÇÃO ---")

if __name__ == "__main__":
    main()
