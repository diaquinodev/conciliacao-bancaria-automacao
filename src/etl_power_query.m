// ==============================================================================
// SCRIPT M - POWER QUERY ETL: CONCILIAÇÃO BANCÁRIA CORPORATIVA
// Compatível com: Power BI Desktop / Excel Power Query (Editor Avançado)
// Autor: Diego Luiz Lino de Aquino (diaquinotech@gmail.com)
// Contexto: case técnico de automação bancária
//
// Entrada: transacoes_brutas.json gerado por extrator_bancario.py
// Contrato: id_externo, banco, conta, data_transacao, valor, descricao, tipo,
//           categoria_sugerida (opcional), data_extracao, correlation_id
// ==============================================================================

let
    // --------------------------------------------------------------------------
    // 0. PARÂMETRO DE ORIGEM
    // Ajuste para o caminho da pasta do projeto (ou transforme em Parâmetro do
    // Power BI: Página Inicial > Gerenciar Parâmetros > "CaminhoTransacoes").
    // --------------------------------------------------------------------------
    CaminhoTransacoes = "C:\case-tecnico\transacoes_brutas.json",

    // --------------------------------------------------------------------------
    // 1. EXTRAÇÃO E CARGA DE DADOS
    // --------------------------------------------------------------------------
    Origem = Json.Document(File.Contents(CaminhoTransacoes)),

    // Converte a lista raiz de objetos JSON em Tabela
    TabelaDeLista = Table.FromList(Origem, Splitter.SplitByNothing(), null, null, ExtraValues.Error),

    // Expande os registros com os mesmos nomes de campo emitidos pelo extrator Python
    ColunasExpandidas = Table.ExpandRecordColumn(
        TabelaDeLista,
        "Column1",
        {"id_externo", "banco", "conta", "data_transacao", "valor", "descricao", "tipo", "categoria_sugerida", "correlation_id"},
        {"id_externo", "banco", "conta", "data_transacao", "valor", "descricao", "tipo", "categoria_sugerida", "correlation_id"}
    ),

    // --------------------------------------------------------------------------
    // 2. OTIMIZAÇÃO DE PERFORMANCE (PREVENÇÃO DE LAZY EVALUATION)
    // O Table.Buffer armazena a tabela em memória RAM para evitar re-execuções
    // --------------------------------------------------------------------------
    TabelaBufferizada = Table.Buffer(ColunasExpandidas),

    // --------------------------------------------------------------------------
    // 3. LIMPEZA, HIGIENIZAÇÃO E REMOÇÃO DE DUPLICATAS IDEMPOTENTES
    // Mesma chave da constraint UK_EXTERNO_BANCO_CONTA do SQL Server
    // --------------------------------------------------------------------------
    DuplicatasRemovidas = Table.Distinct(TabelaBufferizada, {"id_externo", "banco", "conta"}),

    // Tipagem rigorosa dos dados para garantir integridade contábil
    // (data_transacao vem como "AAAA-MM-DD HH:MM:SS"; valor em Decimal Fixo = moeda)
    TiposCorrigidos = Table.TransformColumnTypes(DuplicatasRemovidas, {
        {"id_externo", type text},
        {"banco", type text},
        {"conta", type text},
        {"data_transacao", type datetime},
        {"valor", Currency.Type},
        {"descricao", type text},
        {"tipo", type text},
        {"categoria_sugerida", type text},
        {"correlation_id", type text}
    }, "en-US"),

    // --------------------------------------------------------------------------
    // 4. TRANSFORMAÇÃO DE REGRAS DE NEGÓCIO (VIAGENS CORPORATIVAS)
    // --------------------------------------------------------------------------
    // Padroniza textos removendo espaços excedentes
    DescricaoLimpa = Table.TransformColumns(TiposCorrigidos, {
        {"descricao", Text.Trim, type text},
        {"banco", Text.Upper, type text},
        {"tipo", each Text.Upper(Text.Trim(_)), type text}
    }),

    // Categoria financeira: usa a sugerida pelo extrator e, na ausência, aplica
    // regras heurísticas sobre o histórico bancário.
    ContemAlgum = (texto as nullable text, termos as list) as logical =>
        texto <> null and List.AnyTrue(List.Transform(termos, (t) => Text.Contains(texto, t, Comparer.OrdinalIgnoreCase))),

    CategoriaAdicionada = Table.AddColumn(DescricaoLimpa, "categoria_despesa", each
        if [categoria_sugerida] <> null and [categoria_sugerida] <> "" then [categoria_sugerida]
        else if ContemAlgum([descricao], {"TAXA", "IOF", " DU "}) then "Taxas/Serviços"
        else if ContemAlgum([descricao], {"LATAM", "GOL LINHAS", "AZUL", "BSP", "TKT", "CHARTER"}) then "Passagens Aéreas"
        else if ContemAlgum([descricao], {"HOTEL", "IBIS", "WINDSOR", "COPACABANA", "DIARIA", "DIÁRIA"}) then "Hospedagem"
        else if ContemAlgum([descricao], {"UBER", "TRANSFER", "LOCADORA", "LOCALIZA"}) then "Transfer/Transporte"
        else if ContemAlgum([descricao], {"SEGURO", "ASSIST CARD", "CHUBB"}) then "Seguros"
        else "Outros Lançamentos",
        type text
    ),

    // Sinal contábil: débitos negativos, créditos positivos.
    // O extrator emite "Débito"/"Crédito"; aceita também a grafia sem acento.
    ValorContabilAdicionado = Table.AddColumn(CategoriaAdicionada, "valor_fluxo_caixa", each
        if List.Contains({"DÉBITO", "DEBITO"}, [tipo]) then -[valor] else [valor],
        Currency.Type
    ),

    // Teto de alçada da tesouraria (mesma regra da SP_DETECTAR_DISCREPANCIAS)
    FlagAlcada = Table.AddColumn(ValorContabilAdicionado, "acima_teto_alcada", each [valor] > 100000, type logical),

    // --------------------------------------------------------------------------
    // 5. FILTRAGEM DE INTEGRIDADE
    // Elimina valores zerados ou nulos que não afetam a tesouraria
    // --------------------------------------------------------------------------
    LinhasFiltradas = Table.SelectRows(FlagAlcada, each [valor] <> null and [valor] > 0 and [data_transacao] <> null)

in
    LinhasFiltradas
