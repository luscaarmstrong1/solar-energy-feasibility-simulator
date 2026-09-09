# Exportação Opcional para Power BI

A simulação em Python grava saídas normalizadas em CSV que podem ser importadas no Power BI:

- `outputs/monthly_generation.csv`
- `outputs/cashflow.csv`
- `outputs/sensitivity.csv`
- `outputs/sensitivity_heatmap.csv`
- `outputs/scenario_comparison.csv`

Modelo sugerido:

- `Dim_Cenário`
- `Dim_Calendário`
- `Fato_GeraçãoMensal`
- `Fato_FluxoCaixa`
- `Fato_Sensibilidade`
- `Dim_Premissas`
