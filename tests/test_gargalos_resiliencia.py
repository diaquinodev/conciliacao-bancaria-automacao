"""
==============================================================================
SUITE DE TESTES FUNCIONAIS: GARGALOS, ARMADILHAS E RESILIÊNCIA
Esteira de Conciliação Bancária Automatizada - Viagens Corporativas
==============================================================================
"""

import os
import sys
import unittest
import sqlite3
import hashlib
import time
from datetime import datetime, date, timedelta

# Assegura que os módulos da esteira (src/) estejam no sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Assegura suporte a UTF-8 no Windows Console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from extrator_bancario import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ExtratorBancario,
)
from claude_integration import (
    DiscrepanciaInput,
    AnaliseDiscrepanciaOutput,
    AnalisadorIADiscrepancias,
)


class TestGargalosEArmadilhas(unittest.TestCase):
    """
    Testes funcionais que validam a mitigação de gargalos técnicos
    e armadilhas operacionais da tesouraria em viagens corporativas.
    """

    def setUp(self):
        """Inicializa banco SQLite em memória para testes de concorrência e idempotência."""
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self._setup_schema()

    def tearDown(self):
        self.conn.close()

    def _setup_schema(self):
        self.cursor.execute("""
            CREATE TABLE TB_EXTRATO_BANCARIO (
                id_transacao INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_transacao TEXT UNIQUE NOT NULL,
                banco_origem TEXT NOT NULL,
                data_transacao DATE NOT NULL,
                valor DECIMAL(18,2) NOT NULL,
                tipo_operacao TEXT NOT NULL,
                descricao_historico TEXT NOT NULL
            );
        """)
        self.cursor.execute("""
            CREATE TABLE TB_CONCILIACAO_AUDITORIA (
                id_conciliacao INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_transacao TEXT NOT NULL,
                status_conciliacao TEXT NOT NULL,
                divergencia_centavos DECIMAL(18,2) DEFAULT 0.00,
                FOREIGN KEY(hash_transacao) REFERENCES TB_EXTRATO_BANCARIO(hash_transacao)
            );
        """)
        self.conn.commit()

    # --------------------------------------------------------------------------
    # TESTE 1: ARMADILHA DE IDEMPOTÊNCIA (DUPLICAÇÃO POR RETENTATIVA DO FLOW)
    # --------------------------------------------------------------------------
    def test_01_idempotencia_reprocessamento_sem_duplicacao(self):
        """
        Armadilha: Power Automate re-executa a extração após queda ou timeout de rede.
        Gargalo Evitado: Duplicar saldos e movimentações financeiras no banco.
        Mecanismo: Hash SHA-256 e INSERT OR IGNORE / MERGE idempotente.
        """
        lote_transacoes = [
            ("ITAU", "2026-09-21", 12500.50, "CREDITO", "EMISSAO LATAM TKT 957382"),
            ("BRADESCO", "2026-09-21", 450.00, "DEBITO", "HOTEL IBIS DIARIA 1402"),
            ("SANTANDER", "2026-09-21", 89.90, "DEBITO", "UBER CORP SP"),
        ]

        def calcular_hash(banco, dt, val, tipo, desc):
            raw = f"{banco}|{dt}|{val:.2f}|{tipo}|{desc.strip().upper()}"
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()

        # 1ª Execução (Inserção normal de lote)
        for b, dt, val, tp, dsc in lote_transacoes:
            h = calcular_hash(b, dt, val, tp, dsc)
            self.cursor.execute("""
                INSERT OR IGNORE INTO TB_EXTRATO_BANCARIO
                (hash_transacao, banco_origem, data_transacao, valor, tipo_operacao, descricao_historico)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (h, b, dt, val, tp, dsc))
        self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) FROM TB_EXTRATO_BANCARIO;")
        total_apos_1a = self.cursor.fetchone()[0]
        self.assertEqual(total_apos_1a, 3, "Deveria ter inserido exatamente 3 transações na 1ª rodada.")

        # 2ª Execução (Simulação de Retentativa com mesmo lote)
        for b, dt, val, tp, dsc in lote_transacoes:
            h = calcular_hash(b, dt, val, tp, dsc)
            self.cursor.execute("""
                INSERT OR IGNORE INTO TB_EXTRATO_BANCARIO
                (hash_transacao, banco_origem, data_transacao, valor, tipo_operacao, descricao_historico)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (h, b, dt, val, tp, dsc))
        self.conn.commit()

        # Validação: Nenhuma duplicata permitida
        self.cursor.execute("SELECT COUNT(*) FROM TB_EXTRATO_BANCARIO;")
        total_apos_2a = self.cursor.fetchone()[0]

        self.assertEqual(total_apos_2a, 3, "O total no banco deve permanecer estritamente 3 após reprocessamento.")

    # --------------------------------------------------------------------------
    # TESTE 2: GARGALO DE RATE LIMIT & CIRCUIT BREAKER (HTTP 429 / 503)
    # --------------------------------------------------------------------------
    def test_02_resiliencia_circuit_breaker_sob_rate_limit(self):
        """
        Gargalo Técnico: APIs bancárias retornam HTTP 429 ao exceder limite de chamadas.
        Armadilha: Insistir em chamadas imediatas sem backoff bloqueia o CNPJ da empresa.
        Mecanismo: CircuitBreaker com transições CLOSED -> OPEN -> HALF_OPEN.
        """
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout_sec=0.2)
        cb = CircuitBreaker(config=config)

        # Estado inicial fechado (operacional normal)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        # Simula 3 falhas consecutivas de conexão bancária
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()

        # O circuito deve abrir imediatamente e barrar novas chamadas
        self.assertEqual(cb.state, CircuitState.OPEN, "Circuito deve estar ABERTO após 3 falhas.")
        self.assertFalse(cb.can_execute(), "Circuito ABERTO deve barrar novas requisições.")

        # Aguarda a janela de expiração (recovery timeout)
        time.sleep(0.25)

        # Após a janela, deve permitir uma chamada de teste em modo HALF_OPEN
        self.assertTrue(cb.can_execute(), "Deve permitir tentativa de recuperação pós-timeout.")
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Caso a chamada tenha sucesso, o circuito fecha novamente
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    # --------------------------------------------------------------------------
    # TESTE 3: ARMADILHAS DE VIAGENS CORPORATIVAS & DIAGNÓSTICO COGNITIVO
    # --------------------------------------------------------------------------
    def test_03_diagnostico_armadilhas_viagens_corporativas(self):
        """
        Armadilhas de Negócio:
        1. Faturamento BSP/IATA consolidado de companhias aéreas.
        2. No-Show e multas parciais de hotelaria.
        3. Despesas internacionais com dispersão de fuso horário e taxa de câmbio.
        """
        # Inicializa sem cliente externo para garantir execução local e determinística
        analisador = AnalisadorIADiscrepancias(api_key=None)

        discrepancias = [
            {
                "id": "DISC-001",
                "banco": "ITAU",
                "conta": "12345-6",
                "data_transacao": "2026-09-21",
                "valor": 850000.00,
                "descricao": "FATURA BSP IATA CONSOLIDADO 400 E-TICKETS",
                "motivo_detectado_sql": "DIVERGENCIA_AGRUPADOR_LOTE"
            },
            {
                "id": "DISC-002",
                "banco": "BRADESCO",
                "conta": "98765-4",
                "data_transacao": "2026-09-21",
                "valor": 320.00,
                "descricao": "HOTEL WINDSOR NO-SHOW RETENCAO 1 DIARIA",
                "motivo_detectado_sql": "duplicada_cancelamento_parcial"
            }
        ]

        # Executa motor de diagnóstico (usando motor analítico determinístico)
        resultado = analisador.analisar(discrepancias)
        analises = resultado.get("analises", [])
        resumo = resultado.get("resumo_executivo", "")

        self.assertEqual(len(analises), 2)
        # Validação do contrato de saída para cada discrepância
        for a in analises:
            self.assertIn(a["nivel_risco"], ["Baixo", "Médio", "Alto"])
            self.assertGreater(a["confianca"], 0.70)
            self.assertTrue(len(a["acao_recomendada"]) > 10)
            self.assertTrue(len(a["motivo_provavel"]) > 10)

        # Validação do resumo executivo gerado
        self.assertIn("auditoria", resumo.lower())

    # --------------------------------------------------------------------------
    # TESTE 4: INVARIANTE CONTÁBIL (EQUILÍBRIO DE PARTIDA DOBRADA)
    # --------------------------------------------------------------------------
    def test_04_equilibrio_contabil_extrato_vs_erp(self):
        """
        Armadilha: Desbalanceamento de saldos por omissão de taxas ou estornos.
        Regra Invariante: Saldo Final = Saldo Inicial + Créditos - Débitos.
        """
        saldo_inicial = 500000.00
        lancamentos = [
            {"tipo": "CREDITO", "valor": 120000.00}, # Recebimento de clientes corporativos
            {"tipo": "DEBITO",  "valor": 85000.00},  # Fatura BSP Companhias Aéreas
            {"tipo": "DEBITO",  "valor": 15000.00},  # Hotelaria consolidada
            {"tipo": "DEBITO",  "valor": 1250.40},   # Taxa de serviço e DU
            {"tipo": "CREDITO", "valor": 3400.00},   # Estorno de cancelamento de voo
        ]

        saldo_calculado = saldo_inicial
        for item in lancamentos:
            if item["tipo"] == "CREDITO":
                saldo_calculado += item["valor"]
            else:
                saldo_calculado -= item["valor"]

        # 500.000 + 120.000 - 85.000 - 15.000 - 1.250,40 + 3.400 = 522.149,60
        saldo_extrato_bancario = 522149.60

        self.assertAlmostEqual(
            saldo_calculado,
            saldo_extrato_bancario,
            places=2,
            msg="O balanço contábil deve fechar com precisão exata de centavos."
        )


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGargalosEArmadilhas)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
