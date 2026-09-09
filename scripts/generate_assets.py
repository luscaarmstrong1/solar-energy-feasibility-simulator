from __future__ import annotations

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
from src.solar_model import monthly_generation, size_system


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def architecture() -> None:
    out = ROOT / "assets" / "architecture" / "system_architecture.png"
    labels = [
        "Premissas editáveis",
        "Dimensionamento FV",
        "Geração de energia",
        "Modelo financeiro",
        "Fluxo de caixa",
        "Indicadores",
        "Excel, Streamlit e relatórios",
    ]
    fig, ax = plt.subplots(figsize=(9, 10))
    ax.axis("off")
    for idx, label in enumerate(labels):
        y = len(labels) - idx - 1
        ax.text(
            0.5,
            y,
            label,
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#1F2937",
            bbox=dict(boxstyle="round,pad=0.42", fc="#EAF6F0", ec="#0F766E", lw=1.6),
        )
        if y > 0:
            ax.annotate("", xy=(0.5, y - 0.32), xytext=(0.5, y - 0.72), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475467"))
    ax.set_title("Arquitetura do Simulador de Viabilidade Solar", fontsize=17, fontweight="bold", pad=20)
    ax.set_ylim(-0.9, len(labels) - 0.2)
    _save(fig, out)


def _kpi_panel(ax, metrics: dict[str, float | int | str | None]) -> None:
    ax.axis("off")
    lines = [
        f"Potência instalada: {metrics['installed_kwp']:.1f} kWp",
        f"Módulos: {metrics['modules']}",
        f"Geração anual: {metrics['annual_generation_kwh']:,.0f} kWh",
        f"CAPEX: R$ {metrics['capex_total_brl']:,.0f}",
        f"Payback simples: {metrics['payback_simple_years']:.1f} anos",
        f"VPL: R$ {metrics['npv_brl']:,.0f}",
        f"TIR: {metrics['irr']:.1%}",
        f"ROI acumulado em 25 anos: {metrics['roi_accumulated']:.1%}",
        f"LCOE: R$ {metrics['lcoe_brl_kwh']:.3f}/kWh",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), va="top", fontsize=12, color="#1F2937")


def screenshots() -> None:
    outdir = ROOT / "assets" / "screenshots"
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    metrics = kpis(solar, financial)
    monthly = pd.DataFrame(monthly_generation(solar))
    cash = pd.DataFrame(cash_flow(solar, financial))
    sens = pd.DataFrame(sensitivity_suite(solar, financial))
    heat = pd.DataFrame(capex_tariff_heatmap(solar, financial))
    scenarios = pd.DataFrame(compare_scenarios())
    sizing = size_system(solar)

    fig, axes = plt.subplots(1, 2, figsize=(13, 7))
    fig.suptitle("Visão Geral", fontsize=18, fontweight="bold")
    _kpi_panel(axes[0], metrics)
    axes[1].plot(monthly["month"], monthly["consumption_kwh"], marker="o", label="Consumo")
    axes[1].plot(monthly["month"], monthly["generation_kwh"], marker="o", label="Geração")
    axes[1].set_title("Consumo x geração mensal")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].legend()
    axes[1].grid(True, alpha=0.25)
    _save(fig, outdir / "01_visao_geral.png")

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axis("off")
    rows = [[k, f"{v:.3f}" if isinstance(v, float) else v] for k, v in sizing.items()]
    table = ax.table(cellText=rows, colLabels=["Indicador", "Valor"], cellLoc="left", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.5)
    ax.set_title("Dimensionamento fotovoltaico", fontsize=16, fontweight="bold")
    _save(fig, outdir / "02_dimensionamento.png")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(monthly["month"], monthly["generation_kwh"], label="Geração", color="#0F766E")
    ax.plot(monthly["month"], monthly["consumption_kwh"], marker="o", color="#1F4E78", label="Consumo")
    ax.set_title("Energia e geração")
    ax.set_ylabel("kWh")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    _save(fig, outdir / "03_energia_geracao.png")

    fig, ax = plt.subplots(figsize=(11, 6))
    _kpi_panel(ax, metrics)
    ax.set_title("Análise financeira", fontsize=16, fontweight="bold")
    _save(fig, outdir / "04_analise_financeira.png")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(cash["year"], cash["cash_flow_brl"], label="Fluxo anual", color="#1F4E78")
    ax.plot(cash["year"], cash["cumulative_cash_flow_brl"], color="#0F766E", label="Fluxo acumulado")
    ax.plot(cash["year"], cash["cumulative_discounted_cash_flow_brl"], color="#B42318", label="Fluxo descontado acumulado")
    ax.axhline(0, color="#475467", linewidth=1)
    ax.set_title("Fluxo de caixa")
    ax.set_xlabel("Ano")
    ax.set_ylabel("R$")
    ax.legend()
    _save(fig, outdir / "05_fluxo_caixa.png")

    fig, ax = plt.subplots(figsize=(12, 5))
    display = scenarios[["scenario", "installed_kwp", "annual_generation_kwh", "npv_brl", "irr", "lcoe_brl_kwh"]].copy()
    ax.axis("off")
    table = ax.table(cellText=display.round(3).values, colLabels=["Cenário", "kWp", "Geração", "VPL", "TIR", "LCOE"], cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.6)
    ax.set_title("Cenários", fontsize=16, fontweight="bold")
    _save(fig, outdir / "06_cenarios.png")

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for name, group in sens[sens["variable"].isin(["capex", "tariff", "generation"])].groupby("variable"):
        axes[0].plot(group["variation"] * 100, group["payback_simple_years"], marker="o", label=name)
    axes[0].set_title("Sensibilidade univariada")
    axes[0].set_xlabel("Variação (%)")
    axes[0].set_ylabel("Payback simples (anos)")
    axes[0].legend()
    pivot = heat.pivot(index="capex_variation", columns="tariff_variation", values="npv_brl")
    im = axes[1].imshow(pivot.values, cmap="RdYlGn")
    axes[1].set_title("Mapa CAPEX x tarifa")
    axes[1].set_xticks(range(len(pivot.columns)), [f"{v:.0%}" for v in pivot.columns])
    axes[1].set_yticks(range(len(pivot.index)), [f"{v:.0%}" for v in pivot.index])
    axes[1].set_xlabel("Variação da tarifa")
    axes[1].set_ylabel("Variação do CAPEX")
    fig.colorbar(im, ax=axes[1], fraction=0.046)
    _save(fig, outdir / "07_sensibilidade.png")

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axis("off")
    premissas = [
        ["Tarifa", "Premissa sintética editável, não oficial"],
        ["Reajuste", "Premissa de cenário, não previsão"],
        ["CO2", "Premissa ilustrativa editável"],
        ["LCOE", "CAPEX + OPEX + custos extraordinários / energia descontada"],
        ["ROI", "Economia líquida acumulada / CAPEX"],
    ]
    table = ax.table(cellText=premissas, colLabels=["Premissa", "Tratamento"], cellLoc="left", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.6)
    ax.set_title("Premissas e metodologia", fontsize=16, fontweight="bold")
    _save(fig, outdir / "08_premissas.png")


