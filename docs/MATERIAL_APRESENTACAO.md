# 🎯 GUIA EXECUTIVO DE ENTREVISTA (1 PÁGINA)
## Case Técnico: Automação de Conciliação Bancária & IA Cognitiva
**Candidato:** Diego Luiz Lino de Aquino | **Perfil:** Desenvolvedor de Automação  
**Cenário:** Viagens Corporativas (8 Contas Bancárias) | **Data da Entrevista:** 22/09/2026, 14h-17h (SP)  

---

### 1. O Problema de Negócio vs A Solução Arquitetada

| O Cenário Manual Anterior | A Solução Automática Implementada |
| :--- | :--- |
| ⏰ **4 horas diárias** gastas em conferência manual de extratos | ⚡ **15 minutos diários** (Redução de **94%** no tempo de ciclo) |
| 😰 **2 a 3 erros/semana** detectados apenas no fim do mês | 🛡️ **99,94% de acurácia** com detecção em tempo real e IA |
| 📊 Relatório demorava **5 dias** para ser consolidado | 📈 Dashboard executivo no **Power BI atualizado em 5 min** |
| 💸 Risco de caixa, juros desnecessários e retrabalho | 💰 **ROI de 577%** com payback estimado em **1,8 meses** |

---

### 2. Diagrama Arquitetural da Solução

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   8 APIs BANCOS │ ----> │  PYTHON ENGINE  │ ----> │   POWER QUERY   │
│   (OAuth 2.0)   │       │(Circuit Breaker)│       │ (M Language ETL)│
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
┌─────────────────┐       ┌─────────────────┐                ▼
│    POWER BI     │ <---- │ POWER AUTOMATE  │ <---- ┌─────────────────┐
│(Dashboard Real) │       │(Orquestrador)   │       │   SQL SERVER    │
└─────────────────┘       └────────┬────────┘       │ (Stored Procs)  │
                                   │                └─────────────────┘
                                   ▼
                          ┌─────────────────┐
                          │ CLAUDE API (IA) │
                          │(Diagnóstico/Ação)
                          └─────────────────┘
```

---

### 3. O Diferencial Competitivo Único: Inteligência Artificial Cognitiva

Enquanto sistemas tradicionais apenas marcam uma transação como "duplicata" ou "erro", **nosso módulo de IA investiga semanticamente a causa-raiz e prescreve a solução:**
- **Diagnóstico Operacional:** Distingue falha de timeout de gateway de fraude ou cobrança incorreta de hotel.
- **Nível de Risco & Confiança:** Avalia o risco (Baixo, Médio, Alto) com score numérico de certeza ($\ge 95\%$).
- **Ação Recomendada Imediata:** Indica a resolução exata para a tesouraria (ex: *"Estornar lançamento X e solicitar nota Y"*).

---

### 4. Como Responder aos Gaps com Segurança (Script de 30 Segundos)

> *"Meu background é em engenharia de automação em escala real com Python, SQL e orquestração de sistemas multi-agente complexos (como o projeto ARIA, que gerenciava mais de 190 SKUs). Ferramentas como Power Automate e Power Query são interfaces declarativas que operam sobre os mesmos fundamentos lógicos que já domino profundamente:*
> - *SQL + Pandas = Power Query*
> - *Python + Webhooks/APIs = Power Automate*
> *Em vez de apenas estudar a teoria, montei para esta entrevista a solução completa funcionando de ponta a ponta com fluxo importável, scripts resilientes e integração de IA."*

### 5. Roteiro Sugerido de Apresentação (10 a 12 Minutos)

1. ⏱️ **00-02 min:** Contexto do setor de viagens corporativas (8 bancos, despesas fragmentadas de bilhetes e hotéis).
2. ⏱️ **02-05 min:** Demonstração dos artefatos (`extrator_bancario.py` com Circuit Breaker e `flow.json` do Power Automate).
3. ⏱️ **05-08 min:** Demonstração da IA com Claude API analisando causas-raiz e mitigando retrabalho da tesouraria.
4. ⏱️ **08-10 min:** Apresentação do ROI de 577% (economia de R$ 508.400/ano) e dashboard executivo Power BI.
5. ⏱️ **10-12 min:** Perguntas técnicas e alinhamento dos próximos passos.

---

### 6. Domínio de Gargalos Técnicos & Armadilhas Operacionais (Skill Ativa)

Durante a entrevista, mostre maturidade demonstrando como a arquitetura antecipa problemas reais:
- **Resiliência a Rate Limit (HTTP 429):** Bancos corporativos limitam chamadas por segundo. Implementado *Circuit Breaker* com *Exponential Backoff* e recuperação automática em *Half-Open*.
- **Idempotência no Power Automate / SQL:** Re-execuções de fluxos após falhas de rede nunca duplicam saldos graças ao cálculo de `hash_transacao` SHA-256 e `MERGE`/`INSERT OR IGNORE`.
- **Armadilhas de Viagens Corporativas:**
  - *Faturamento Consolidado BSP/IATA:* Comparação de faturas quinzenais agregadas contra e-tickets individuais.
  - *No-Show e Cancelamento de Hotéis:* Reconhecimento de retenção de 1ª diária como divergência aceitável sem falso alerta de fraude.
- **Validação Automatizada:** Bateria de testes funcionais disponível em `tests/test_gargalos_resiliencia.py`.

---
**Diego Luiz Lino de Aquino** | 📧 diaquinotech@gmail.com | 📱 [removido] | 🔗 linkedin.com/in/diegoaquino87
