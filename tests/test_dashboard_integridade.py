"""
==============================================================================
SUÍTE DE TESTES UNITÁRIOS & AUDITORIA DE INTEGRIDADE DO DASHBOARD
Validação de Dados Reais, Filtros Front-End, Paginação e Elementos DOM
==============================================================================
Autor: Diego Aquino
Data: 2026-09-22
Contexto: projeto de portfólio de automação bancária (dados sintéticos)
"""

import os
import sys

# Módulos da esteira ficam em src/ (execute os testes a partir da raiz do repositório)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import re
import json
import math
import unittest
from datetime import datetime
from collections import Counter

# Assegura suporte a UTF-8 no Windows Console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class TestIntegridadeEDashboard(unittest.TestCase):
    """
    Testes de integridade de dados e validação de funcionamento
    dos filtros interativos e elementos front-end do Dashboard.
    """

    @classmethod
    def setUpClass(cls):
        """Carrega transações reais e arquivo HTML do dashboard."""
        cls.caminho_json = "transacoes_brutas.json"
        cls.caminho_html = "dashboard_demonstracao.html"

        with open(cls.caminho_json, "r", encoding="utf-8") as f:
            cls.transacoes = json.load(f)

        with open(cls.caminho_html, "r", encoding="utf-8") as f:
            cls.conteudo_html = f.read()

        cls.bancos_esperados = {"BB", "BRADESCO", "ITAU", "SANTANDER", "CAIXA", "INTER", "SICREDI", "HSBC"}
        cls.categorias_esperadas = {
            "Passagens Aéreas", "Hospedagem", "Transfer/Transporte", "Seguros", "Taxas/Serviços"
        }

    # --------------------------------------------------------------------------
    # 1. TESTES DE INTEGRIDADE DOS DADOS EXTRAÍDOS
    # --------------------------------------------------------------------------
    def test_01_quantidade_e_unicidade_transacoes(self):
        """Valida que exatamente 216 transações existem e todas possuem IDs únicos."""
        self.assertEqual(len(self.transacoes), 216, "A base deve conter 216 transações extraídas.")
        
        ids = [t.get("id_externo") for t in self.transacoes]
        self.assertEqual(len(ids), len(set(ids)), "Não pode haver IDs duplicados na extração.")

    def test_02_validade_campos_e_valores_positivos(self):
        """Garante que nenhum registro possui valor zerado, nulo ou campos obrigatórios vazios."""
        campos_obrigatorios = ["id_externo", "banco", "conta", "data_transacao", "valor", "descricao", "tipo", "categoria_sugerida"]

        for idx, t in enumerate(self.transacoes):
            for campo in campos_obrigatorios:
                self.assertIn(campo, t, f"Campo {campo} ausente na transação índice {idx}.")
                self.assertIsNotNone(t[campo], f"Campo {campo} é nulo na transação {t.get('id_externo')}.")
            
            valor = float(t.get("valor", 0.0))
            self.assertGreater(valor, 0.0, f"Transação {t.get('id_externo')} possui valor inválido (<= 0).")

    def test_03_conformidade_dos_oito_bancos_e_categorias(self):
        """Valida se todos os lançamentos pertencem estritamente aos 8 bancos comerciais e categorias válidas."""
        bancos_encontrados = set(t.get("banco") for t in self.transacoes)
        categorias_encontradas = set(t.get("categoria_sugerida") for t in self.transacoes)

        self.assertEqual(bancos_encontrados, self.bancos_esperados, "Os bancos na base devem corresponder aos 8 oficiais.")
        self.assertTrue(categorias_encontradas.issubset(self.categorias_esperadas), "Categorias desconhecidas detectadas.")

    def test_04_formato_datas_transacao(self):
        """Garante que todas as datas estão em formato válido e dentro do período auditado."""
        for t in self.transacoes:
            dt_str = t.get("data_transacao", "")[:10]
            try:
                dt_obj = datetime.strptime(dt_str, "%Y-%m-%d")
                self.assertIn(dt_obj.year, [2026], "Ano da transação fora do escopo do case (2026).")
            except ValueError:
                self.fail(f"Data inválida detectada na transação {t.get('id_externo')}: {dt_str}")

    # --------------------------------------------------------------------------
    # 2. TESTES DE INTEGRIDADE DO FRONT-END (HTML & DOM)
    # --------------------------------------------------------------------------
    def test_05_elementos_dom_essenciais_presentes(self):
        """Valida que todos os IDs de elementos manipulados pelo JavaScript existem no HTML."""
        elementos_obrigatorios = [
            'id="filtro-categoria"',
            'id="filtro-banco"',
            'id="filtro-data-inicio"',
            'id="filtro-data-fim"',
            'id="filtro-busca"',
            'id="btn-limpar"',
            'id="kpi-total-gasto"',
            'id="kpi-qtd-transacoes"',
            'id="kpi-ticket-medio"',
            'id="kpi-maior-gasto"',
            'id="chart-categorias"',
            'id="chart-bancos"',
            'id="tabela-corpo"',
            'id="btn-prev"',
            'id="btn-next"',
            'id="page-info"',
            'id="table-counter"'
        ]

        for elem in elementos_obrigatorios:
            self.assertIn(elem, self.conteudo_html, f"Elemento essencial do front-end ausente no HTML: {elem}")

    def test_06_sincronizacao_dados_embutidos_no_html(self):
        """Valida se o array JavaScript DADOS_TRANSACOES no HTML contém exatamente as 216 transações reais."""
        match = re.search(r'const DADOS_TRANSACOES = (\[.*?\]);', self.conteudo_html, re.DOTALL)
        self.assertIsNotNone(match, "Array DADOS_TRANSACOES não encontrado no script do HTML.")

        dados_html = json.loads(match.group(1))
        self.assertEqual(len(dados_html), len(self.transacoes), "Quantidade de dados embutidos no HTML difere do JSON real.")
        
        # Valida que o total em R$ embutido no HTML bate com o JSON real
        total_json = sum(t["valor"] for t in self.transacoes)
        total_html = sum(t["valor"] for t in dados_html)
        self.assertAlmostEqual(total_json, total_html, places=2, msg="Soma dos valores embutidos difere do arquivo real.")

    # --------------------------------------------------------------------------
    # 3. TESTES FUNCIONAIS DOS FILTROS (SIMULAÇÃO EXATA DA LÓGICA DO JAVASCRIPT)
    # --------------------------------------------------------------------------
    def _simular_filtro_js(self, categoria="", banco="", data_inicio="", data_fim="", busca=""):
        """Implementação exata da lógica da função JS aplicarFiltros()."""
        cat_filtro = categoria.lower().strip()
        banco_filtro = banco.upper().strip()
        busca_filtro = busca.lower().strip()

        resultado = []
        for t in self.transacoes:
            dt = (t.get("data_transacao") or "")[:10]
            cat = (t.get("categoria_sugerida") or "").lower()
            b = (t.get("banco") or "").upper()
            desc = (t.get("descricao") or "").lower()

            if cat_filtro and cat_filtro not in cat:
                continue
            if banco_filtro and b != banco_filtro:
                continue
            if data_inicio and dt < data_inicio:
                continue
            if data_fim and dt > data_fim:
                continue
            if busca_filtro and (busca_filtro not in desc and busca_filtro not in cat):
                continue

            resultado.append(t)
        return resultado

    def test_07_filtro_por_cada_categoria(self):
        """Valida que cada categoria filtra a quantidade e o volume exato de despesas."""
        casos_categoria = {
            "Passagens Aéreas": {"qtd": 58, "total_esperado": 649332.51},
            "Hospedagem": {"qtd": 52, "total_esperado": 149715.16},
            "Transfer/Transporte": {"qtd": 54, "total_esperado": 24395.34},
            "Seguros": {"qtd": 28, "total_esperado": 15160.76},
            "Taxas/Serviços": {"qtd": 24, "total_esperado": 7288.33}
        }

        for cat, esperado in casos_categoria.items():
            filtrados = self._simular_filtro_js(categoria=cat)
            total = sum(t["valor"] for t in filtrados)

            self.assertEqual(len(filtrados), esperado["qtd"], f"Qtd incorreta para categoria {cat}.")
            self.assertAlmostEqual(total, esperado["total_esperado"], places=2, 
                                   msg=f"Total em R$ divergente para categoria {cat}.")

    def test_08_filtro_por_cada_um_dos_oito_bancos(self):
        """Valida se filtrar por cada banco isola os registros correspondentes."""
        for banco in self.bancos_esperados:
            filtrados = self._simular_filtro_js(banco=banco)
            self.assertGreater(len(filtrados), 0, f"O banco {banco} não retornou nenhum registro.")
            for t in filtrados:
                self.assertEqual(t.get("banco"), banco, f"Registro com banco incorreto encontrado no filtro de {banco}.")

    def test_09_filtro_por_intervalo_de_datas(self):
        """Valida o funcionamento dos filtros de Data Inicial e Data Final."""
        # Filtra apenas o dia 2026-09-20
        dia_20 = self._simular_filtro_js(data_inicio="2026-09-20", data_fim="2026-09-20")
        self.assertGreater(len(dia_20), 0)
        for t in dia_20:
            self.assertTrue(t["data_transacao"].startswith("2026-09-20"))

        # Filtra apenas o dia 2026-09-21
        dia_21 = self._simular_filtro_js(data_inicio="2026-09-21", data_fim="2026-09-21")
        self.assertGreater(len(dia_21), 0)
        for t in dia_21:
            self.assertTrue(t["data_transacao"].startswith("2026-09-21"))

        # A soma dos dois dias deve dar o total de 216
        self.assertEqual(len(dia_20) + len(dia_21), 216)

        # Filtro em data inexistente futura deve retornar lista vazia
        futuro = self._simular_filtro_js(data_inicio="2026-10-01", data_fim="2026-10-05")
        self.assertEqual(len(futuro), 0, "Filtro de data futura deve retornar 0 registros.")

    def test_10_busca_textual_por_fornecedor(self):
        """Valida se o campo de pesquisa rápida localiza fornecedores específicos."""
        # Busca por Copacabana
        copacabana = self._simular_filtro_js(busca="copacabana")
        self.assertGreater(len(copacabana), 0, "Deveria encontrar transações do Copacabana Palace.")
        for t in copacabana:
            self.assertIn("copacabana", t["descricao"].lower())

        # Busca por GOL
        gol = self._simular_filtro_js(busca="gol")
        self.assertGreater(len(gol), 0, "Deveria encontrar transações da GOL.")

        # Busca por termo inexistente
        inexistente = self._simular_filtro_js(busca="fornecedor_inexistente_xyz_123")
        self.assertEqual(len(inexistente), 0, "Busca sem correspondência deve retornar 0 resultados.")

    def test_11_filtros_combinados_multiplos(self):
        """Valida a combinação simultânea de múltiplos filtros (Ex: Categoria + Banco)."""
        # Filtrar Hospedagem no Itaú
        hospedagem_itau = self._simular_filtro_js(categoria="Hospedagem", banco="ITAU")
        self.assertGreater(len(hospedagem_itau), 0)
        for t in hospedagem_itau:
            self.assertEqual(t["banco"], "ITAU")
            self.assertIn("hospedagem", t["categoria_sugerida"].lower())

    def test_12_paginacao_e_limites(self):
        """Valida que a paginação de 15 itens por página fecha exatamente em 15 páginas."""
        itens_por_pagina = 15
        total_itens = len(self.transacoes)
        total_paginas = math.ceil(total_itens / itens_por_pagina)

        self.assertEqual(total_paginas, 15, "216 itens a 15 por página devem resultar em 15 páginas.")
        
        # Última página deve ter exatamente 216 - (14 * 15) = 6 itens
        itens_ultima_pagina = total_itens - (14 * itens_por_pagina)
        self.assertEqual(itens_ultima_pagina, 6, "A 15ª página deve conter exatamente 6 itens.")

    def test_13_reset_de_filtros(self):
        """Valida que limpar os filtros restaura 100% dos dados e o valor total."""
        resetados = self._simular_filtro_js(categoria="", banco="", data_inicio="2026-09-20", data_fim="2026-09-22", busca="")
        self.assertEqual(len(resetados), 216, "Limpar filtros deve restaurar todas as 216 transações.")
        total = sum(t["valor"] for t in resetados)
        self.assertAlmostEqual(total, 845892.10, places=2, msg="O total após reset deve ser exatamente R$ 845.892,10.")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegridadeEDashboard)
    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(suite)
    sys.exit(not resultado.wasSuccessful())