def linkedin_assets() -> None:
    outdir = ROOT / "assets" / "linkedin"
    carousel = outdir / "carrossel"
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    metrics = kpis(solar, financial)

    def card(path: Path, size: tuple[int, int], title: str, lines: list[str]) -> None:
        width, height = size
        fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor("#F8FAFC")
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0.86), 1, 0.14, color="#0F766E"))
        ax.text(0.05, 0.92, title, fontsize=28 if width > 1100 else 24, fontweight="bold", color="white", va="center")
        y = 0.72
        for line in lines:
            ax.text(0.07, y, line, fontsize=20 if width > 1100 else 18, color="#1F2937", va="top")
            y -= 0.11
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=100, facecolor="#F8FAFC")
        plt.close(fig)

    main_lines = [
        "Modelo técnico e financeiro em Python, Excel e Streamlit",
        f"{metrics['installed_kwp']:.1f} kWp simulados para cliente comercial fictício",
        f"VPL de R$ {metrics['npv_brl']:,.0f} e payback simples de {metrics['payback_simple_years']:.1f} anos",
        "Sensibilidade, cenários, LCOE e fluxo de caixa em 25 anos",
    ]
    card(outdir / "capa_projeto_linkedin.png", (1200, 627), "Simulador de Viabilidade Solar", main_lines)
    card(outdir / "projeto_linkedin_1080x1080.png", (1080, 1080), "Projeto de Portfólio", main_lines)
    slides = [
        ("01_capa.png", "Simulador de Viabilidade Solar", main_lines[:3]),
        ("02_problema.png", "Problema", ["Avaliar investimento solar exige conectar engenharia, energia e finanças.", "O projeto organiza esse raciocínio em uma ferramenta auditável."]),
        ("03_modelo.png", "Modelo", ["Dimensionamento FV, geração degradada, CAPEX, OPEX e fluxo de caixa.", "Indicadores: VPL, TIR, Payback, ROI acumulado e LCOE."]),
        ("04_resultados.png", "Resultados", [f"Potência instalada: {metrics['installed_kwp']:.1f} kWp", f"Geração anual: {metrics['annual_generation_kwh']:,.0f} kWh", f"LCOE: R$ {metrics['lcoe_brl_kwh']:.3f}/kWh"]),
        ("05_dashboard.png", "Painel", ["App Streamlit em português com oito abas.", "Entradas agrupadas, premissas explicadas e mapa CAPEX x tarifa."]),
        ("06_excel.png", "Excel", ["Pasta de trabalho com fórmulas, gráficos e abas de apoio.", "Cálculos rastreáveis para revisão técnica."]),
        ("07_tecnologias.png", "Tecnologias", ["Python, pandas, numpy-financial, Streamlit, matplotlib e openpyxl.", "Projeto pronto para GitHub e LinkedIn."]),
    ]
    for filename, title, lines in slides:
        card(carousel / filename, (1080, 1080), title, lines)


def main() -> None:
    architecture()
    screenshots()
    linkedin_assets()
    print("Assets gerados.")


if __name__ == "__main__":
    main()
