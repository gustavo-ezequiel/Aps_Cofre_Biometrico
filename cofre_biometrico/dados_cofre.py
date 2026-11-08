"""
Conteúdo do cofre: uma tabela por nível de segurança.

Este arquivo é a FONTE dos dados: a cada execução o sistema recria as três
tabelas no banco a partir daqui. Para alterar o conteúdo, edite este arquivo
(mudanças feitas direto no phpMyAdmin são sobrescritas ao reiniciar).
"""

AREAS = {
    1: {
        "tabela": "nivel1_baixa_periculosidade",
        "titulo": "NIVEL 1 - Baixa periculosidade ambiental",
        "colunas": [
            ("substancia", "VARCHAR(80)", "Substância"),
            ("onde_encontrada", "VARCHAR(120)", "Onde é encontrada"),
            ("risco_ambiental", "VARCHAR(150)", "Risco ambiental"),
        ],
        "linhas": [
            ("Bicarbonato de sódio", "Produtos domésticos", "Baixo em pequenas quantidades"),
            ("Ácido cítrico", "Alimentos e produtos de limpeza", "Baixo em soluções diluídas"),
            ("Etanol diluído", "Produtos de limpeza", "Pode afetar organismos em altas concentrações"),
            ("Cloreto de sódio", "Sal de cozinha", "Pode salinizar o solo e a água"),
            ("Carbonato de cálcio", "Rochas e produtos industriais", "Geralmente baixo"),
        ],
        "observacao": ("Substâncias de baixo risco não são necessariamente inofensivas. "
                       "Quantidade, concentração e forma de descarte fazem diferença."),
    },
    2: {
        "tabela": "nivel2_periculosidade_moderada",
        "titulo": "NIVEL 2 - Periculosidade moderada a elevada",
        "colunas": [
            ("substancia", "VARCHAR(80)", "Substância"),
            ("onde_encontrada", "VARCHAR(120)", "Onde é encontrada"),
            ("risco_ambiental", "VARCHAR(150)", "Risco ambiental"),
        ],
        "linhas": [
            ("Hipoclorito de sódio", "Desinfetantes", "Tóxico para organismos aquáticos"),
            ("Amônia", "Fertilizantes e indústrias", "Pode causar mortalidade de peixes"),
            ("Sulfato de cobre", "Agricultura e indústria", "Tóxico para organismos aquáticos"),
            ("Formaldeído", "Indústrias e laboratórios", "Tóxico e prejudicial à saúde"),
            ("Tolueno", "Solventes e tintas", "Pode contaminar o ar, a água e o solo"),
        ],
        "observacao": "",
    },
    3: {
        "tabela": "nivel3_periculosidade_extrema",
        "titulo": "NIVEL 3 - Periculosidade ambiental extrema",
        "colunas": [
            ("substancia", "VARCHAR(80)", "Substância"),
            ("perigo_ambiental", "VARCHAR(150)", "Principal perigo ambiental"),
            ("controle", "VARCHAR(150)", "Controle"),
        ],
        "linhas": [
            ("Dioxinas (ex.: TCDD)", "Persistência, bioacumulação e toxicidade elevada",
             "Controle rigoroso de emissões e resíduos"),
            ("Bifenilas policloradas (PCBs)", "Contaminação persistente de solos e águas",
             "Restrições internacionais"),
            ("Metilmercúrio", "Bioacumulação em peixes e cadeias alimentares",
             "Controle de emissões e exposição"),
            ("Tributilestanho (TBT)", "Toxicidade elevada para organismos marinhos",
             "Restrições severas de uso"),
        ],
        "observacao": "",
    },
}

# Tabelas de versões anteriores do sistema, removidas automaticamente.
TABELAS_ANTIGAS = [
    "nivel1_registro_toxinas",
    "nivel2_relatorios_incidentes",
    "nivel3_arquivos_ultrassecretos",
]
