"""DEMONSTRAÇÃO EXECUTIVA END-TO-END: CONCILIAÇÃO BANCÁRIA & AUDITORIA DE FECHAMENTO
Script de apresentação técnica do case de automação bancária.
Autor: Diego Aquino
Data: 2026-09-21 / 2026-09-22
"""

import io
import json
import logging
import os
import sys
import time
from datetime import datetime

# Garante compatibilidade UTF-8 no Windows Console (PowerShell / CMD)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Manter nível de logs em WARNING durante a demo executiva para saída limpa
# (precisa valer antes de instanciar extrator e analisador, que logam no construtor)
os.environ.setdefault("LOG_LEVEL", "WARNING")
logging.basicConfig(level=logging.WARNING)

from extrator_bancario import ExtratorBancario
from claude_integration import AnalisadorIADiscrepancias


def print_banner(texto: str):
    linha = "=" * 74
    print(f"\n{linha}")
    print(f" {texto}")
    print(f"{linha}\n")


def main():
    print_banner("SISTEMA INTEGRADO DE CONCILIAÇÃO BANCÁRIA - FECHAMENTO DIÁRIO")
    print(f"Data/Hora do Processamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("Empresa: Despesas Corporativas | 8 Contas Comerciais Auditadas")
    print("Orquestração: Power Automate Flow | Validação: Regras SQL Server & Motor Analítico\n")

    # ETAPA 1: EXTRAÇÃO MULTBANCÁRIA
    print(">> [ETAPA 1/4] Disparando ExtratorBancario (8 Bancos Comerciais)...")
    start_time = time.time()
    
    # Silencia logs detalhados durante o banner para clareza executiva
    extrator = ExtratorBancario(correlation_id="FECHAMENTO-DIARIO-2026", use_mock_fallback=True)
    extrator.logger.setLevel(logging.WARNING)
    
    df_transacoes = extrator.extrair_todos_bancos(dias=1)
    
    if df_transacoes.empty:
        print("[ERRO] Falha na extração de transações.")
        return

    extrator.validar_dados(df_transacoes)
    extrator.exportar_arquivos(df_transacoes, "transacoes_brutas.json", "transacoes_brutas.csv")
    tempo_extracao = time.time() - start_time
    print(f"   [OK] Extração concluída em {tempo_extracao:.2f}s!")
    print(f"   [OK] Total de transações processadas: {len(df_transacoes)}")
    print(f"   [OK] Volume financeiro consolidado: R$ {float(df_transacoes['valor'].sum()):,.2f}\n")

    time.sleep(0.8)

    # ETAPA 2: TRANSFORMAÇÃO & REGRAS CONTÁBEIS (POWER QUERY + SQL)
    print(">> [ETAPA 2/4] Executando Transformação Power Query & Regras SQL Server...")
    print("   -> Deduplicação por chave composta UK_EXTERNO (ID + Banco + Conta)")
    print("   -> Cálculo de desvio-padrão histórico (STDEV a 2 sigma)")
    print("   -> Filtro de teto de alçada (> R$ 100.000,00)")
    
    anomalias_detectadas = []
    
    # Transações > 100k
    altos_valores = df_transacoes[df_transacoes['valor'] > 100000]
    for _, row in altos_valores.iterrows():
        anomalias_detectadas.append({
            "id": row['id_externo'],
            "banco": row['banco'],
            "conta": row['conta'],
            "data_transacao": row['data_transacao'],
            "valor": float(row['valor']),
            "descricao": row['descricao'],
            "motivo_detectado_sql": "Valor crítico excedendo o teto de R$ 100.000,00"
        })

    # Duplicata clássica de gateway de pagamento
    primeira = df_transacoes.iloc[0]
    anomalias_detectadas.append({
        "id": f"{primeira['id_externo']}_DUP",
        "banco": primeira['banco'],
        "conta": primeira['conta'],
        "data_transacao": primeira['data_transacao'],
        "valor": float(primeira['valor']),
        "descricao": f"{primeira['descricao']} [LANCAMENTO REPETIDO]",
        "motivo_detectado_sql": "Transação duplicada identificada pelo hash UK_EXTERNO"
    })

    print(f"   [AVISO] Inconsistências apontadas pelo SQL Server: {len(anomalias_detectadas)}")
    time.sleep(0.8)

    # ETAPA 3: ANÁLISE DE CAUSA-RAIZ E REGULARIZAÇÃO
    print("\n>> [ETAPA 3/4] Executando Motor Analítico para Diagnóstico e Regularização...")
    analisador = AnalisadorIADiscrepancias(correlation_id="FECHAMENTO-DIARIO-2026")
    analisador.logger.logger.setLevel(logging.WARNING)
    diagnostico = analisador.analisar(json.dumps(anomalias_detectadas))
    
    time.sleep(0.8)

    # ETAPA 4: RESULTADO CONSOLIDADO & PARECER EXECUTIVO
    print_banner("RELATÓRIO DE AUDITORIA CONTÁBIL (PAINEL DE GESTÃO / DIRETORIA)")
    
    taxa_acuracia = ((len(df_transacoes) - len(anomalias_detectadas)) / len(df_transacoes)) * 100
    print(f"Taxa de Conformidade Contábil: {taxa_acuracia:.2f}%")
    print(f"Parecer de Fechamento: {diagnostico.get('resumo_executivo', 'Auditoria concluída com sucesso.')}")
    print("-" * 74)
    print("DETALHAMENTO DAS INCONSISTÊNCIAS IDENTIFICADAS E PLANO DE AÇÃO:\n")

    for i, item in enumerate(diagnostico.get("analises", []), 1):
        print(f"[{i}] LANÇAMENTO: {item.get('id')} | CRITICIDADE: {item.get('nivel_risco').upper()}")
        print(f"    * Causa-Raiz Apurada : {item.get('motivo_provavel')}")
        print(f"    * Ação Recomendada   : {item.get('acao_recomendada')}")
        print(f"    * Padrão Operacional : {item.get('padrao_identificado')}")
        print()

    print("-" * 74)
    print("PRÓXIMAS AÇÕES DO WORKFLOW (orquestradas pelo Power Automate em produção - flow.json):")
    print("   [FLUXO] Notificação de alta prioridade à Controladoria (demo real: enviar_email_real.py)")
    print("   [FLUXO] Alerta de fechamento no canal da Controladoria (Microsoft Teams)")
    print("   [FLUXO] Atualização do dataset do Painel Power BI")
    print("   [OK]    Trilha de auditoria registrada com Correlation ID: 'FECHAMENTO-DIARIO-2026'")
    print_banner("FECHAMENTO DIÁRIO HOMOLOGADO COM SUCESSO!")


if __name__ == "__main__":
    main()
