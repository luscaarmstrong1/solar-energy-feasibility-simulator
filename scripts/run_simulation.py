from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "work" / ".mplconfig"))

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(ROOT))

from src.financial_model import cash_flow, kpis
from src.scenarios import base_financial_inputs, base_solar_inputs, compare_scenarios
from src.sensitivity import capex_tariff_heatmap, sensitivity_suite
from src.solar_model import monthly_generation


def _write_chart(monthly_df: pd.DataFrame, cashflow_df: pd.DataFrame) -> None:
    chart_dir = ROOT / "assets" / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(monthly_df["month"], monthly_df["consumption_kwh"], marker="o", label="Consumo")
    ax.plot(monthly_df["month"], monthly_df["generation_kwh"], marker="o", label="Geração FV")
    ax.set_ylabel("kWh")
    ax.set_title("Consumo x geração estimada")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(chart_dir / "monthly_consumption_generation.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(cashflow_df["year"], cashflow_df["cash_flow_brl"], label="Fluxo anual")
    ax.plot(cashflow_df["year"], cashflow_df["cumulative_cash_flow_brl"], color="#0F766E", label="Acumulado")
    ax.set_xlabel("Ano")
    ax.set_ylabel("R$")
    ax.set_title("Fluxo de caixa do projeto")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(chart_dir / "cashflow.png", dpi=160)
    plt.close(fig)


def main() -> None:
    outputs = ROOT / "outputs"
    outputs.mkdir(exist_ok=True)
    solar = base_solar_inputs()
    financial = base_financial_inputs()

    monthly_df = pd.DataFrame(monthly_generation(solar))
    cashflow_df = pd.DataFrame(cash_flow(solar, financial))
    sensitivity_df = pd.DataFrame(sensitivity_suite(solar, financial))
    heatmap_df = pd.DataFrame(capex_tariff_heatmap(solar, financial))
    scenarios_df = pd.DataFrame(compare_scenarios())
    results = kpis(solar, financial)
    portfolio_summary = {
        "nome_projeto": "Simulador de Viabilidade Técnica e Econômica de Energia Solar",
        "tipo": "Projeto de portfólio técnico",
        "idioma": "pt-BR",
        "caso": "Cliente comercial fictício",
        "horizonte_anos": solar.system_life_years,
        "premissas": {
            "tarifa_compensavel_brl_kwh": financial.tariff_compensable_brl_kwh,
            "tarifa_observacao": "Premissa sintética editável, não tarifa oficial.",
            "reajuste_tarifario": financial.tariff_escalation,
            "reajuste_observacao": "Premissa de cenário, não previsão oficial.",
            "fator_emissoes_kgco2_kwh": financial.co2_factor_kg_per_kwh,
            "fator_emissoes_observacao": "Premissa ilustrativa editável, não fonte oficial.",
        },
        "resultados": results,
        "arquivos_principais": [
            "app.py",
            "Solar_Feasibility_Simulator.xlsx",
            "outputs/results.json",
            "outputs/cashflow.csv",
            "outputs/resumo_portfolio.json",
        ],
        "competencias": [
            "Engenharia elétrica",
            "Energia solar fotovoltaica",
            "Modelagem financeira",
            "Python",
            "Streamlit",
            "Excel",
            "Análise de sensibilidade",
            "Documentação técnica",
        ],
    }

    monthly_df.to_csv(outputs / "monthly_generation.csv", index=False)
    cashflow_df.to_csv(outputs / "cashflow.csv", index=False)
    sensitivity_df.to_csv(outputs / "sensitivity.csv", index=False)
    heatmap_df.to_csv(outputs / "sensitivity_heatmap.csv", index=False)
    scenarios_df.to_csv(outputs / "scenario_comparison.csv", index=False)
    (outputs / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    (outputs / "resumo_portfolio.json").write_text(json.dumps(portfolio_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_chart(monthly_df, cashflow_df)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
