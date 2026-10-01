# Resumo técnico do projeto (1 página)

Projeto de portfólio de automação de conciliação bancária. **Todos os dados são sintéticos.**

## Problema (cenário hipotético)

Consolidar extratos de 8 bancos em uma única base, sem duplicar lançamentos quando uma carga é reexecutada, e sinalizar exceções (duplicatas, outliers, lançamentos acima de um teto de alçada).

## Arquitetura

```
 8 APIs bancárias --> Extrator Python --> Power Query (M) --> SQL (T-SQL / SQLite na demo)
 (OAuth 2.0, demo)   (Circuit Breaker)     (ETL)               |
                                                               +--> Painel HTML (Chart.js)
                                                               +--> Análise de discrepâncias (Claude API ou heurística)
                                                               +--> Relatório por e-mail (SMTP opcional)
```

## Pontos técnicos

- **Resiliência:** Circuit Breaker (CLOSED → OPEN → HALF_OPEN) e backoff exponencial com jitter para HTTP 429/5xx (`src/extrator_bancario.py`).
- **Idempotência:** chave SHA-256 por `banco | conta | data | valor | descrição normalizada`; reprocessar o lote não duplica registros.
- **Qualidade de dados:** validação de schema, taxa de erro do lote, regras de teto de alçada, duplicata potencial e outlier (média + 2σ).
- **Camada de IA (opcional):** só as discrepâncias são enviadas à API; sem chave, usa motor heurístico determinístico.
- **Testes:** 4 suítes automatizadas executadas no GitHub Actions (Python 3.12 e 3.13).

## Como demonstrar

1. `python src/demo_executiva.py` — extração, regras e diagnóstico no terminal.
2. `python src/executar_esteira_ao_vivo.py` — SQLite idempotente, câmbio/Selic ao vivo e painel (e-mail só se `SMTP_EMAIL` e `SMTP_PASSWORD` estiverem no `.env`).
3. Abrir `dashboard_demonstracao.html` e testar os filtros.

## Limitações

Dados sintéticos, sem integração real com bancos; SQLite na demo e T-SQL como modelo alvo; extração sequencial. Não há afirmação de retorno financeiro ou ganho medido em operação real.
