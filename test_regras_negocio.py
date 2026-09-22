"""Testes de regressão das regras de negócio e de segurança da esteira.

Cobre: precedência de risco acima do teto de alçada, hash idempotente normalizado,
escape de HTML no painel e resumo de conciliação calculado a partir dos dados reais.
"""

import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import enviar_email_real
import executar_esteira_ao_vivo
import gerar_dashboard_interativo
from claude_integration import AnalisadorIADiscrepancias


class TestRegrasDeRisco(unittest.TestCase):
    def setUp(self):
        self.analisador = AnalisadorIADiscrepancias(api_key=None, feedback_file=os.devnull)

    def _risco(self, **item):
        base = {"id": "X", "banco": "ITAU", "conta": "1", "valor": 100.0, "descricao": "", "motivo_detectado_sql": ""}
        base.update(item)
        return self.analisador._gerar_analise_mock([base])["analises"][0]["nivel_risco"]

    def test_duplicata_acima_do_teto_e_risco_alto(self):
        self.assertEqual(
            self._risco(valor=250000.0, motivo_detectado_sql="Transação duplicada identificada"), "Alto"
        )

    def test_charter_acima_do_teto_nao_e_rebaixado(self):
        self.assertEqual(
            self._risco(valor=120500.0, descricao="CHARTER AEREO EXECUTIVO - Fretamento"), "Alto"
        )

    def test_duplicata_abaixo_do_teto_e_risco_medio(self):
        self.assertEqual(self._risco(valor=450.0, motivo_detectado_sql="duplicada"), "Médio")


class TestIdempotencia(unittest.TestCase):
    def test_formatacao_do_valor_nao_gera_duplicata(self):
        base = {"banco": "BB", "conta": "123-4", "data_transacao": "2026-09-21 10:00:00", "descricao": "Hotel Ibis"}
        lote = [dict(base, valor=1500.0), dict(base, valor="1500.00", descricao="HOTEL IBIS ")]

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "teste.db")
            origem = os.path.join(tmp, "transacoes_brutas.json")
            with open(origem, "w", encoding="utf-8") as f:
                json.dump(lote, f)

            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                with patch.object(executar_esteira_ao_vivo, "DB_PATH", db):
                    executar_esteira_ao_vivo.etapa_1_extracao_e_idempotencia()
            finally:
                os.chdir(cwd)

            with closing(sqlite3.connect(db)) as conn:
                total = conn.execute("SELECT COUNT(*) FROM TB_EXTRATO_CONCILIACAO").fetchone()[0]
        self.assertEqual(total, 1)


class TestSegurancaDashboard(unittest.TestCase):
    def test_descricao_maliciosa_nao_quebra_script(self):
        maliciosa = [{
            "id_externo": "TX1", "banco": "BB", "conta": "1", "data_transacao": "2026-09-21 10:00:00",
            "valor": 10.0, "descricao": "</script><img src=x onerror=alert(1)>", "tipo": "Débito",
            "categoria_sugerida": "Hospedagem",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "transacoes_brutas.json"), "w", encoding="utf-8") as f:
                json.dump(maliciosa, f)
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                gerar_dashboard_interativo.compilar_dashboard()
                with open("dashboard_demonstracao.html", encoding="utf-8") as f:
                    html = f.read()
            finally:
                os.chdir(cwd)

        bloco = re.search(r"const DADOS_TRANSACOES = (\[.*?\]);", html, re.DOTALL).group(1)
        self.assertNotIn("</script>", bloco)
        self.assertEqual(json.loads(bloco)[0]["descricao"], maliciosa[0]["descricao"])
        self.assertIn("escaparHtml(t.descricao)", html)


class TestResumoEmail(unittest.TestCase):
    def test_resumo_reflete_dados_extraidos(self):
        with open("transacoes_brutas.json", encoding="utf-8") as f:
            transacoes = json.load(f)
        resumo = enviar_email_real.resumir_conciliacao()

        self.assertEqual(sum(b["qtd"] for b in resumo.values()), len(transacoes))
        self.assertAlmostEqual(
            sum(b["total"] for b in resumo.values()), sum(float(t["valor"]) for t in transacoes), places=2
        )
        self.assertEqual(
            sum(b["discrepancias"] for b in resumo.values()),
            sum(1 for t in transacoes if float(t["valor"]) > enviar_email_real.TETO_ALCADA),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
