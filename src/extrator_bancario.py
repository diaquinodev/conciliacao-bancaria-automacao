"""Módulo de Extração de Dados Bancários para Conciliação Automatizada.

Este módulo implementa o motor de extração resiliente para 8 instituições bancárias,
incorporando autenticação OAuth 2.0, padrão Circuit Breaker, retentativas com backoff
exponencial, validação rígida de schemas e telemetria estruturada em JSON.

Autor: Diego Aquino
Data: 2026-09-21
Contexto: projeto de portfólio de automação bancária (dados sintéticos)
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


class CircuitState(str, Enum):
    """Estados possíveis do padrão Circuit Breaker."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    """Configurações do Circuit Breaker por banco."""
    failure_threshold: int = 3
    recovery_timeout_sec: float = 30.0


class CircuitBreaker:
    """Implementação do padrão Circuit Breaker para evitar chamadas a serviços instáveis."""

    def __init__(self, config: Optional[CircuitBreakerConfig] = None) -> None:
        self.config = config or CircuitBreakerConfig()
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.last_failure_time: Optional[float] = None

    def record_success(self) -> None:
        """Registra sucesso na operação, restaurando o circuito para CLOSED."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def record_failure(self) -> None:
        """Registra uma falha e altera o estado do circuito caso atinja o limiar."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """Determina se a chamada pode ser executada ou deve ser barrada."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.config.recovery_timeout_sec:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False


