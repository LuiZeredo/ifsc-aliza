# TCC: Análise e Predição de Evasão em Sistemas de Informação
# Autor:Luiz André Zeredo
# Instituição: Instituto Federal de Santa Catarina (IFSC) — Câmpus Caçador
# Curso: Bacharelado em Sistemas de Informação

## Sobre o Projeto

# Este repositório armazena os códigos desenvolvidos para a qualificação do Trabalho de Conclusão de Curso (TCC). O objetivo central do trabalho é utilizar técnicas de Machine Learning para mitigar a evasão escolar no curso de Sistemas de Informação.

# O projeto é composto por dois módulos principais:

# 1.Extração e Tratamento de Dados (leitura_historicos.p):Script responsável pela leitura de históricos escolares em formato PDF. O código extrai indicadores de desempenho acadêmico mantendo a total anonimização dos indivíduos, em conformidade com as diretrizes da Lei Geral de Proteção de Dados (LGPD).
# 2.Modelo Preditivo (Machine Learning): Algoritmo de aprendizado de máquina desenvolvido para reconhecer padrões comportamentais e acadêmicos associados à desistência. O sistema visa prever quais alunos apresentam alto risco de evasão, fornecendo subsídios para ações de retenção.

## Pré-requisitos e Execução

# Para a correta execução dos códigos, certifique-se de possuir:

# Fonte de Dados: Uma pasta contendo os históricos escolares dos alunos (arquivos PDF).
# Dataset Processado: O arquivo .xlsx resultante da compilação dos históricos (necessário para alimentar o modelo de Machine Learning).

## Tecnologias e Bibliotecas

# O projeto foi desenvolvido em Python, utilizando bibliotecas específicas para análise de dados não estruturados e estruturados:

# pdfplumber: Escolhida por sua robustez na leitura de arquivos PDF. A biblioteca processa o documento como texto corrido e, através de regras e parâmetros definidos no código, extrai apenas as informações pertinentes à pesquisa.
# pandas: Utilizada para a manipulação, limpeza e análise estatística dos dados extraídos, permitindo a criação dos datasets utilizados no treinamento do modelo.


# Este projeto foi desenvolvido para fins acadêmicos.