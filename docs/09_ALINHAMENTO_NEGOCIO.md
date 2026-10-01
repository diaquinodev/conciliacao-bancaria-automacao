# Contexto de negócio (ilustrativo)

Projeto de portfólio com **dados sintéticos**. Este documento descreve, de forma qualitativa, os problemas que a esteira de conciliação busca endereçar. Não contém cálculo de retorno financeiro: qualquer estimativa de ganho dependeria de premissas de um caso real.

## 1. Cenário hipotético

Uma área financeira com várias contas bancárias (8 neste projeto) precisa consolidar extratos de formatos e horários diferentes antes de decidir sobre caixa.

## 2. Dores típicas e resposta técnica

| Área | Dor típica | Resposta no projeto | Onde ver |
| :--- | :--- | :--- | :--- |
| Tesouraria | Extratos de bancos diferentes, com limites de requisição distintos | Extrator com Circuit Breaker e backoff; um banco com falha não derruba os demais | `src/extrator_bancario.py` |
| Controladoria | Falta de trilha de auditoria | Tabela de auditoria com `correlation_id` | `src/conciliacao_bancaria.sql` |
| Contas a pagar | Lançamentos duplicados após reprocessamento | Chave idempotente SHA-256 e `UNIQUE(ID_EXTERNO, BANCO, CONTA)` | `src/executar_esteira_ao_vivo.py` |
| Gestão | Lançamentos de valor alto sem revisão | Teto de alçada que gera discrepância de risco Alto | `SP_DETECTAR_DISCREPANCIAS` |
| Análise | Dificuldade de investigar exceções | Diagnóstico por IA (opcional) ou heurística | `src/claude_integration.py` |

## 3. Conceitos de negócio usados

- **Alçada de aprovação:** limite de valor acima do qual o lançamento exige aprovação (R$ 100.000,00 no projeto).
- **Idempotência:** reexecutar a carga produz o mesmo estado, sem duplicar registros.
- **Trilha de auditoria:** registro de quem/quando/por que um lançamento mudou de status.
- **Partida dobrada:** saldo final = saldo inicial + créditos − débitos (validada em `tests/test_gargalos_resiliencia.py`).

## 4. O que não é afirmado

Não há medição de tempo economizado, taxa de acurácia em produção, economia anual ou retorno financeiro. Valores monetários nos exemplos e no painel são fictícios.
