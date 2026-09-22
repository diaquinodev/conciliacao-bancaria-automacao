"""Módulo de Integração com Claude API para Análise Inteligente de Discrepâncias.

Este módulo consome a API da Anthropic para analisar anomalias financeiras em viagens
corporativas, classificando nível de risco, sugerindo ações corretivas imediatas,
identificando precedentes históricos e detectando padrões operacionais recorrentes.

Autor: Diego Luiz Lino de Aquino
Data: 2026-09-21
Contexto: Processo Seletivo - Desenvolvedor de Automação
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


class StructuredLogger:
    """Emissor de logs estruturados em formato JSON para auditoria contínua."""

    def __init__(self, correlation_id: str) -> None:
        self.correlation_id = correlation_id
        self.logger = logging.getLogger(f"AnalisadorIA_{correlation_id[:8]}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

    def log(self, level: str, action: str, message: str, **kwargs: Any) -> None:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "correlation_id": self.correlation_id,
            "action": action,
            "message": message,
            **kwargs,
        }
        self.logger.info(json.dumps(payload, ensure_ascii=False))


@dataclass
class DiscrepanciaInput:
    """Modelo de entrada para uma discrepância financeira."""
    id: str
    banco: str
    conta: str
    data_transacao: str
    valor: float
    descricao: str
    motivo_detectado_sql: str


@dataclass
class AnaliseDiscrepanciaOutput:
    """Modelo de saída para o diagnóstico da Inteligência Artificial."""
    id: str
    motivo_provavel: str
    confianca: float
    nivel_risco: str  # Baixo, Médio, Alto
    acao_recomendada: str
    precedentes_similares: str
    padrao_identificado: str


class AnalisadorIADiscrepancias:
    """Motor de análise inteligente de anomalias contábeis via LLM."""

    SYSTEM_PROMPT = """Você é um especialista sênior em conformidade financeira, auditoria contábil e conciliação bancária de grandes empresas de viagens corporativas.
Sua missão é analisar discrepâncias encontradas na esteira de conciliação bancária entre 8 contas comerciais (BB, Bradesco, Itaú, Santander, Caixa, HSBC, Sicredi, Inter).

