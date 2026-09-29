# Arquitetura de RPA: Power Automate Desktop (PAD)
## Extração de Extratos Legados via Internet Banking (OFX / CNAB 240)

**Candidato:** Diego Luiz Lino de Aquino  
**Perfil:** Desenvolvedor de Automação  
**Contexto:** Contingência para Instituições Financeiras ou Portais de Viagens sem API REST

---

### 1. Quando Utilizar Power Automate Desktop (PAD) vs Power Automate Cloud

| Critério | Power Automate Cloud (`flow.json`) | Power Automate Desktop (PAD) |
| :--- | :--- | :--- |
| **Tipo de Interface** | APIs REST, Webhooks, Bancos de Dados, Conectores M365 | Telas Web, Portais Legados, Aplicações Desktop ERP |
| **Protocolo de Conexão** | HTTPS / JSON / OAuth 2.0 | UI Automation, Seletores Web, Emulação de Teclado/Mouse |
| **Caso no Projeto** | Orquestração macro, agendamento 07:00, e-mails executivos | Download de arquivos OFX/CNAB em bancos sem Open Finance |
| **Execução** | Nuvem da Microsoft (SaaS) | Máquina Virtual (VM) dedicada ou On-Premises Gateway |

---

### 2. Fluxo Lógico do Robô de Tela (Power Automate Desktop)

```
[Início Agendado] 
       │
       ▼
1. Obter Credenciais Seguras (Windows Credential Manager / Azure Key Vault)
       │
       ▼
2. Lançar Novo Microsoft Edge (Navegação Privativa, Perfil Dedicado de Serviço)
       │
       ▼
3. Acessar Portal do Internet Banking Corporativo
       │
       ▼
4. Preencher Usuário / Certificado Digital A1 via Smart Card Emulado
       │
       ▼
5. Tratar Modal de Alerta / Avisos Operacionais com Try/Catch
       │
       ▼
6. Navegar até o Menu: "Conta Corrente > Extrato Consolidado > Exportar"
       │
       ▼
7. Selecionar Formato: OFX / CNAB 240 e Janela Temporal (D-1 a D0)
       │
       ▼
8. Baixar Arquivo para Diretório Monitorado: `C:\Integracao\Entrada\`
       │
       ▼
9. Validar Checksum e Tamanho do Arquivo (> 0 bytes)
       │
       ▼
10. Disparar Gatilho HTTP para o Motor Python / Power Automate Cloud
```

---

### 3. Tratamento de Exceções e Resiliência no PAD

1. **Seletores Web Dinâmicos:**
   - Evitar seletores absolutos com IDs gerados dinamicamente (`id="btn_198273"`).
   - Utilizar seletores CSS relativos baseados em atributos semânticos:  
     `button:contains("Exportar OFX"), a[data-action="download-cnab"]`.

2. **Mecanismo de Espera Inteligente (Smart Wait):**
   - Nunca utilizar comandos `Wait (Sleep)` fixos.
   - Utilizar ações do PAD: `Wait for web page content to contain element` com timeout máximo de 30 segundos.

3. **Gerenciamento de Falhas e Notificação de Contingência:**
   - Bloco `On Block Error` englobando todo o fluxo do banco.
   - Em caso de falha: captura de screenshot automático da tela de erro gravada em `C:\Integracao\Logs\Screenshots\` e notificação imediata via Teams/E-mail.

---

### 4. Como Defender o Domínio de Cloud e Desktop na Entrevista

> *"Se o banco disponibiliza API Open Finance ou conector direto, a melhor prática arquitetural é sempre o **Power Automate Cloud** integrado com **Python**, pois garante alta vazão, segurança e menor custo de manutenção.*  
> *Porém, se a empresa trabalhar com um banco ou portal legado de consolidadora de viagens que só opera via interface web, domino a construção do robô no **Power Automate Desktop**: estruturo a captura segura de credenciais pelo cofre do Windows, utilizo seletores web dinâmicos e disparo o download dos arquivos CNAB/OFX direto para a pasta vigiada da nossa esteira de conciliação."*
