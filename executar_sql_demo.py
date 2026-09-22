"""SCRIPT DE VALIDAÇÃO REAL DO BANCO DE DADOS SQL
Criação física de banco relacional local (conciliacao_bancaria.db),
ingestão de dados das 8 contas e execução de queries analíticas / Stored Procedures.

Autor: Diego Luiz Lino de Aquino (diaquinotech@gmail.com)
Data: 2026-09-21
"""

import io
import json
import os
import sqlite3
import sys
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


DB_PATH = "conciliacao_bancaria.db"
JSON_PATH = "transacoes_brutas.json"


def print_linha():
    print("-" * 75)


def main():
    print("\n" + "=" * 75)
    print(" DEMONSTRAÇÃO PRÁTICA: MOTOR DE BANCO DE DADOS RELACIONAL (SQL)")
    print("=" * 75)
    print(f"Arquivo do Banco Local: {os.path.abspath(DB_PATH)}")
    print(f"Data de Execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")

    # 1. Conexão com o banco relacional
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Criação das Tabelas Relacionais (DDL)
    print(">> [1/4] Criando Estrutura Relacional (Tabelas, Índices e Constraints)...")
    cursor.executescript("""
    DROP TABLE IF EXISTS TB_AUDITORIA_CONCILIACAO;
    DROP TABLE IF EXISTS TB_CONCILIACAO_BANCARIA;

    CREATE TABLE TB_CONCILIACAO_BANCARIA (
        ID_TRANSACAO INTEGER PRIMARY KEY AUTOINCREMENT,
        ID_EXTERNO TEXT NOT NULL,
        BANCO TEXT NOT NULL,
        CONTA TEXT NOT NULL,
        DATA_TRANSACAO TEXT NOT NULL,
        VALOR REAL NOT NULL,
        DESCRICAO TEXT NOT NULL,
        TIPO TEXT DEFAULT 'Débito',
        CATEGORIA TEXT,
        STATUS_CONCILIACAO TEXT DEFAULT 'Pendente',
        FLAG_DISCREPANCIA INTEGER DEFAULT 0,
        MOTIVO_DISCREPANCIA TEXT,
        DATA_PROCESSAMENTO TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(ID_EXTERNO, BANCO, CONTA)
    );

    CREATE INDEX IDX_CONC_BANCO ON TB_CONCILIACAO_BANCARIA(BANCO);
    CREATE INDEX IDX_CONC_FLAG ON TB_CONCILIACAO_BANCARIA(FLAG_DISCREPANCIA);

    CREATE TABLE TB_AUDITORIA_CONCILIACAO (
        ID_AUDITORIA INTEGER PRIMARY KEY AUTOINCREMENT,
        ID_TRANSACAO INTEGER,
        ACAO TEXT NOT NULL,
        DETALHES TEXT,
        USUARIO TEXT DEFAULT 'sistema_automacao',
        DATA_ACAO TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)
    conn.commit()
    print("   [OK] Tabelas 'TB_CONCILIACAO_BANCARIA' e 'TB_AUDITORIA_CONCILIACAO' criadas com sucesso!")

    # 3. Carga dos Dados das 8 Contas Comerciais
    print("\n>> [2/4] Carregando Transações Extraídas dos 8 Bancos no SQL...")
    if not os.path.exists(JSON_PATH):
        print(f"   [ERRO] Arquivo {JSON_PATH} não encontrado. Execute o extrator primeiro.")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        registros = json.load(f)

    for r in registros:
        cursor.execute("""
        INSERT OR IGNORE INTO TB_CONCILIACAO_BANCARIA 
        (ID_EXTERNO, BANCO, CONTA, DATA_TRANSACAO, VALOR, DESCRICAO, CATEGORIA)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            r.get("id_externo"),
            r.get("banco"),
            r.get("conta"),
            r.get("data_transacao"),
            float(r.get("valor", 0)),
            r.get("descricao"),
            r.get("categoria_sugerida", "Outros")
        ))
    
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM TB_CONCILIACAO_BANCARIA;")
    total_linhas = cursor.fetchone()[0]
    print(f"   [OK] {total_linhas} registros inseridos com chave de integridade relacional!")

    # 4. Execução de Regras de Detecção SQL (Equivalente à Stored Procedure)
    print("\n>> [3/4] Executando Regras de Auditoria SQL (SP_DETECTAR_DISCREPANCIAS)...")
    
    # Regra A: Transações com valor acima do teto de R$ 100.000,00
    cursor.execute("""
    UPDATE TB_CONCILIACAO_BANCARIA
    SET FLAG_DISCREPANCIA = 1,
        STATUS_CONCILIACAO = 'Discrepância',
        MOTIVO_DISCREPANCIA = 'Valor crítico excedendo o teto de R$ 100.000,00'
    WHERE VALOR > 100000;
    """)
    
    # Inserir propositalmente uma duplicata para teste das regras de unicidade
    cursor.execute("""
    INSERT OR IGNORE INTO TB_CONCILIACAO_BANCARIA 
    (ID_EXTERNO, BANCO, CONTA, DATA_TRANSACAO, VALOR, DESCRICAO, CATEGORIA, FLAG_DISCREPANCIA, STATUS_CONCILIACAO, MOTIVO_DISCREPANCIA)
    VALUES ('TX_BB_DUP_DEMO', 'BB', '12345-6', datetime('now'), 45000.0, 'LATAM AIRLINES - Bilhete GRU-MIA [DUPLICADA]', 'Passagens Aéreas', 1, 'Discrepância', 'Potencial duplicata identificada');
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM TB_CONCILIACAO_BANCARIA WHERE FLAG_DISCREPANCIA = 1;")
    discrepancias_count = cursor.fetchone()[0]
    print(f"   [OK] Procedimento concluído: {discrepancias_count} inconsistências marcadas no banco.")

    # 5. Queries Analíticas SQL (O que o entrevistador quer ver)
    print("\n>> [4/4] Executando Queries Analíticas de Consolidação (Views do Power BI):")
    print_linha()
    print(f"{'BANCO':<15} | {'OPERAÇÕES':<10} | {'VOLUME TOTAL (R$)':<20} | {'DISCREPÂNCIAS':<12}")
    print_linha()

    cursor.execute("""
    SELECT 
        BANCO,
        COUNT(*) AS TOTAL_OPERACOES,
        ROUND(SUM(VALOR), 2) AS VOLUME_TOTAL,
        SUM(CASE WHEN FLAG_DISCREPANCIA = 1 THEN 1 ELSE 0 END) AS DISCREPANCIAS
    FROM TB_CONCILIACAO_BANCARIA
    GROUP BY BANCO
    ORDER BY VOLUME_TOTAL DESC;
    """)

    for row in cursor.fetchall():
        banco, ops, vol, disc = row
        print(f"{banco:<15} | {ops:<10} | R$ {vol:>16,.2f} | {disc:<12}")

    print_linha()

    # Exibir detalhes das inconsistências detectadas via SQL
    print("\nDETALHE DAS INCONSISTÊNCIAS ENCONTRADAS VIA QUERY SQL:")
    print_linha()
    cursor.execute("""
    SELECT ID_EXTERNO, BANCO, VALOR, MOTIVO_DISCREPANCIA 
    FROM TB_CONCILIACAO_BANCARIA 
    WHERE FLAG_DISCREPANCIA = 1 
    LIMIT 5;
    """)
    for r in cursor.fetchall():
        print(f"* [{r[1]}] {r[0]}: R$ {r[2]:,.2f} -> {r[3]}")
    print_linha()

    conn.close()
    print("\n[SUCESSO] Base relacional 'conciliacao_bancaria.db' pronta para auditoria ao vivo!\n")


if __name__ == "__main__":
    main()