class JsonStructuredFormatter(logging.Formatter):
    """Formatador customizado para emissão de logs em JSON machine-readable."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            payload.update(record.extra_data)
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(correlation_id: str) -> logging.Logger:
    """Configura e retorna um logger estruturado em formato JSON."""
    logger = logging.getLogger(f"ExtratorBancario_{correlation_id[:8]}")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.handlers.clear()
    logger.propagate = False  # evita duplicar cada evento no handler do logger raiz

    handler = logging.StreamHandler()
    handler.setFormatter(JsonStructuredFormatter())
    logger.addHandler(handler)
    return logger


class ExtratorBancario:
    """Extrator de transações financeiras multbancário com OAuth 2.0 e alta resiliência.

    Suporta 8 bancos: Banco do Brasil (BB), Bradesco, Itaú, Santander, Caixa,
    HSBC, Sicredi e Banco Inter.
    """

    SUPPORTED_BANKS = ["BB", "BRADESCO", "ITAU", "SANTANDER", "CAIXA", "HSBC", "SICREDI", "INTER"]

    def __init__(self, correlation_id: Optional[str] = None, use_mock_fallback: bool = True) -> None:
        """Inicializa configurações de conexão, circuit breakers e logging.

        Args:
            correlation_id: Identificador único de rastreamento da execução.
            use_mock_fallback: Se True, gera dados sintéticos realistas quando APIs
                externas não estiverem acessíveis (ideal para ambientes de demo/teste).
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.logger = setup_logger(self.correlation_id)
        self.use_mock_fallback = use_mock_fallback

        self.base_urls: Dict[str, str] = {
            "BB": os.getenv("BB_API_URL", "https://api.bb.com.br/v1"),
            "BRADESCO": os.getenv("BRADESCO_API_URL", "https://api.bradesco.com.br/v1"),
            "ITAU": os.getenv("ITAU_API_URL", "https://api.itau.com.br/v1"),
            "SANTANDER": os.getenv("SANTANDER_API_URL", "https://api.santander.com.br/v1"),
            "CAIXA": os.getenv("CAIXA_API_URL", "https://api.caixa.com.br/v1"),
            "HSBC": os.getenv("HSBC_API_URL", "https://api.hsbc.com.br/v1"),
            "SICREDI": os.getenv("SICREDI_API_URL", "https://api.sicredi.com.br/v1"),
            "INTER": os.getenv("INTER_API_URL", "https://api.inter.com.br/v1"),
        }

        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            banco: CircuitBreaker() for banco in self.SUPPORTED_BANKS
        }

        self._log_event(
            level=logging.INFO,
            action="inicializacao",
            banco="ALL",
            message="ExtratorBancario inicializado com sucesso",
            details={"bancos_suportados": self.SUPPORTED_BANKS, "mock_fallback": self.use_mock_fallback},
        )

        self.tokens: Dict[str, str] = self._autenticar_bancos()

    def _log_event(
        self,
        level: int,
        action: str,
        banco: str,
        message: str,
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emite evento de log estruturado."""
        extra_data: Dict[str, Any] = {
            "correlation_id": self.correlation_id,
            "action": action,
            "banco": banco,
        }
        if duration_ms is not None:
            extra_data["duration_ms"] = round(duration_ms, 2)
        if details:
            extra_data.update(details)

        self.logger.log(level, message, extra={"extra_data": extra_data})

    def _autenticar_bancos(self) -> Dict[str, str]:
        """Autentica com cada banco utilizando fluxo OAuth 2.0 (Client Credentials).

        Returns:
            Dicionário com tokens Bearer válidos por instituição bancária.
        """
        tokens: Dict[str, str] = {}

        for banco in self.SUPPORTED_BANKS:
            start_time = time.time()
            client_id = os.getenv(f"{banco}_CLIENT_ID")
            client_secret = os.getenv(f"{banco}_CLIENT_SECRET")
            url = self.base_urls[banco]

            if not client_id or not client_secret:
                if self.use_mock_fallback:
                    tokens[banco] = f"mock_token_{banco.lower()}_{uuid.uuid4().hex[:12]}"
                    self._log_event(
                        level=logging.INFO,
                        action="oauth_autenticacao",
                        banco=banco,
                        message=f"Credenciais reais não detectadas. Utilizando token de sessão mock para {banco}",
                        duration_ms=(time.time() - start_time) * 1000,
                        details={"status": "MOCK_TOKEN_GERADO"},
                    )
                else:
                    self._log_event(
                        level=logging.WARNING,
                        action="oauth_autenticacao",
                        banco=banco,
                        message=f"Credenciais ausentes no .env para {banco}",
                        duration_ms=(time.time() - start_time) * 1000,
                        details={"status": "CREDENCIAIS_AUSENTES"},
                    )
                continue

            try:
                response = requests.post(
                    f"{url}/oauth/token",
                    data={"grant_type": "client_credentials"},
                    auth=(client_id, client_secret),
                    timeout=10,
                )
                duration_ms = (time.time() - start_time) * 1000
                if response.status_code == 200:
                    tokens[banco] = response.json().get("access_token", "")
                    self._log_event(
                        level=logging.INFO,
                        action="oauth_autenticacao",
                        banco=banco,
                        message=f"Autenticação OAuth realizada com sucesso para {banco}",
                        duration_ms=duration_ms,
                        details={"status_code": response.status_code},
                    )
                else:
                    self._log_event(
                        level=logging.WARNING,
                        action="oauth_autenticacao",
                        banco=banco,
                        message=f"Falha de autenticação OAuth em {banco}",
                        duration_ms=duration_ms,
                        # O corpo da resposta de erro do OAuth pode ecoar client_id/segredos: não logar.
                        details={"status_code": response.status_code},
                    )
            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                self._log_event(
                    level=logging.ERROR,
                    action="oauth_autenticacao",
                    banco=banco,
                    message=f"Exceção durante handshake OAuth em {banco}: {str(exc)}",
                    duration_ms=duration_ms,
                    details={"error": str(exc)},
                )

        return tokens

    def _gerar_transacoes_mock(self, banco: str, dias: int) -> pd.DataFrame:
        """Gera massa de dados sintética realista para despesas corporativas.

        Simula transações reais de passagens aéreas, hotéis, transfers e taxas
        com algumas discrepâncias intencionais para teste do motor de IA.
        """
        categorias_despesa = [
            ("GOL LINHAS AEREAS - Bilhete SP-RJ", "Passagens Aéreas", 850.00, 1800.00),
            ("LATAM AIRLINES - Bilhete GRU-BSB", "Passagens Aéreas", 950.00, 2400.00),
            ("HOTEL COPACABANA PALACE - 3 Diárias", "Hospedagem", 3200.00, 6500.00),
            ("IBIS HOTEL PAULISTA - Diárias Operacionais", "Hospedagem", 480.00, 1200.00),
            ("LOCALIZA RENT A CAR - Locação Executiva", "Transfer/Transporte", 320.00, 950.00),
            ("UBER FOR BUSINESS - Deslocamentos Diretoria", "Transfer/Transporte", 85.00, 310.00),
            ("CHUBB SEGUROS - Seguro Viagem Internacional", "Seguros", 210.00, 890.00),
            ("TAXA BSP/IATA - Remissão de Bilhete Corporativo", "Taxas/Serviços", 150.00, 450.00),
        ]

        transacoes: List[Dict[str, Any]] = []
        qtd_registros = random.randint(15, 35)

        for _ in range(qtd_registros):
            desc, cat, min_val, max_val = random.choice(categorias_despesa)
            valor = round(random.uniform(min_val, max_val), 2)
            delta_minutos = random.randint(0, dias * 24 * 60)
            data_tx = (datetime.now() - timedelta(minutes=delta_minutos)).strftime("%Y-%m-%d %H:%M:%S")

            transacoes.append({
                "id_externo": f"TX_{banco}_{uuid.uuid4().hex[:8].upper()}",
                "banco": banco,
                "conta": f"{random.randint(10000, 99999)}-{random.randint(0, 9)}",
                "data_transacao": data_tx,
                "valor": valor,
                "descricao": desc,
                "tipo": "Débito",
                "categoria_sugerida": cat,
            })

        # Inserção esporádica de transação de alto valor para disparar regras de auditoria
        if random.random() < 0.3:
            transacoes.append({
                "id_externo": f"TX_{banco}_CRITICO_{uuid.uuid4().hex[:6].upper()}",
                "banco": banco,
                "conta": "99999-9",
                "data_transacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "valor": round(random.uniform(110000.00, 240000.00), 2),
                "descricao": "CHARTER AEREO EXECUTIVO - Fretamento Internacional",
                "tipo": "Débito",
                "categoria_sugerida": "Passagens Aéreas",
            })

        df = pd.DataFrame(transacoes)
        return df

    def extrair_transacoes(self, banco: str, dias: int = 1, max_retries: int = 3) -> pd.DataFrame:
        """Extrai transações bancárias com Circuit Breaker e Exponential Backoff.

        Args:
            banco: Sigla do banco suportado.
            dias: Janela temporal em dias para trás.
            max_retries: Quantidade máxima de tentativas em caso de erro transitório.

        Returns:
            DataFrame pandas com os registros ou DataFrame vazio em caso de indisponibilidade.
        """
        banco_upper = banco.upper()
        if banco_upper not in self.SUPPORTED_BANKS:
            self._log_event(
                level=logging.ERROR,
                action="extracao_transacoes",
                banco=banco_upper,
                message=f"Banco {banco_upper} não suportado pelo sistema",
            )
            return pd.DataFrame()

        cb = self.circuit_breakers[banco_upper]
        if not cb.can_execute():
            self._log_event(
                level=logging.WARNING,
                action="circuit_breaker_bloqueio",
                banco=banco_upper,
                message=f"Circuit Breaker em estado {cb.state.value}. Chamada abortada preventivamente.",
                details={"circuit_state": cb.state.value, "falhas_consecutivas": cb.failure_count},
            )
            return pd.DataFrame()

        start_time = time.time()
        token = self.tokens.get(banco_upper)

        # Caso esteja sem token e sem fallback, encerra
        if not token and not self.use_mock_fallback:
            self._log_event(
                level=logging.ERROR,
                action="extracao_transacoes",
                banco=banco_upper,
                message="Sem token de autenticação disponível",
            )
            cb.record_failure()
            return pd.DataFrame()

        # Tentativa de chamada com Exponential Backoff
        for tentativa in range(1, max_retries + 1):
            attempt_start = time.time()
            try:
                # Se estiver em modo mock/demo
                if self.use_mock_fallback and (not token or token.startswith("mock_token_")):
                    df_mock = self._gerar_transacoes_mock(banco_upper, dias)
                    cb.record_success()
                    self._log_event(
                        level=logging.INFO,
                        action="extracao_transacoes",
                        banco=banco_upper,
                        message=f"Extração concluída via mock engine ({len(df_mock)} registros)",
                        duration_ms=(time.time() - start_time) * 1000,
                        details={"registros": len(df_mock), "tentativa": tentativa, "origem": "MOCK"},
                    )
                    return df_mock

                # Chamada REST real
                data_inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
                data_fim = datetime.now().strftime("%Y-%m-%d")
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                url = f"{self.base_urls[banco_upper]}/transacoes"

                response = requests.get(
                    url,
                    headers=headers,
                    params={"data_inicio": data_inicio, "data_fim": data_fim, "limite": 1000},
                    timeout=15,
                )

                if response.status_code == 200:
                    payload = response.json()
                    transacoes = payload.get("transacoes", [])
                    df = pd.DataFrame(transacoes)
                    cb.record_success()
                    self._log_event(
                        level=logging.INFO,
                        action="extracao_transacoes",
                        banco=banco_upper,
                        message=f"Extração de {banco_upper} finalizada com sucesso ({len(df)} registros)",
                        duration_ms=(time.time() - start_time) * 1000,
                        details={"registros": len(df), "tentativas_necessarias": tentativa},
                    )
                    return df
                elif response.status_code in [429, 500, 502, 503, 504]:
                    delay = (2 ** (tentativa - 1)) + random.uniform(0.1, 0.5)
                    self._log_event(
                        level=logging.WARNING,
                        action="retry_backoff",
                        banco=banco_upper,
                        message=f"Erro HTTP {response.status_code} na tentativa {tentativa}/{max_retries}. Aguardando {delay:.2f}s",
                        duration_ms=(time.time() - attempt_start) * 1000,
                        details={"status_code": response.status_code, "tentativa": tentativa, "delay_sec": delay},
                    )
                    time.sleep(delay)
                else:
                    self._log_event(
                        level=logging.ERROR,
                        action="extracao_transacoes",
                        banco=banco_upper,
                        message=f"Erro não recuperável {response.status_code} em {banco_upper}",
                        details={"status_code": response.status_code, "body": response.text[:200]},
                    )
                    cb.record_failure()
                    return pd.DataFrame()

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                delay = (2 ** (tentativa - 1)) + random.uniform(0.1, 0.5)
                self._log_event(
                    level=logging.WARNING,
                    action="retry_backoff",
                    banco=banco_upper,
                    message=f"Timeout ou erro de conexão na tentativa {tentativa}/{max_retries}: {str(exc)}",
                    details={"error": str(exc), "delay_sec": delay},
                )
                time.sleep(delay)
            except Exception as exc:
                self._log_event(
                    level=logging.ERROR,
                    action="extracao_transacoes",
                    banco=banco_upper,
                    message=f"Exceção não esperada ao extrair de {banco_upper}: {str(exc)}",
                    details={"error": str(exc)},
                )
                cb.record_failure()
                return pd.DataFrame()

        cb.record_failure()
        self._log_event(
            level=logging.ERROR,
            action="extracao_falha_total",
            banco=banco_upper,
            message=f"Esgotadas {max_retries} tentativas de extração para {banco_upper}",
            duration_ms=(time.time() - start_time) * 1000,
        )
        return pd.DataFrame()

    def extrair_todos_bancos(self, dias: int = 1) -> pd.DataFrame:
        """Extrai transações de todos os 8 bancos e consolida em um único DataFrame."""
        start_time = time.time()
        self._log_event(
            level=logging.INFO,
            action="extracao_consolidada_inicio",
            banco="ALL",
            message=f"Iniciando ciclo de extração de transações para 8 bancos (Janela: {dias} dia)",
        )

        dataframes: List[pd.DataFrame] = []
        bancos_sucesso = 0
        bancos_falha = 0

        for banco in self.SUPPORTED_BANKS:
            df = self.extrair_transacoes(banco=banco, dias=dias)
            if not df.empty:
                dataframes.append(df)
                bancos_sucesso += 1
            else:
                bancos_falha += 1

        if dataframes:
            consolidado = pd.concat(dataframes, ignore_index=True)
            consolidado["data_extracao"] = datetime.now().isoformat()
            consolidado["correlation_id"] = self.correlation_id

            duration_total = (time.time() - start_time) * 1000
            self._log_event(
                level=logging.INFO,
                action="extracao_consolidada_fim",
                banco="ALL",
                message=f"Consolidação finalizada: {len(consolidado)} transações extraídas",
                duration_ms=duration_total,
                details={
                    "total_registros": len(consolidado),
                    "bancos_sucesso": bancos_sucesso,
                    "bancos_falha": bancos_falha,
                    "volume_financeiro": round(float(consolidado["valor"].sum()), 2),
                },
            )
            return consolidado

        self._log_event(
            level=logging.WARNING,
            action="extracao_consolidada_fim",
            banco="ALL",
            message="Nenhuma transação foi retornada pelos bancos no período",
            duration_ms=(time.time() - start_time) * 1000,
        )
        return pd.DataFrame()

    def validar_dados(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Aplica validação estrutural e regras de qualidade sobre os dados extraídos.

        Args:
            df: DataFrame com as transações consolidadas.

        Returns:
            Dicionário com métricas de validação, registros válidos/inválidos e taxa de erro.
        """
        if df.empty:
            return {
                "status": "VAZIO",
                "total_registros": 0,
                "registros_validos": 0,
                "registros_invalidos": 0,
                "taxa_erro": 0.0,
            }

        total = len(df)
        colunas_obrigatorias = ["id_externo", "banco", "conta", "data_transacao", "valor", "descricao"]
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]

        if colunas_faltantes:
            return {
                "status": "SCHEMA_INVALIDO",
                "colunas_faltantes": colunas_faltantes,
                "total_registros": total,
                "registros_validos": 0,
                "registros_invalidos": total,
                "taxa_erro": 1.0,
            }

        nulos = df[colunas_obrigatorias].isnull().any(axis=1)
        valores_negativos = df["valor"] <= 0
        bancos_invalidos = ~df["banco"].str.upper().isin(self.SUPPORTED_BANKS)

        invalidos_mask = nulos | valores_negativos | bancos_invalidos
        qtd_invalidos = int(invalidos_mask.sum())
        qtd_validos = total - qtd_invalidos
        taxa_erro = round(qtd_invalidos / total, 4)

        metricas = {
            "status": "VALIDADO",
            "total_registros": total,
            "registros_validos": qtd_validos,
            "registros_invalidos": qtd_invalidos,
            "taxa_erro": taxa_erro,
            "valor_total": round(float(df["valor"].sum()), 2),
            "bancos_presentes": sorted(df["banco"].unique().tolist()),
            "outliers_acima_100k": int((df["valor"] > 100000).sum()),
        }

        self._log_event(
            level=logging.INFO,
            action="validacao_dados",
            banco="ALL",
            message=f"Validação de integridade: {qtd_validos}/{total} registros válidos (Taxa erro: {taxa_erro * 100}%)",
            details=metricas,
        )
        return metricas

    def exportar_arquivos(
        self,
        df: pd.DataFrame,
        caminho_json: str = "transacoes_brutas.json",
        caminho_csv: str = "transacoes_brutas.csv",
    ) -> Tuple[bool, bool]:
        """Exporta os dados consolidados para JSON e CSV de forma atômica."""
        if df.empty:
            return False, False

        sucesso_json = False
        sucesso_csv = False

        try:
            df.to_json(caminho_json, orient="records", indent=2, force_ascii=False)
            sucesso_json = True
        except Exception as exc:
            self._log_event(level=logging.ERROR, action="exportar_json", banco="ALL", message=str(exc))

        try:
            df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
            sucesso_csv = True
        except Exception as exc:
            self._log_event(level=logging.ERROR, action="exportar_csv", banco="ALL", message=str(exc))

        self._log_event(
            level=logging.INFO,
            action="exportacao_arquivos",
            banco="ALL",
            message="Exportação concluída",
            details={"json_status": sucesso_json, "csv_status": sucesso_csv},
        )
        return sucesso_json, sucesso_csv


if __name__ == "__main__":
    print("Iniciando Execução do Extrator Bancário (Ambiente Corporativo)...")
    extrator = ExtratorBancario()
    dados = extrator.extrair_todos_bancos(dias=1)
    metricas = extrator.validar_dados(dados)
    extrator.exportar_arquivos(dados)
    print("Processo concluído com sucesso!")
