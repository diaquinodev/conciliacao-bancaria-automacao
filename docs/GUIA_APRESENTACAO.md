# Roteiro de demonstração

Passo a passo para mostrar o projeto funcionando (dados sintéticos).

## 1. Preparar o ambiente

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

O `.env` é opcional: sem ele, tudo roda em modo demo. Para testar o envio de e-mail, copie `.env.example` para `.env` e preencha `SMTP_EMAIL` e `SMTP_PASSWORD` (senha de app, nunca a senha da conta).

## 2. Rodar a esteira ao vivo

```bash
python src/executar_esteira_ao_vivo.py
```

O script extrai os 8 bancos (massa sintética), grava em SQLite com chave idempotente, consulta câmbio (AwesomeAPI) e Selic (BACEN SGS), mostra a decomposição por categoria e banco, regenera o painel e simula uma reexecução da carga para comprovar a idempotência.

## 3. Abrir o painel

Abra [`dashboard_demonstracao.html`](../dashboard_demonstracao.html) no navegador. Filtros por categoria, banco, período e fornecedor recalculam KPIs, gráficos e extrato.

## 4. (Opcional) E-mail

Com `SMTP_EMAIL` e `SMTP_PASSWORD` configurados, o relatório executivo é enviado para o próprio remetente. Sem essas variáveis, o envio é ignorado.

## 5. Testes

```bash
python -m unittest tests/test_extrator_bancario.py -v
python tests/test_dashboard_integridade.py
python tests/test_gargalos_resiliencia.py
python tests/test_regras_negocio.py
```