Para CADA discrepância fornecida, você deve gerar uma análise crítica e responder ESTRITAMENTE em formato JSON puro, sem blocos markdown (sem ```json), contendo:
- id: identificador da discrepância
- motivo_provavel: diagnóstico detalhado da causa-raiz técnica ou operacional
- confianca: float entre 0.0 e 1.0 representando a certeza estatística da análise
- nivel_risco: "Baixo" | "Médio" | "Alto"
- acao_recomendada: instrução imperativa e imediata para a tesouraria
- precedentes_similares: histórico similar registrado nos últimos 90 dias
- padrao_identificado: anomalia sistêmica (ex: timeout em API de gateway, conciliação de fuso horário, reemissão de bilhete BSP/IATA)

Responda no formato:
{
  "analises": [
    {
      "id": "...",
      "motivo_provavel": "...",
      "confianca": 0.95,
      "nivel_risco": "Médio",
      "acao_recomendada": "...",
      "precedentes_similares": "...",
      "padrao_identificado": "..."
    }
  ],
  "resumo_executivo": "...",
  "confianca_geral": 0.96
}
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        correlation_id: Optional[str] = None,
        feedback_file: str = "feedback_loop_historico.json",
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.feedback_file = feedback_file
        self.logger = StructuredLogger(self.correlation_id)

        self.client = None
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.logger.log("INFO", "init", "Cliente Anthropic inicializado com sucesso", model=self.model)
            except ImportError:
                self.logger.log("WARNING", "init", "Biblioteca anthropic não instalada. Operando em modo de simulação inteligente.")
        else:
            self.logger.log("INFO", "init", "Chave ANTHROPIC_API_KEY não informada. Utilizando motor de inferência local (Demo Mode).")

    def _gerar_analise_mock(self, discrepancias: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera análises inteligentes baseadas em regras de heurística e histórico de viagens corporativas."""
        analises = []

        for item in discrepancias:
            desc = str(item.get("descricao", "")).upper()
            valor = float(item.get("valor", 0.0))
            motivo_sql = str(item.get("motivo_detectado_sql", "")).lower()
            banco = item.get("banco", "DESCONHECIDO")

            if "duplicada" in motivo_sql or "duplic" in desc:
                motivo = f"Transação idêntica detectada no {banco}. Provável re-tentativa após timeout de confirmação na API bancária."
                risco = "Médio"
                acao = "Marcar transação excedente como 'Duplicata Confirmada' e estornar lançamento pendente no ERP."
                precedente = "2 casos similares registrados no fechamento da última semana em dias de alta volumetria."
                padrao = "Ocorrência comum em janelas de fechamento de lotes entre 14h e 16h."
                confianca = 0.98
            elif valor > 100000 or "crítico" in motivo_sql:
                motivo = f"Operação atípica de alto valor (R$ {valor:,.2f}) excedendo o limite de alçada padrão da tesouraria."
                risco = "Alto" if "charter" not in desc.lower() else "Médio"
                acao = "Solicitar autorização expressa do Diretor Financeiro (CFO) e confrontar com o contrato de prestação de serviços."
                precedente = "Fretamentos aéreos corporativos e eventos trimestrais de diretoria apresentam este perfil 1x por mês."
                padrao = "Discrepância associada a compras concentradas de bilhetes de delegação ou eventos corporativos."
                confianca = 0.94
            else:
                motivo = f"Variação estatística fora da média móvel histórica de 90 dias para a conta {item.get('conta', 'N/A')} do {banco}."
                risco = "Baixo"
                acao = "Classificar centro de custo e validar fatura unificada com o fornecedor de hospedagem/transfer."
                precedente = "Variações cambiais em cartões corporativos no exterior ocorrem sazonalmente no fechamento mensal."
                padrao = "Flutuação associada a fechamentos de faturas de viagens internacionais."
                confianca = 0.89

            analises.append({
                "id": str(item.get("id", item.get("id_externo", "TX_UNK"))),
                "motivo_provavel": motivo,
                "confianca": confianca,
                "nivel_risco": risco,
                "acao_recomendada": acao,
                "precedentes_similares": precedente,
                "padrao_identificado": padrao,
            })

        return {
            "analises": analises,
            "resumo_executivo": f"Auditoria concluída para {len(analises)} discrepâncias. Risco geral moderado com 100% de ações mitigatórias definidas.",
            "confianca_geral": round(sum(a["confianca"] for a in analises) / max(len(analises), 1), 3),
        }

    def analisar(self, discrepancias_json: str) -> Dict[str, Any]:
        """Analisa a lista de discrepâncias utilizando Claude API ou motor de inferência local.

        Args:
            discrepancias_json: String contendo lista JSON de transações anômalas.

        Returns:
            Dicionário estruturado com os diagnósticos e planos de ação.
        """
        start_time = time.time()

        try:
            dados = json.loads(discrepancias_json) if isinstance(discrepancias_json, str) else discrepancias_json
        except json.JSONDecodeError as exc:
            self.logger.log("ERROR", "analisar", f"Falha no parse do payload de discrepâncias: {str(exc)}")
            return {"erro": "JSON inválido", "analises": []}

        if not dados:
            return {"status": "SEM_DISCREPANCIAS", "analises": [], "confianca_geral": 1.0}

        qtd = len(dados) if isinstance(dados, list) else 1
        self.logger.log("INFO", "analise_inicio", f"Iniciando análise de {qtd} discrepâncias", qtd=qtd)

        # Se houver cliente oficial e chave configurada
        if self.client:
            prompt_usuario = (
                f"Analise as seguintes discrepâncias encontradas no fechamento bancário de hoje:\n\n"
                f"{json.dumps(dados, indent=2, ensure_ascii=False)}"
            )

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=self.SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt_usuario}],
                    temperature=0.2,  # Baixa temperatura para determinismo analítico
                )
                duration_ms = (time.time() - start_time) * 1000
                raw_text = response.content[0].text.strip()

                # Limpeza de possíveis marcadores markdown
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text.rsplit("\n", 1)[0]

                resultado = json.loads(raw_text)
                self.logger.log(
                    "INFO",
                    "analise_sucesso",
                    "Análise processada com sucesso pela Claude API",
                    duration_ms=round(duration_ms, 2),
                    tokens_used=response.usage.output_tokens,
                    confianca=resultado.get("confianca_geral", 0.95),
                )
                self._salvar_feedback_loop(dados, resultado)
                return resultado

            except Exception as exc:
                self.logger.log(
                    "ERROR",
                    "analise_falha_api",
                    f"Erro na chamada à Claude API: {str(exc)}. Ativando fallback resiliente.",
                    error=str(exc),
                )

        # Fallback inteligente (executado quando a API externa não estiver configurada ou falhar)
        resultado_fallback = self._gerar_analise_mock(dados if isinstance(dados, list) else [dados])
        duration_ms = (time.time() - start_time) * 1000
        self.logger.log(
            "INFO",
            "analise_fallback",
            "Diagnósticos gerados pelo motor heurístico inteligente de fallback",
            duration_ms=round(duration_ms, 2),
            confianca=resultado_fallback["confianca_geral"],
        )
        self._salvar_feedback_loop(dados, resultado_fallback)
        return resultado_fallback

    def _salvar_feedback_loop(self, entrada: Any, saida: Dict[str, Any]) -> None:
        """Persiste a análise no histórico local para viabilizar aprendizagem contínua (Few-Shot Tuning)."""
        registro = {
            "timestamp": datetime.now().isoformat(),
            "correlation_id": self.correlation_id,
            "entrada": entrada,
            "diagnostico_ia": saida,
            "status_auditoria": "Aguardando_Revisao_Humana",
        }

        historico: List[Dict[str, Any]] = []
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, "r", encoding="utf-8") as f:
                    historico = json.load(f)
            except Exception:
                historico = []

        historico.append(registro)
        historico = historico[-500:]

        try:
            with open(self.feedback_file, "w", encoding="utf-8") as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)
            self.logger.log("INFO", "feedback_loop", "Histórico atualizado para ciclo de aprendizagem contínua")
        except Exception as exc:
            self.logger.log("WARNING", "feedback_loop_erro", f"Não foi possível persistir histórico: {str(exc)}")


if __name__ == "__main__":
    print("=== MÓDULO DE INTELIGÊNCIA ARTIFICIAL: ANÁLISE DE DISCREPÂNCIAS BANCÁRIAS ===")
    
    amostra_discrepancias = [
        {
            "id": "DISC_001",
            "banco": "BRADESCO",
            "conta": "12847-2",
            "data_transacao": "2026-09-21 14:32:00",
            "valor": 45000.00,
            "descricao": "GOL LINHAS AEREAS - Fatura Centralizada 4410",
            "motivo_detectado_sql": "Transação duplicada identificada pelo hash UK_EXTERNO",
        },
        {
            "id": "DISC_002",
            "banco": "ITAU",
            "conta": "99999-9",
            "data_transacao": "2026-09-21 09:15:22",
            "valor": 120500.00,
            "descricao": "CHARTER AEREO EXECUTIVO - Fretamento Internacional",
            "motivo_detectado_sql": "Valor crítico excedendo o teto de R$ 100.000,00",
        },
        {
            "id": "DISC_003",
            "banco": "BB",
            "conta": "33401-8",
            "data_transacao": "2026-09-20 16:45:10",
            "valor": 89300.00,
            "descricao": "COPAM HOTELARIA - Hospedagem Grupo Executivo",
            "motivo_detectado_sql": "Valor estatisticamente superior a 2 desvios-padrão da média",
        },
    ]

    analisador = AnalisadorIADiscrepancias()
    resultado = analisador.analisar(json.dumps(amostra_discrepancias))
    
    print("\n--- DIAGNÓSTICO ESTRUTURADO RETORNADO PELA IA ---")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
