// ==============================================================================
// SCRIPT M - POWER QUERY ETL: CONCILIAÇÃO BANCÁRIA CORPORATIVA
// Compatível com: Power BI Desktop / Excel Power Query (Editor Avançado)
// Autor: Diego Luiz Lino de Aquino (diaquinotech@gmail.com)
// Contexto: Processo Seletivo - Desenvolvedor de Automação
// ==============================================================================

let
    // --------------------------------------------------------------------------
    // 1. EXTRAÇÃO E CARGA DE DADOS
    // Conecta à saída consolidada do motor Python ou Staging SQL Server
    // --------------------------------------------------------------------------
    Origem = Json.Document(File.Contents("C:\Users\dayan\Downloads\case-tecnico\transacoes_brutas.json")),
    
    // Converte a lista raiz de objetos JSON em Tabela
    TabelaDeLista = Table.FromList(Origem, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    
    // Expande os registros estruturados para colunas individuais
    ColunasExpandidas = Table.ExpandRecordColumn(
        TabelaDeLista, 
        "Column1", 
        {"id_transacao", "banco", "agencia", "conta", "data_movimentacao", "valor", "tipo_operacao", "descricao_historico", "numero_documento"}, 
        {"id_transacao", "banco", "agencia", "conta", "data_movimentacao", "valor", "tipo_operacao", "descricao_historico", "numero_documento"}
    ),

    // --------------------------------------------------------------------------
    // 2. OTIMIZAÇÃO DE PERFORMANCE (PREVENÇÃO DE LAZY EVALUATION)
    // O Table.Buffer armazena a tabela em memória RAM para evitar re-execuções
    // --------------------------------------------------------------------------
    TabelaBufferizada = Table.Buffer(ColunasExpandidas),

    // --------------------------------------------------------------------------
    // 3. LIMPEZA, HIGIENIZAÇÃO E REMOÇÃO DE DUPLICATAS IDEMPOTENTES
    // --------------------------------------------------------------------------
    DuplicatasRemovidas = Table.Distinct(TabelaBufferizada, {"id_transacao"}),

    // Tipagem rigorosa dos dados para garantir integridade contábil
    TiposCorrigidos = Table.TransformColumnTypes(DuplicatasRemovidas, {
        {"id_transacao", type text},
        {"banco", type text},
        {"agencia", type text},
        {"conta", type text},
        {"data_movimentacao", type date},
        {"valor", type number},
        {"tipo_operacao", type text},
        {"descricao_historico", type text},
        {"numero_documento", type text}
    }),

    // --------------------------------------------------------------------------
    // 4. TRANSFORMAÇÃO DE REGRAS DE NEGÓCIO (VIAGENS CORPORATIVAS)
    // --------------------------------------------------------------------------
    // Padroniza a descrição removendo espaços excedentes e caracteres invisíveis
    DescricaoLimpa = Table.TransformColumns(TiposCorrigidos, {
        {"descricao_historico", Text.Trim, type text},
        {"banco", Text.Upper, type text}
    }),

    // Criação de Categoria Financeira a partir do histórico (Regras Heurísticas)
    CategoriaAdicionada = Table.AddColumn(DescricaoLimpa, "categoria_despesa", each 
        if Text.Contains([descricao_historico], "LATAM", Comparer.OrdinalIgnoreCase) or 
           Text.Contains([descricao_historico], "GOL", Comparer.OrdinalIgnoreCase) or 
           Text.Contains([descricao_historico], "AZUL", Comparer.OrdinalIgnoreCase) or 
           Text.Contains([descricao_historico], "BSP", Comparer.OrdinalIgnoreCase) or
           Text.Contains([descricao_historico], "TKT", Comparer.OrdinalIgnoreCase) then "Aéreo / Bilhetes"
        else if Text.Contains([descricao_historico], "HOTEL", Comparer.OrdinalIgnoreCase) or 
                Text.Contains([descricao_historico], "IBIS", Comparer.OrdinalIgnoreCase) or 
                Text.Contains([descricao_historico], "WINDSOR", Comparer.OrdinalIgnoreCase) or 
                Text.Contains([descricao_historico], "COPACABANA", Comparer.OrdinalIgnoreCase) then "Hospedagem"
        else if Text.Contains([descricao_historico], "UBER", Comparer.OrdinalIgnoreCase) or 
                Text.Contains([descricao_historico], "TRANSFER", Comparer.OrdinalIgnoreCase) or 
                Text.Contains([descricao_historico], "LOCADORA", Comparer.OrdinalIgnoreCase) or
                Text.Contains([descricao_historico], "LOCALIZA", Comparer.OrdinalIgnoreCase) then "Locomoção / Transfer"
        else if Text.Contains([descricao_historico], "TAXA", Comparer.OrdinalIgnoreCase) or 
                Text.Contains([descricao_historico], "DU", Comparer.OrdinalIgnoreCase) or
                Text.Contains([descricao_historico], "IOF", Comparer.OrdinalIgnoreCase) then "Taxas & Encargos"
        else "Outros Lançamentos",
        type text
    ),

    // Criação de Sinal Contábil (Créditos positivos, Débitos negativos)
    ValorContabilAdicionado = Table.AddColumn(CategoriaAdicionada, "valor_fluxo_caixa", each 
        if [tipo_operacao] = "DEBITO" then -[valor] else [valor],
        type number
    ),

    // --------------------------------------------------------------------------
    // 5. FILTRAGEM DE INTEGRIDADE
    // Elimina valores zerados ou nulos que não afetam a tesouraria
    // --------------------------------------------------------------------------
    LinhasFiltradas = Table.SelectRows(ValorContabilAdicionado, each [valor] > 0 and [data_movimentacao] <> null)

in
    LinhasFiltradas
