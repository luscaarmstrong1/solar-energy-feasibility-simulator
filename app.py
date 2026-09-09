from __future__ import annotations

from dataclasses import replace

import altair as alt
import pandas as pd
import streamlit as st

from src.financial_model import cash_flow, kpis
from src.scenarios import base_financial_inputs, base_solar_inputs, compare_scenarios
from src.sensitivity import capex_tariff_heatmap, sensitivity_suite
from src.solar_model import monthly_generation, size_system


st.set_page_config(page_title="Simulador de Viabilidade Solar", page_icon="☀️", layout="wide")

base_solar = base_solar_inputs()
base_financial = base_financial_inputs()


def brl(value: float | int | None) -> str:
    if value is None:
        return "n.a."
    return f"R$ {float(value):,.0f}".replace(",", ".")


def pct(value: float | int | None) -> str:
    if value is None:
        return "n.a."
    return f"{float(value) * 100:.1f}%".replace(".", ",")


def num(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "n.a."
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.title("Simulador de Viabilidade Técnica e Econômica de Energia Solar")
st.caption(
    "Dados fictícios para demonstração. Tarifa, reajuste, CAPEX, OPEX e fator de CO2 são premissas ilustrativas e editáveis."
)

with st.sidebar:
    st.header("Premissas do projeto")
    with st.expander("Perfil e consumo", expanded=True):
        profile = st.selectbox(
            "Perfil de consumo",
            ["Residencial", "Comercial", "Industrial / pequeno negócio", "Personalizado"],
            index=1,
            help="Segmento usado apenas para contextualizar o caso. Não altera regras tarifárias oficiais.",
        )
        monthly_consumption = st.number_input(
            "Consumo médio mensal (kWh)",
            100.0,
            50000.0,
            float(base_solar.monthly_consumption_kwh),
            100.0,
            help="Consumo médio mensal usado para dimensionar a potência fotovoltaica.",
        )
        avg_hsp = st.slider(
            "HSP média diária",
            3.0,
            7.0,
            4.87,
            0.1,
            help="Horas de sol pleno médias do exemplo. Substitua por fonte técnica local em uso real.",
        )
    with st.expander("Dimensionamento elétrico", expanded=True):
        module_power = st.number_input("Potência do módulo (Wp)", 300.0, 800.0, float(base_solar.module_power_wp), 10.0)
        inverter_kw = st.number_input("Potência do inversor (kW)", 1.0, 500.0, float(base_solar.inverter_kw), 1.0)
        performance_ratio = st.slider("Performance Ratio", 0.50, 0.95, base_solar.performance_ratio, 0.01)
        degradation = st.slider("Degradação anual", 0.0, 0.02, base_solar.degradation_rate, 0.001)
    with st.expander("Premissas financeiras", expanded=True):
        tariff = st.number_input(
            "Tarifa compensável (R$/kWh)",
            0.0,
            5.0,
            base_financial.tariff_compensable_brl_kwh,
            0.01,
            help="Premissa sintética. Não representa tarifa oficial nem previsão regulatória.",
        )
        capex_kwp = st.number_input("CAPEX (R$/kWp)", 1000.0, 10000.0, float(base_financial.capex_per_kwp_brl), 100.0)
        opex_pct = st.slider("OPEX anual (% do CAPEX)", 0.0, 0.05, base_financial.opex_pct_capex, 0.001)
        discount_rate = st.slider("TMA / taxa de desconto", 0.0, 0.30, base_financial.discount_rate, 0.005)
        tariff_escalation = st.slider(
            "Reajuste tarifário anual",
            0.0,
            0.15,
            base_financial.tariff_escalation,
            0.005,
            help="Premissa de cenário, não previsão oficial.",
        )
    with st.expander("Custos e emissões", expanded=False):
        include_extra = st.checkbox("Incluir substituição de inversor no ano 12", value=base_financial.include_extraordinary_costs)
        extra_cost = st.number_input("Custo extraordinário no ano 12 (R$)", 0.0, 200000.0, 25000.0, 1000.0)
        co2_factor = st.number_input(
            "Fator de emissões ilustrativo (kgCO2/kWh)",
            0.0,
            1.0,
            base_financial.co2_factor_kg_per_kwh,
            0.001,
            help="Premissa editável. Use fonte oficial e data de referência antes de citar publicamente.",
        )

solar = replace(
    base_solar,
    profile=profile,
    monthly_consumption_kwh=monthly_consumption,
    hsp_monthly=[avg_hsp] * 12,
    module_power_wp=module_power,
    inverter_kw=inverter_kw,
    performance_ratio=performance_ratio,
    degradation_rate=degradation,
)
financial = replace(
    base_financial,
    tariff_compensable_brl_kwh=tariff,
    capex_per_kwp_brl=capex_kwp,
    opex_pct_capex=opex_pct,
    discount_rate=discount_rate,
    tariff_escalation=tariff_escalation,
    co2_factor_kg_per_kwh=co2_factor,
    extraordinary_costs={12: extra_cost},
    include_extraordinary_costs=include_extra,
)

metrics = kpis(solar, financial)
monthly_df = pd.DataFrame(monthly_generation(solar))
cashflow_df = pd.DataFrame(cash_flow(solar, financial))
sensitivity_df = pd.DataFrame(sensitivity_suite(solar, financial))
heatmap_df = pd.DataFrame(capex_tariff_heatmap(solar, financial))
scenarios_df = pd.DataFrame(compare_scenarios())

tabs = st.tabs(
    [
        "Visão Geral",
        "Dimensionamento",
        "Energia e Geração",
        "Análise Financeira",
        "Fluxo de Caixa",
        "Cenários",
        "Sensibilidade",
        "Premissas e Metodologia",
    ]
)

with tabs[0]:
    cols = st.columns(6)
    cols[0].metric("Potência instalada", f"{num(metrics['installed_kwp'])} kWp")
    cols[1].metric("Módulos", f"{metrics['modules']}")
    cols[2].metric("Geração anual", f"{num(metrics['annual_generation_kwh'], 0)} kWh")
    cols[3].metric("Payback simples", f"{num(metrics['payback_simple_years'])} anos")
    cols[4].metric("VPL", brl(metrics["npv_brl"]))
    cols[5].metric("TIR", pct(metrics["irr"]))
    st.success(f"Classificação: {metrics['feasibility']}")
    st.write(
        "O resultado combina dimensionamento fotovoltaico, geração anual degradada, fluxo de caixa de 25 anos, "
        "CAPEX, OPEX, custo extraordinário, TMA e premissas sintéticas de tarifa."
    )
    chart_df = monthly_df.melt("month", value_vars=["consumption_kwh", "generation_kwh"], var_name="Série", value_name="kWh")
    chart = (
        alt.Chart(chart_df)
        .mark_line(point=True)
        .encode(x=alt.X("month:N", title="Mês", sort=None), y=alt.Y("kWh:Q", title="kWh"), color=alt.Color("Série:N", title="Série"))
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)

with tabs[1]:
    sizing = size_system(solar)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Potência recomendada", f"{num(sizing['recommended_kwp'])} kWp")
    c2.metric("Potência instalada", f"{num(sizing['installed_kwp'])} kWp")
    c3.metric("Área estimada", f"{num(sizing['area_m2'])} m²")
    c4.metric("Relação DC/AC", num(sizing["dc_ac_ratio"], 2))
    st.dataframe(pd.DataFrame([sizing]).T.rename(columns={0: "Valor"}), width="stretch")

with tabs[2]:
    st.bar_chart(monthly_df.set_index("month")[["consumption_kwh", "generation_kwh"]])
    st.dataframe(
        monthly_df.rename(
            columns={
                "month": "Mês",
                "days": "Dias",
                "consumption_kwh": "Consumo kWh",
                "hsp": "HSP",
                "generation_kwh": "Geração kWh",
                "deficit_surplus_kwh": "Déficit/Excedente kWh",
                "service_rate": "Atendimento",
            }
        ),
        width="stretch",
    )

with tabs[3]:
    cols = st.columns(5)
    cols[0].metric("CAPEX", brl(metrics["capex_total_brl"]))
    cols[1].metric("Economia líquida Ano 1", brl(metrics["year_1_savings_brl"]))
    cols[2].metric("VPL", brl(metrics["npv_brl"]))
    cols[3].metric("ROI acumulado em 25 anos", pct(metrics["roi_accumulated"]))
    cols[4].metric("LCOE", f"R$ {num(metrics['lcoe_brl_kwh'], 3)}/kWh")
    st.write("ROI acumulado em 25 anos = economia líquida acumulada do horizonte / CAPEX inicial.")
    st.write("LCOE = valor presente de CAPEX, OPEX e custos extraordinários / energia degradada descontada.")

with tabs[4]:
    flow_df = cashflow_df.melt(
        "year",
        value_vars=["cash_flow_brl", "cumulative_cash_flow_brl", "cumulative_discounted_cash_flow_brl"],
        var_name="Série",
        value_name="R$",
    )
    chart = (
        alt.Chart(flow_df)
        .mark_line(point=True)
        .encode(x=alt.X("year:O", title="Ano"), y=alt.Y("R$:Q", title="R$"), color=alt.Color("Série:N", title="Série"))
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(cashflow_df, width="stretch")

with tabs[5]:
    cols = [
        "scenario",
        "installed_kwp",
        "annual_generation_kwh",
        "capex_total_brl",
        "payback_simple_years",
        "npv_brl",
        "irr",
        "roi_accumulated",
        "lcoe_brl_kwh",
    ]
    st.dataframe(scenarios_df[cols], width="stretch")

with tabs[6]:
    st.subheader("Sensibilidade univariada")
    st.dataframe(sensitivity_df, width="stretch")
    st.subheader("Mapa de calor: CAPEX x tarifa")
    heatmap_view = heatmap_df.pivot(index="capex_variation", columns="tariff_variation", values="npv_brl")
    st.dataframe(heatmap_view.style.format("R$ {:,.0f}").background_gradient(cmap="RdYlGn"), width="stretch")

with tabs[7]:
    st.dataframe(
        pd.DataFrame(
            [
                ["Tarifa compensável", tariff, "R$/kWh", "Premissa sintética editável. Não é tarifa oficial."],
                ["Reajuste tarifário", tariff_escalation, "% ao ano", "Premissa de cenário. Não é previsão oficial."],
                ["Fator de emissões", co2_factor, "kgCO2/kWh", "Premissa ilustrativa editável. Substitua por fonte oficial para uso público."],
                ["Vida útil", solar.system_life_years, "anos", "Horizonte econômico do fluxo de caixa."],
                ["LCOE", metrics["lcoe_brl_kwh"], "R$/kWh", "Inclui CAPEX, OPEX, custos extraordinários e energia degradada descontada."],
            ],
            columns=["Premissa", "Valor", "Unidade", "Observação"],
        ),
        width="stretch",
    )
    st.write(
        "O dimensionamento usa consumo diário médio dividido por HSP e Performance Ratio. "
        "A geração mensal é estimada por potência instalada, HSP, dias do mês, Performance Ratio e disponibilidade. "
        "A viabilidade financeira usa fluxo anual, VPL, TIR, payback simples, payback descontado, ROI acumulado e LCOE."
    )
