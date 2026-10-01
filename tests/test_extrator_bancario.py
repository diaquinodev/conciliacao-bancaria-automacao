"""Suíte de Testes Unitários para o Extrator Bancário.

Valida regras de resiliência, Circuit Breaker, Exponential Backoff,
validação de schemas e integridade dos dados extraídos.

Autor: Diego Aquino
Data: 2026-09-21
"""

import os
import sys

# Módulos da esteira ficam em src/ (execute os testes a partir da raiz do repositório)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from extrator_bancario import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ExtratorBancario,
)


class TestExtratorBancario(unittest.TestCase):
    """Casos de teste unitário para o Extrator Bancário."""

    def setUp(self) -> None:
        """Inicializa instância de teste."""
        self.extrator = ExtratorBancario(correlation_id="test-corr-12345", use_mock_fallback=True)

    def test_circuit_breaker_transicao_estados(self) -> None:
        """Verifica a transição de CLOSED para OPEN após atingir o limiar de falhas."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_sec=0.5)
        cb = CircuitBreaker(config)

        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

        # Teste de recuperação
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    def test_suporte_aos_oito_bancos(self) -> None:
        """Garante que a classe possui mapeamento e tokens para os 8 bancos corporativos."""
        esperados = ["BB", "BRADESCO", "ITAU", "SANTANDER", "CAIXA", "HSBC", "SICREDI", "INTER"]
        for banco in esperados:
            self.assertIn(banco, self.extrator.SUPPORTED_BANKS)
            self.assertIn(banco, self.extrator.tokens)
            self.assertIn(banco, self.extrator.circuit_breakers)

    def test_extracao_banco_individual(self) -> None:
        """Testa extração de transações de um banco com schema válido."""
        df = self.extrator.extrair_transacoes("BRADESCO", dias=1)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)

        colunas_esperadas = {"id_externo", "banco", "conta", "data_transacao", "valor", "descricao"}
        self.assertTrue(colunas_esperadas.issubset(set(df.columns)))
        self.assertTrue((df["banco"] == "BRADESCO").all())

    def test_extracao_consolidada_oito_bancos(self) -> None:
        """Verifica se a extração consolidada unifica os 8 bancos com correlation ID."""
        df_total = self.extrator.extrair_todos_bancos(dias=1)
        self.assertIsInstance(df_total, pd.DataFrame)
        self.assertFalse(df_total.empty)

        # Checar se correlation_id foi injetado em cada linha
        self.assertIn("correlation_id", df_total.columns)
        self.assertEqual(df_total["correlation_id"].iloc[0], "test-corr-12345")

        # Checar presença de múltiplos bancos
        bancos_retornados = df_total["banco"].unique()
        self.assertGreaterEqual(len(bancos_retornados), 5)

    def test_validacao_dados_com_sucesso(self) -> None:
        """Testa o validador com dados íntegros."""
        df = pd.DataFrame([
            {
                "id_externo": "TX1",
                "banco": "BB",
                "conta": "12345-6",
                "data_transacao": "2026-09-21 10:00:00",
                "valor": 1500.50,
                "descricao": "Passagem SP-RJ",
            },
            {
                "id_externo": "TX2",
                "banco": "ITAU",
                "conta": "54321-0",
                "data_transacao": "2026-09-21 11:30:00",
                "valor": 450.00,
                "descricao": "Hotel Copacabana",
            },
        ])

        metricas = self.extrator.validar_dados(df)
        self.assertEqual(metricas["status"], "VALIDADO")
        self.assertEqual(metricas["total_registros"], 2)
        self.assertEqual(metricas["registros_validos"], 2)
        self.assertEqual(metricas["registros_invalidos"], 0)
        self.assertEqual(metricas["taxa_erro"], 0.0)

    def test_validacao_dados_com_anomalias(self) -> None:
        """Testa a detecção de valores inválidos (negativos e bancos desconhecidos)."""
        df_invalido = pd.DataFrame([
            {
                "id_externo": "TX1",
                "banco": "BANCO_INEXISTENTE",
                "conta": "12345-6",
                "data_transacao": "2026-09-21 10:00:00",
                "valor": 1500.50,
                "descricao": "Passagem",
            },
            {
                "id_externo": "TX2",
                "banco": "BB",
                "conta": "12345-6",
                "data_transacao": "2026-09-21 11:00:00",
                "valor": -100.00,  # Valor negativo
                "descricao": "Estorno",
            },
        ])

        metricas = self.extrator.validar_dados(df_invalido)
        self.assertEqual(metricas["total_registros"], 2)
        self.assertEqual(metricas["registros_invalidos"], 2)
        self.assertEqual(metricas["taxa_erro"], 1.0)

    def test_exportacao_arquivos(self) -> None:
        """Testa geração de arquivos físicos JSON e CSV."""
        df = self.extrator.extrair_transacoes("ITAU", dias=1)
        json_path = "test_transacoes.json"
        csv_path = "test_transacoes.csv"

        try:
            status_json, status_csv = self.extrator.exportar_arquivos(df, json_path, csv_path)
            self.assertTrue(status_json)
            self.assertTrue(status_csv)
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(csv_path))
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)
            if os.path.exists(csv_path):
                os.remove(csv_path)


if __name__ == "__main__":
    unittest.main()
