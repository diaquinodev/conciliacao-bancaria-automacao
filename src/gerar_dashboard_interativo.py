"""
Gerador do Dashboard Executivo Interativo com Filtros de Gastos, Datas e Bancos
Compatível com exibição offline no navegador (tema corporativo)
"""

import json
import os
from collections import defaultdict

def compilar_dashboard():
    caminho_json = "transacoes_brutas.json"
    with open(caminho_json, "r", encoding="utf-8") as f:
        transacoes = json.load(f)

    # Estatísticas gerais
    total_debitos = sum(t["valor"] for t in transacoes if t.get("tipo") in ["Débito", "DEBITO", "debito"])
    total_transacoes = len(transacoes)
    ticket_medio = total_debitos / max(total_transacoes, 1)

    # Agrupamento por categoria
    categorias_map = defaultdict(lambda: {"qtd": 0, "total": 0.0})
    bancos_map = defaultdict(lambda: {"qtd": 0, "total": 0.0})

    for t in transacoes:
        cat = t.get("categoria_sugerida", "Outros")
        banco = t.get("banco", "DESCONHECIDO")
        val = float(t.get("valor", 0.0))
        categorias_map[cat]["qtd"] += 1
        categorias_map[cat]["total"] += val
        bancos_map[banco]["qtd"] += 1
        bancos_map[banco]["total"] += val

    # Escapa "<", ">" e "&" para que uma descrição vinda do banco não consiga
    # fechar a tag <script> e injetar HTML no painel (XSS armazenado).
    transacoes_js = (
        json.dumps(transacoes, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Painel Executivo de Conciliação Bancária</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg-primary: #0b1320;
      --bg-secondary: #141f32;
      --bg-card: #162238;
      --border-color: #24344d;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --brand-red: #bd1023;
      --corporate-blue: #1d4ed8;
      --corporate-teal: #0f766e;
      --status-green: #10b981;
      --status-amber: #d97706;
      --status-red: #ef4444;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
    body {{ background-color: var(--bg-primary); color: var(--text-main); padding: 24px; line-height: 1.5; }}
    .container {{ max-width: 1440px; margin: 0 auto; }}

    /* HEADER */
    .header {{
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 20px; border-bottom: 1px solid var(--border-color);
      margin-bottom: 24px; flex-wrap: wrap; gap: 16px;
    }}
    .header-brand {{ display: flex; align-items: center; gap: 12px; }}
    .brand-mark {{
      background: var(--brand-red); color: white; font-weight: 800;
      font-size: 13px; padding: 4px 8px; border-radius: 4px; letter-spacing: 0.5px;
    }}
    .header-title h1 {{
      font-size: 22px; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 10px;
    }}
    .header-title p {{ color: var(--text-muted); font-size: 13px; margin-top: 2px; }}

    .badge-status {{
      display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px;
      background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399; border-radius: 6px; font-size: 12px; font-weight: 600;
    }}
    .badge-status.alerta {{
      background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.35); color: #fca5a5;
    }}
    .badge-status.alerta::before {{ background: #ef4444; box-shadow: 0 0 8px #ef4444; }}
    .badge-status::before {{
      content: ''; width: 8px; height: 8px; background: #10b981; border-radius: 50%;
      box-shadow: 0 0 8px #10b981;
    }}

    /* BARRA DE FILTROS INTERATIVA */
    .filter-bar {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 10px; padding: 18px 20px; margin-bottom: 24px;
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px; align-items: flex-end;
    }}
    .filter-group {{ display: flex; flex-direction: column; gap: 6px; }}
    .filter-group label {{
      font-size: 11px; text-transform: uppercase; font-weight: 700;
      color: var(--text-muted); letter-spacing: 0.5px;
    }}
    .filter-control {{
      background: var(--bg-secondary); border: 1px solid var(--border-color);
      color: var(--text-main); padding: 9px 12px; border-radius: 6px;
      font-size: 13px; outline: none; transition: border-color 0.2s;
    }}
    .filter-control:focus {{ border-color: var(--corporate-blue); }}
    .filter-actions {{ display: flex; gap: 10px; align-items: flex-end; }}
    .btn {{
      padding: 9px 16px; border-radius: 6px; font-size: 13px; font-weight: 600;
      cursor: pointer; border: 1px solid transparent; transition: all 0.2s;
      display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    }}
    .btn-reset {{
      background: #1e293b; color: #cbd5e1; border-color: #334155; width: 100%;
    }}
    .btn-reset:hover {{ background: #334155; color: #ffffff; }}

    /* KPIS GRID */
    .kpi-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px; margin-bottom: 24px;
    }}
    .kpi-card {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 8px; padding: 18px 20px; position: relative; overflow: hidden;
    }}
    .kpi-card::before {{
      content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
      background: var(--corporate-blue);
    }}
    .kpi-card.red::before {{ background: var(--brand-red); }}
    .kpi-card.green::before {{ background: var(--status-green); }}
    .kpi-card.amber::before {{ background: var(--status-amber); }}

    .kpi-label {{
      font-size: 11px; font-weight: 700; text-transform: uppercase;
      color: var(--text-muted); letter-spacing: 0.5px;
    }}
    .kpi-value {{
      font-size: 26px; font-weight: 800; color: #ffffff; margin: 8px 0 4px 0;
      letter-spacing: -0.5px;
    }}
    .kpi-sub {{ font-size: 12px; color: var(--text-muted); }}

    /* CHARTS GRID */
    .charts-grid {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;
    }}
    @media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}

    .chart-card {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 8px; padding: 20px;
    }}
    .chart-header {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 10px;
    }}
    .chart-header h3 {{ font-size: 14px; font-weight: 700; color: #f1f5f9; }}
    .chart-container {{ position: relative; height: 260px; width: 100%; }}

    /* TABELA DE GASTOS DETALHADA */
    .table-card {{
      background: var(--bg-card); border: 1px solid var(--border-color);
      border-radius: 8px; padding: 20px; margin-bottom: 24px;
    }}
    .table-header {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 16px; flex-wrap: wrap; gap: 10px;
    }}
    .table-header h3 {{ font-size: 15px; font-weight: 700; color: #ffffff; }}
    .table-counter {{ font-size: 12px; color: var(--text-muted); font-weight: 500; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
    th {{
      background: #141f32; color: #94a3b8; font-weight: 600; font-size: 11px;
      text-transform: uppercase; padding: 12px 14px; border-bottom: 1px solid var(--border-color);
    }}
    td {{ padding: 12px 14px; border-bottom: 1px solid #1a2942; color: #e2e8f0; }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}

    .badge-bank {{
      padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;
      background: #1e293b; color: #93c5fd; border: 1px solid #334155;
    }}
    .badge-cat {{
      padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
      background: rgba(29, 78, 216, 0.15); color: #93c5fd; border: 1px solid rgba(29, 78, 216, 0.3);
    }}
    .badge-debito {{ color: #f87171; font-weight: 700; }}

    /* PAGINAÇÃO */
    .pagination {{
      display: flex; justify-content: space-between; align-items: center;
      margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-color);
      font-size: 12px; color: var(--text-muted);
    }}
    .pagination-btns {{ display: flex; gap: 8px; }}
    .btn-page {{
      background: #141f32; color: #e2e8f0; border: 1px solid var(--border-color);
      padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
    }}
    .btn-page:hover:not(:disabled) {{ background: #1e293b; color: white; }}
    .btn-page:disabled {{ opacity: 0.4; cursor: not-allowed; }}

    /* FOOTER */
    .footer {{
      margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border-color);
      font-size: 12px; color: var(--text-muted); display: flex;
      justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <!-- HEADER -->
    <header class="header">
      <div class="header-brand">
        <span class="brand-mark">CONCILIAÇÃO</span>
        <div class="header-title">
          <h1>Painel de Gestão e Conciliação Financeira</h1>
          <p>Esteira Automatizada de Tesouraria Multibancária &bull; Despesas Corporativas</p>
        </div>
      </div>
      <div class="badge-status" id="badge-status">Conciliação em andamento</div>
    </header>

    <!-- BARRA DE FILTROS INTERATIVA -->
    <section class="filter-bar">
      <div class="filter-group">
        <label for="filtro-categoria">Categoria do Gasto (No que gastou):</label>
        <select id="filtro-categoria" class="filter-control">
          <option value="">Todas as Categorias</option>
          <option value="Passagens Aéreas">Passagens Aéreas (LATAM, GOL, AZUL, IATA)</option>
          <option value="Hospedagem">Hospedagem (Hotéis & Diárias)</option>
          <option value="Transfer/Transporte">Locomoção & Transfer (Localiza, Uber)</option>
          <option value="Seguros">Seguros de Viagem (GTA, Assist Card)</option>
          <option value="Taxas/Serviços">Taxas Aeroportuárias, DU & IOF</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="filtro-banco">Instituição Bancária:</label>
        <select id="filtro-banco" class="filter-control">
          <option value="">Todos os 8 Bancos</option>
          <option value="BB">Banco do Brasil</option>
          <option value="BRADESCO">Bradesco Corporate</option>
          <option value="ITAU">Itaú BBA</option>
          <option value="SANTANDER">Santander Empresas</option>
          <option value="CAIXA">Caixa Econômica</option>
          <option value="INTER">Banco Inter</option>
          <option value="SICREDI">Sicredi</option>
          <option value="HSBC">HSBC Corporate</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="filtro-data-inicio">Data Inicial:</label>
        <input type="date" id="filtro-data-inicio" class="filter-control" value="2026-09-20">
      </div>

      <div class="filter-group">
        <label for="filtro-data-fim">Data Final:</label>
        <input type="date" id="filtro-data-fim" class="filter-control" value="2026-09-22">
      </div>

      <div class="filter-group">
        <label for="filtro-busca">Pesquisa Rápida (Fornecedor):</label>
        <input type="text" id="filtro-busca" class="filter-control" placeholder="Ex: Copacabana, LATAM, Uber...">
      </div>

      <div class="filter-actions">
        <button id="btn-limpar" class="btn btn-reset">↺ Limpar Filtros</button>
      </div>
    </section>

    <!-- KPIS RECALCULADOS EM TEMPO REAL -->
    <section class="kpi-grid">
      <div class="kpi-card red">
        <div class="kpi-label">Volume Total de Despesas (Filtrado)</div>
        <div class="kpi-value" id="kpi-total-gasto">R$ {total_debitos:,.2f}</div>
        <div class="kpi-sub" id="kpi-sub-total">Decomposição das 8 contas bancárias</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Lançamentos Auditados</div>
        <div class="kpi-value" id="kpi-qtd-transacoes">{total_transacoes}</div>
        <div class="kpi-sub">Idempotência garantida via SHA-256</div>
      </div>

      <div class="kpi-card green">
        <div class="kpi-label">Ticket Médio por Lançamento</div>
        <div class="kpi-value" id="kpi-ticket-medio">R$ {ticket_medio:,.2f}</div>
        <div class="kpi-sub">Alinhado à política de alçadas da tesouraria</div>
      </div>

      <div class="kpi-card amber">
        <div class="kpi-label">Maior Lançamento Filtrado</div>
        <div class="kpi-value" id="kpi-maior-gasto">R$ 0,00</div>
        <div class="kpi-sub" id="kpi-maior-desc">Nenhum outlier detectado</div>
      </div>
    </section>

    <!-- GRÁFICOS ANALÍTICOS DINÂMICOS -->
    <section class="charts-grid">
      <div class="chart-card">
        <div class="chart-header">
          <h3>No que foi gasto (Distribuição por Categoria)</h3>
          <span style="font-size: 11px; color: var(--text-muted);">Recalcula com os filtros</span>
        </div>
        <div class="chart-container">
          <canvas id="chart-categorias"></canvas>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>Onde foi gasto (Volume por Banco Comercial)</h3>
          <span style="font-size: 11px; color: var(--text-muted);">8 Contas Corporativas</span>
        </div>
        <div class="chart-container">
          <canvas id="chart-bancos"></canvas>
        </div>
      </div>
    </section>

    <!-- TABELA ANALÍTICA DETALHADA COM PAGINAÇÃO -->
    <section class="table-card">
      <div class="table-header">
        <div>
          <h3>Extrato Consolidado de Despesas (Item por Item)</h3>
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
            Exibindo os lançamentos bancários extraídos com categorização e valores auditados
          </p>
        </div>
        <div class="table-counter" id="table-counter">Mostrando 1-15 de 216 transações</div>
      </div>

      <div style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Banco</th>
              <th>Data/Hora</th>
              <th>Categoria (No que gastou)</th>
              <th>Fornecedor / Histórico</th>
              <th>Conta</th>
              <th style="text-align: right;">Valor (R$)</th>
              <th style="text-align: center;">Status</th>
            </tr>
          </thead>
          <tbody id="tabela-corpo">
            <!-- Linhas inseridas dinamicamente pelo JavaScript -->
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <span id="page-info">Página 1 de 15</span>
        <div class="pagination-btns">
          <button id="btn-prev" class="btn-page">◀ Anterior</button>
          <button id="btn-next" class="btn-page">Próxima ▶</button>
        </div>
      </div>
    </section>

    <!-- FOOTER EXECUTIVO -->
    <footer class="footer">
      <div>
        Autor: <strong>Diego Aquino</strong> &bull; Projeto de portfólio
      </div>
      <div>
        Dados sintéticos &bull; automação bancária (Python, SQL, ETL)
      </div>
    </footer>
  </div>

  <!-- JAVASCRIPT DOS FILTROS E TABELA -->
  <script>
    const DADOS_TRANSACOES = {transacoes_js};

    let dadosFiltrados = [...DADOS_TRANSACOES];
    let paginaAtual = 1;
    const ITENS_POR_PAGINA = 15;
    let chartCategoriasInstance = null;
    let chartBancosInstance = null;

    // Teto de alçada da tesouraria (mesma regra da SP_DETECTAR_DISCREPANCIAS)
    const TETO_ALCADA = 100000;

    function escaparHtml(valor) {{
      return String(valor ?? "").replace(/[&<>"']/g, c => ({{
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }}[c]));
    }}

    function statusConciliacao(t) {{
      return Number(t.valor) > TETO_ALCADA
        ? '<span style="color: #f87171; font-weight: 600; font-size: 11px;">● Discrepância</span>'
        : '<span style="color: #34d399; font-weight: 600; font-size: 11px;">● Conciliado</span>';
    }}

    function formatarMoeda(val) {{
      return "R$ " + Number(val).toLocaleString("pt-BR", {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    }}

    function aplicarFiltros() {{
      const categoria = document.getElementById("filtro-categoria").value.toLowerCase();
      const banco = document.getElementById("filtro-banco").value.toUpperCase();
      const dataInicio = document.getElementById("filtro-data-inicio").value;
      const dataFim = document.getElementById("filtro-data-fim").value;
      const busca = document.getElementById("filtro-busca").value.toLowerCase().trim();

      dadosFiltrados = DADOS_TRANSACOES.filter(t => {{
        const dt = (t.data_transacao || "").substring(0, 10);
        const cat = (t.categoria_sugerida || "").toLowerCase();
        const b = (t.banco || "").toUpperCase();
        const desc = (t.descricao || "").toLowerCase();

        if (categoria && !cat.includes(categoria)) return false;
        if (banco && b !== banco) return false;
        if (dataInicio && dt < dataInicio) return false;
        if (dataFim && dt > dataFim) return false;
        if (busca && !desc.includes(busca) && !cat.includes(busca)) return false;

        return true;
      }});

      paginaAtual = 1;
      atualizarKPIs();
      atualizarGraficos();
      renderizarTabela();
    }}

    function atualizarKPIs() {{
      const total = dadosFiltrados.reduce((acc, t) => acc + Number(t.valor || 0), 0);
      const qtd = dadosFiltrados.length;
      const medio = qtd > 0 ? total / qtd : 0;

      let maiorValor = 0;
      let maiorDesc = "Nenhum";
      dadosFiltrados.forEach(t => {{
        if (Number(t.valor) > maiorValor) {{
          maiorValor = Number(t.valor);
          maiorDesc = t.descricao;
        }}
      }});

      const qtdDiscrepancias = dadosFiltrados.filter(t => Number(t.valor) > TETO_ALCADA).length;
      const badge = document.getElementById("badge-status");
      badge.textContent = qtdDiscrepancias === 0
        ? "Operação 100% Conciliada"
        : `${{qtdDiscrepancias}} lançamento(s) acima do teto aguardando aprovação`;
      badge.classList.toggle("alerta", qtdDiscrepancias > 0);

      document.getElementById("kpi-total-gasto").textContent = formatarMoeda(total);
      document.getElementById("kpi-qtd-transacoes").textContent = qtd;
      document.getElementById("kpi-ticket-medio").textContent = formatarMoeda(medio);
      document.getElementById("kpi-maior-gasto").textContent = formatarMoeda(maiorValor);
      document.getElementById("kpi-maior-desc").textContent = maiorDesc.length > 28 ? maiorDesc.substring(0, 28) + "..." : maiorDesc;
    }}

    function renderizarTabela() {{
      const tbody = document.getElementById("tabela-corpo");
      tbody.innerHTML = "";

      const inicio = (paginaAtual - 1) * ITENS_POR_PAGINA;
      const fim = inicio + ITENS_POR_PAGINA;
      const paginaDados = dadosFiltrados.slice(inicio, fim);

      if (paginaDados.length === 0) {{
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-muted);">Nenhuma despesa encontrada para os filtros selecionados.</td></tr>`;
      }} else {{
        paginaDados.forEach(t => {{
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><span class="badge-bank">${{escaparHtml(t.banco)}}</span></td>
            <td>${{t.data_transacao ? escaparHtml(t.data_transacao.substring(0, 16)) : "N/D"}}</td>
            <td><span class="badge-cat">${{escaparHtml(t.categoria_sugerida || "Geral")}}</span></td>
            <td><strong>${{escaparHtml(t.descricao)}}</strong></td>
            <td style="color: var(--text-muted);">${{escaparHtml(t.conta)}}</td>
            <td style="text-align: right;" class="badge-debito">${{formatarMoeda(t.valor)}}</td>
            <td style="text-align: center;">${{statusConciliacao(t)}}</td>
          `;
          tbody.appendChild(tr);
        }});
      }}

      const totalPaginas = Math.ceil(dadosFiltrados.length / ITENS_POR_PAGINA) || 1;
      document.getElementById("page-info").textContent = `Página ${{paginaAtual}} de ${{totalPaginas}}`;
      document.getElementById("table-counter").textContent = `Mostrando ${{dadosFiltrados.length === 0 ? 0 : inicio + 1}}-${{Math.min(fim, dadosFiltrados.length)}} de ${{dadosFiltrados.length}} despesas auditadas`;

      document.getElementById("btn-prev").disabled = (paginaAtual <= 1);
      document.getElementById("btn-next").disabled = (paginaAtual >= totalPaginas);
    }}

    function atualizarGraficos() {{
      // Agrupa por Categoria
      const cats = {{}};
      dadosFiltrados.forEach(t => {{
        const c = t.categoria_sugerida || "Outros";
        cats[c] = (cats[c] || 0) + Number(t.valor || 0);
      }});

      // Agrupa por Banco
      const bancos = {{}};
      dadosFiltrados.forEach(t => {{
        const b = t.banco || "Outro";
        bancos[b] = (bancos[b] || 0) + Number(t.valor || 0);
      }});

      // Atualiza Chart 1 (Rosca de Categorias)
      const labelsCat = Object.keys(cats);
      const dataCat = Object.values(cats);

      if (chartCategoriasInstance) {{
        chartCategoriasInstance.data.labels = labelsCat;
        chartCategoriasInstance.data.datasets[0].data = dataCat;
        chartCategoriasInstance.update();
      }} else {{
        const ctx1 = document.getElementById("chart-categorias").getContext("2d");
        chartCategoriasInstance = new Chart(ctx1, {{
          type: "doughnut",
          data: {{
            labels: labelsCat,
            datasets: [{{
              data: dataCat,
              backgroundColor: ["#1d4ed8", "#bd1023", "#0f766e", "#d97706", "#7c3aed", "#64748b"],
              borderColor: "#162238",
              borderWidth: 2
            }}]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
              legend: {{ position: "right", labels: {{ color: "#cbd5e1", font: {{ size: 11 }} }} }}
            }}
          }}
        }});
      }}

      // Atualiza Chart 2 (Barras de Bancos)
      const labelsBanco = Object.keys(bancos);
      const dataBanco = Object.values(bancos);

      if (chartBancosInstance) {{
        chartBancosInstance.data.labels = labelsBanco;
        chartBancosInstance.data.datasets[0].data = dataBanco;
        chartBancosInstance.update();
      }} else {{
        const ctx2 = document.getElementById("chart-bancos").getContext("2d");
        chartBancosInstance = new Chart(ctx2, {{
          type: "bar",
          data: {{
            labels: labelsBanco,
            datasets: [{{
              label: "Total Gasto (R$)",
              data: dataBanco,
              backgroundColor: "#2563eb",
              borderRadius: 4
            }}]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
              x: {{ ticks: {{ color: "#94a3b8", font: {{ size: 10 }} }}, grid: {{ display: false }} }},
              y: {{ ticks: {{ color: "#94a3b8", font: {{ size: 10 }} }}, grid: {{ color: "rgba(255,255,255,0.05)" }} }}
            }}
          }}
        }});
      }}
    }}

    // EVENT LISTENERS DOS CONTROLES
    document.getElementById("filtro-categoria").addEventListener("change", aplicarFiltros);
    document.getElementById("filtro-banco").addEventListener("change", aplicarFiltros);
    document.getElementById("filtro-data-inicio").addEventListener("change", aplicarFiltros);
    document.getElementById("filtro-data-fim").addEventListener("change", aplicarFiltros);
    document.getElementById("filtro-busca").addEventListener("input", aplicarFiltros);

    document.getElementById("btn-limpar").addEventListener("click", () => {{
      document.getElementById("filtro-categoria").value = "";
      document.getElementById("filtro-banco").value = "";
      document.getElementById("filtro-data-inicio").value = "2026-09-20";
      document.getElementById("filtro-data-fim").value = "2026-09-22";
      document.getElementById("filtro-busca").value = "";
      aplicarFiltros();
    }});

    document.getElementById("btn-prev").addEventListener("click", () => {{
      if (paginaAtual > 1) {{
        paginaAtual--;
        renderizarTabela();
      }}
    }});

    document.getElementById("btn-next").addEventListener("click", () => {{
      const totalPaginas = Math.ceil(dadosFiltrados.length / ITENS_POR_PAGINA);
      if (paginaAtual < totalPaginas) {{
        paginaAtual++;
        renderizarTabela();
      }}
    }});

    // INICIALIZAÇÃO
    window.addEventListener("DOMContentLoaded", () => {{
      aplicarFiltros();
    }});
  </script>
</body>
</html>
"""

    with open("dashboard_demonstracao.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Dashboard Interativo gerado com sucesso! ({len(transacoes)} transações indexadas)")

if __name__ == "__main__":
    compilar_dashboard()
