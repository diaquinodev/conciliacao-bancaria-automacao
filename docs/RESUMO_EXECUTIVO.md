# Resumo do projeto

**Automação de conciliação bancária** · Diego Aquino · projeto de portfólio com **dados sintéticos**.

## Problema (cenário hipotético)

Consolidar extratos de 8 bancos, evitar lançamentos duplicados em reexecuções e sinalizar exceções para revisão.

## Solução

| Componente | Ferramenta | Função |
|---|---|---|
| Extração | Python | Consumo de APIs bancárias (OAuth 2.0; modo demo sintético) com Circuit Breaker e backoff |
| Transformação | Power Query (M) | Limpeza, tipagem, deduplicação e categoria |
| Dados | SQL (T-SQL; SQLite na demo) | Modelo relacional, views, auditoria e SP de discrepâncias |
| Orquestração | Power Automate (desenho em `flow.json`) | Fluxo diário e alertas |
| BI | Painel HTML / Power BI (spec) | KPIs, filtros e extrato |
| IA (opcional) | Claude API ou heurística | Diagnóstico das discrepâncias |

## Regras implementadas

Teto de alçada (R$ 100.000,00), duplicata potencial, outlier (média + 2σ em 90 dias), validação de schema e idempotência por SHA-256.

## Evidências

- 4 suítes de testes automatizados no GitHub Actions (Python 3.12 e 3.13).
- Massa de referência com 216 transações sintéticas (`transacoes_brutas.json`).

## Limitações

Sem integração real com bancos; resultados de ganho de tempo ou financeiro **não** foram medidos e não são afirmados aqui.
