# 🏦 Esteira de Conciliação Bancária Multibancária

### Projeto de portfólio: integração de dados, SQL, Python e ETL para conciliação financeira (dados sintéticos)

[![CI](https://github.com/diaquinodev/conciliacao-bancaria-automacao/actions/workflows/ci.yml/badge.svg)](https://github.com/diaquinodev/conciliacao-bancaria-automacao/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](requirements.txt)
[![Testes](https://img.shields.io/badge/testes-30%20automatizados-brightgreen?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![SQL](https://img.shields.io/badge/SQL-T--SQL%20%7C%20SQLite-CC2927?logo=microsoftsqlserver&logoColor=white)](src/conciliacao_bancaria.sql)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)](LICENSE)

**Autor:** Diego Aquino · [LinkedIn](https://linkedin.com/in/diegoaquino87) · [GitHub](https://github.com/diaquinodev)

> **Sobre este projeto:** é um **projeto de portfólio**, com **dados sintéticos** (gerados pelo próprio código) e **sem bancos reais**: não há integração com nenhuma instituição financeira, credencial ou dado de cliente. Os nomes de bancos são apenas ilustrativos. O cenário descrito abaixo é hipotético, e o projeto **não promete nem afirma resultado financeiro** (retorno, economia ou ganho de tempo medido em operação real).

**Stack:** Python (pandas, requests) · SQL (T-SQL como modelo; SQLite na demonstração) · ETL (Power Query / M) · painel HTML (Chart.js) · GitHub Actions (CI)

---

## 📌 O cenário (hipotético)

Uma área financeira com **8 contas bancárias** (BB, Bradesco, Itaú, Santander, Caixa, HSBC, Sicredi e Inter) precisa consolidar extratos de formatos diferentes:

| Dor típica | O que o projeto faz |
| :--- | :--- |
| Extratos em formatos e horários distintos | Extrator com autenticação OAuth 2.0 (modo demo sintético), schema validado |
| Retentativas de carga que duplicam lançamentos | Chave idempotente SHA-256 e `UNIQUE(ID_EXTERNO, BANCO, CONTA)` |
| Divergências que só aparecem no fechamento | Regras de duplicata, outlier e teto de alçada, com diagnóstico |
| Falta de visão consolidada | Painel HTML com filtros e relatório por e-mail (opcional) |

**Objetivo técnico:** demonstrar uma esteira diária de ponta a ponta (extração → transformação → SQL → análise → entrega) com qualidade de dados e idempotência.

## 💡 A solução

```mermaid
flowchart LR
    A["8 APIs bancárias<br/>(OAuth 2.0 / REST)"] --> B["Extrator Python<br/>Circuit Breaker + Backoff"]
    P["APIs públicas<br/>Câmbio · BACEN Selic"] --> B
    R["Internet banking legado<br/>(Power Automate Desktop)"] -.->|OFX / CNAB| C
    B --> C["Power Query (M)<br/>limpeza · tipagem · categoria"]
    C --> D[("SQL Server<br/>chave idempotente<br/>SP de discrepâncias")]
    D --> E["Motor de análise<br/>Claude API / heurístico"]
    D --> F["Painel executivo<br/>(Power BI / HTML)"]
    E --> G["Power Automate Cloud<br/>e-mail · Teams"]
```

| Camada | Arquivo | O que faz |
| :--- | :--- | :--- |
| **Extração** | [`src/extrator_bancario.py`](src/extrator_bancario.py) | OAuth 2.0 por banco, *Circuit Breaker* (CLOSED → OPEN → HALF_OPEN), *exponential backoff* com jitter para 429/5xx, validação de schema e logs JSON com `correlation_id`. Sem credenciais, opera em **modo demo** com massa sintética realista. |
| **Transformação (ETL)** | [`src/etl_power_query.m`](src/etl_power_query.m) | `Table.Buffer`, deduplicação pela mesma chave do SQL, tipagem monetária, categoria de despesa e sinal contábil (débito negativo). |
| **Persistência** | [`conciliacao_bancaria.sql`](src/conciliacao_bancaria.sql) | Tabelas com `DECIMAL(15,2)` e `UNIQUE(ID_EXTERNO, BANCO, CONTA)`, views para o BI, trilha de auditoria e a *stored procedure* `SP_DETECTAR_DISCREPANCIAS`. |
| **Inteligência** | [`src/claude_integration.py`](src/claude_integration.py) | Envia apenas as discrepâncias (não o extrato inteiro) à Claude API e devolve causa provável, risco e ação. Sem `ANTHROPIC_API_KEY`, usa um motor heurístico determinístico. |
| **Orquestração (desenho)** | [`flow.json`](docs/flow.json) · [RPA](docs/08_POWER_AUTOMATE_DESKTOP_RPA.md) | Desenho de um fluxo diário no Power Automate (padrão assíncrono *202 Accepted*, alerta e Teams); robô desktop para bancos sem API. Documentado como modelo alvo, não executado neste repositório. |
| **Entrega** | [`src/gerar_dashboard_interativo.py`](src/gerar_dashboard_interativo.py) · [`src/enviar_email_real.py`](src/enviar_email_real.py) | Painel HTML com filtros e relatório executivo por e-mail (SMTP/TLS, opcional) com câmbio e Selic ao vivo. |

## 📏 Regras de negócio implementadas

| Regra | Onde | Comportamento |
| :--- | :--- | :--- |
| **Teto de alçada** | SQL · IA · painel · e-mail | Lançamento acima de **R$ 100.000,00** vira discrepância, risco **Alto** e exige aprovação do CFO — inclusive se também for duplicata. |
| **Idempotência** | [`src/executar_esteira_ao_vivo.py`](src/executar_esteira_ao_vivo.py) | SHA-256 de `banco \| conta \| data \| valor(2 casas) \| descrição normalizada`. Reprocessar o mesmo lote **não duplica saldo**. |
| **Duplicata potencial** | `SP_DETECTAR_DISCREPANCIAS` | Mesmo banco, conta, valor e dia. Mantém as duas marcações quando a duplicata também estoura o teto. |
| **Outlier estatístico** | `SP_DETECTAR_DISCREPANCIAS` | Valor acima de média + 2σ dos últimos 90 dias (mínimo de 10 amostras por banco). |
| **Qualidade de dados** | `ExtratorBancario.validar_dados` | Mede a taxa de erro do lote: campos obrigatórios nulos, valor ≤ 0 e banco fora dos 8 suportados. |
| **Resiliência** | `CircuitBreaker` | 3 falhas seguidas abrem o circuito do banco por 30 s; os outros 7 bancos seguem normalmente. |

## 🖥️ Demonstração (dados sintéticos)

### Painel — visão geral dos 8 bancos
KPIs, "no que foi gasto" (categoria) e "onde foi gasto" (banco). O selo no topo aponta os lançamentos acima do teto.

![Painel](docs/img/01_dashboard_visao_geral.png)

### Filtros dinâmicos — Itaú + Passagens Aéreas
KPIs, gráficos e extrato recalculam no navegador.

![Filtro por banco e categoria](docs/img/02_dashboard_filtro_banco_categoria.png)

### Busca por fornecedor — discrepâncias acima do teto de alçada
![Discrepâncias](docs/img/03_dashboard_busca_discrepancias.png)

<details>
<summary><b>Execução no terminal: idempotência e regras SQL (clique para expandir)</b></summary>

#### Idempotência: reprocessar o lote ignora as 216 transações já gravadas
![Idempotência e APIs públicas](docs/img/05_esteira_idempotencia_apis.png)

#### Regras de auditoria no banco relacional
![SQL](docs/img/06_sql_regras_auditoria.png)

</details>

## 📚 Documentação

O dossiê técnico está em [`docs/`](docs/README.md):

| Documento | Conteúdo |
| :--- | :--- |
| [Índice do dossiê](docs/README.md) | Visão geral e lista de todos os documentos |
| [Arquitetura](docs/02_ARQUITETURA_DESIGN.md) | Desenho da solução e decisões |
| [Código Python](docs/03_CODIGO_PYTHON.md) · [Power Automate](docs/04_POWER_AUTOMATE.md) · [IA](docs/05_INTELIGENCIA_IA.md) · [BI e logs](docs/06_BI_LOGS.md) | Camadas da esteira |
| [Harness final](docs/07_HARNESS_FINAL.md) · [RPA desktop](docs/08_POWER_AUTOMATE_DESKTOP_RPA.md) | Validação ponta a ponta e contingência |
| [Contexto de negócio](docs/09_ALINHAMENTO_NEGOCIO.md) · [Engenharia de dados](docs/10_DOCUMENTACAO_ENGENHARIA_DADOS.md) | Contexto qualitativo e decisões (ADRs) |
| [Caso completo](docs/00_CASE_COMPLETO.md) · [Resumo](docs/RESUMO_EXECUTIVO.md) · [Roteiro de demonstração](docs/GUIA_APRESENTACAO.md) | Material de apoio |

## 🚀 Como executar

Pré-requisito: Python 3.12+.

```bash
git clone https://github.com/diaquinodev/conciliacao-bancaria-automacao.git && cd conciliacao-bancaria-automacao
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                               # opcional: sem ele tudo roda em modo demo
```

| Comando | O que mostra |
| :--- | :--- |
| `python src/demo_executiva.py` | Extração dos 8 bancos → regras → diagnóstico de risco (≈3 s) |
| `python src/executar_esteira_ao_vivo.py` | SQLite idempotente + câmbio/Selic ao vivo + painel; envia e-mail somente se `SMTP_EMAIL` e `SMTP_PASSWORD` estiverem no `.env` |
| `python src/executar_sql_demo.py` | Cria o banco local e executa as queries de auditoria |
| `python src/gerar_dashboard_interativo.py` | Regenera `dashboard_demonstracao.html` a partir de `transacoes_brutas.json` |

> `demo_executiva.py` gera uma nova massa sintética a cada execução e sobrescreve `transacoes_brutas.json`. Para voltar à massa de referência dos testes e prints: `git checkout transacoes_brutas.json transacoes_brutas.csv`.

## 🧪 Testes

```bash
python -m unittest tests/test_extrator_bancario.py -v
python tests/test_dashboard_integridade.py
python tests/test_gargalos_resiliencia.py
python tests/test_regras_negocio.py
```

| Suíte | Testes | Cobre |
| :--- | :---: | :--- |
| `tests/test_extrator_bancario.py` | 7 | Circuit Breaker, 8 bancos, schema, validação |
| `tests/test_dashboard_integridade.py` | 13 | Totais, categorias, paginação e dados embutidos no painel |
| `tests/test_gargalos_resiliencia.py` | 4 | Idempotência, rate limit, armadilhas de negócio (hotelaria/aéreo) e equilíbrio contábil |
| `tests/test_regras_negocio.py` | 6 | Precedência do teto de alçada, hash normalizado, XSS no painel, e-mail com dados reais |

Todas rodam no [GitHub Actions](.github/workflows/ci.yml) em Python 3.12 e 3.13.

## 🔐 Segurança

- **Nenhum segredo no repositório.** Credenciais (OAuth dos bancos, SMTP, Anthropic) vêm só do `.env`, ignorado pelo Git; o [`.env.example`](.env.example) documenta as variáveis.
- **SMTP opcional:** remetente (`SMTP_EMAIL`) e senha de app (`SMTP_PASSWORD`) vêm só do `.env`, sem valor padrão no código; use senha de app, nunca a senha da conta (`STARTTLS`, porta 587).
- **Sem vazamento em log:** respostas de erro do OAuth não são registradas (podem ecoar credenciais).
- **Painel protegido contra XSS:** descrições vindas dos bancos são escapadas antes de ir para o HTML, e o JSON embutido não consegue fechar a tag `<script>`.
- **Menor exposição à IA:** só as discrepâncias vão para a API; o extrato completo não sai do ambiente.
- **Trilha de auditoria** (`TB_AUDITORIA_CONCILIACAO`) com `correlation_id` por execução.

## ⚖️ Decisões técnicas e limitações conhecidas

- **Modo demo por padrão.** Sem credenciais bancárias reais, o extrator gera transações sintéticas realistas (passagens, hotéis, transfers, seguros e um fretamento acima do teto de vez em quando). O caminho REST real está implementado e é ativado quando os `*_CLIENT_ID`/`*_CLIENT_SECRET` existem no `.env`.
- **SQLite na demo, SQL Server no desenho alvo.** Os scripts locais usam SQLite para rodar sem infraestrutura; o [`conciliacao_bancaria.sql`](src/conciliacao_bancaria.sql) é o modelo T-SQL de produção (com `DECIMAL` para valores monetários).
- **Chave idempotente por conteúdo.** Duas compras legítimas idênticas (mesmo banco, conta, segundo, valor e descrição) seriam tratadas como uma só. Com as APIs reais, a chave deve priorizar o identificador único do banco (`id_externo`).
- **Extração sequencial.** Os 8 bancos são consultados em sequência. Para escalar, o próximo passo é paralelizar com limite de concorrência por banco, respeitando o rate limit de cada um.

## 📊 Sobre números e resultados

Este repositório **não** apresenta retorno financeiro, economia ou ganho de tempo. Valores monetários que aparecem em exemplos, painel e documentos vêm de **dados sintéticos** (ex.: massa de referência de 216 transações). Qualquer cálculo de retorno seria uma estimativa ilustrativa que depende de premissas de um caso real.

## 📁 Estrutura

```
├── src/
│   ├── extrator_bancario.py            # Extração resiliente dos 8 bancos
│   ├── claude_integration.py           # Diagnóstico de discrepâncias (Claude API + fallback)
│   ├── etl_power_query.m               # ETL em linguagem M (Power BI / Excel)
│   ├── conciliacao_bancaria.sql        # Modelo T-SQL, views e SP de discrepâncias
│   ├── executar_esteira_ao_vivo.py     # Esteira local: SQLite idempotente, APIs públicas, painel, e-mail
│   ├── executar_sql_demo.py            # Demonstração das regras SQL em banco local
│   ├── demo_executiva.py               # Demo ponta a ponta no terminal
│   ├── enviar_email_real.py            # Relatório executivo via SMTP/TLS
│   └── gerar_dashboard_interativo.py   # Gera o painel HTML
├── tests/                              # Testes automatizados (30)
├── docs/                               # Dossiê técnico, flow.json, spec do Power BI, imagens e apresentação
├── dashboard_demonstracao.html         # Painel executivo (abra no navegador)
├── transacoes_brutas.{json,csv}        # Massa de referência (216 transações)
├── feedback_loop_historico.json        # Histórico de diagnósticos da IA
└── .github/workflows/ci.yml            # Pipeline de testes
```

## 📄 Licença

[MIT](LICENSE) © Diego Aquino
