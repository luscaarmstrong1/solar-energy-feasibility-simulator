from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, DoughnutChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.financial_model import cash_flow, kpis
from src.scenarios import base_financial_inputs, base_solar_inputs, compare_scenarios
from src.sensitivity import capex_tariff_heatmap, sensitivity_suite
from src.solar_model import MONTHS_PT, monthly_generation, size_system

OUT = ROOT / "Solar_Feasibility_Simulator.xlsx"

BLUE = "1F4E78"
GREEN = "0F766E"
LIGHT_GREEN = "DDEFE9"
YELLOW = "FFF2CC"
GRAY = "F3F6F8"
RED = "FCE4D6"
WHITE = "FFFFFF"
TEXT = "1F2937"


def style_title(ws, title: str) -> None:
    ws.sheet_view.showGridLines = False
    ws["A1"] = title
    ws["A1"].font = Font(name="Arial", size=16, bold=True, color=TEXT)
    ws["A2"] = "Dados fictícios para demonstração. Premissas ilustrativas e editáveis."
    ws["A2"].font = Font(name="Arial", size=10, italic=True, color="667085")


def header(row):
    for cell in row:
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.font = Font(name="Arial", bold=True, color=WHITE)
        cell.alignment = Alignment(horizontal="center", vertical="center")


def apply_table_style(ws, cell_range: str) -> None:
    thin = Side(style="thin", color="D0D5DD")
    for row in ws[cell_range]:
        for cell in row:
            cell.border = Border(bottom=thin)
            cell.font = Font(name="Arial", size=10, color=TEXT)
            cell.alignment = Alignment(vertical="center")


def money_fmt(cell):
    cell.number_format = '"R$"#,##0'


def percent_fmt(cell):
    cell.number_format = "0.0%"


def number_fmt(cell):
    cell.number_format = "#,##0.0"


def build() -> None:
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    metrics = kpis(solar, financial)
    monthly_rows = monthly_generation(solar)
    cash_rows = cash_flow(solar, financial)
    sensitivity_rows = sensitivity_suite(solar, financial)
    heatmap_rows = capex_tariff_heatmap(solar, financial)
    scenario_rows = compare_scenarios()
    sizing = size_system(solar)

    wb = Workbook()
    default = wb.active
    wb.remove(default)

    dash = wb.create_sheet("01_Resumo")
    inputs = wb.create_sheet("02_Entradas")
    cons = wb.create_sheet("03_Consumo")
    gen = wb.create_sheet("04_Geração")
    costs = wb.create_sheet("05_Custos")
    cf = wb.create_sheet("06_Fluxo_Caixa")
    scen = wb.create_sheet("07_Cenários")
    sens = wb.create_sheet("08_Sensibilidade")
    heatmap = wb.create_sheet("09_Mapa_CAPEX_Tarifa")
    prem = wb.create_sheet("10_Premissas")
    doc = wb.create_sheet("11_Documentação")

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False

    dash.sheet_properties.tabColor = BLUE
    inputs.sheet_properties.tabColor = GREEN

    style_title(inputs, "Entradas editáveis")
    input_rows = [
        ("Perfil", solar.profile),
        ("Estado", solar.state),
        ("Cidade", solar.city),
        ("Consumo médio mensal kWh", solar.monthly_consumption_kwh),
        ("Tarifa compensável R$/kWh", financial.tariff_compensable_brl_kwh),
        ("Potência módulo Wp", solar.module_power_wp),
        ("Área módulo m2", solar.module_area_m2),
        ("Performance Ratio", solar.performance_ratio),
        ("Inversor kW", solar.inverter_kw),
        ("Disponibilidade", solar.availability),
        ("Degradação anual", solar.degradation_rate),
        ("Vida útil anos", solar.system_life_years),
        ("CAPEX R$/kWp", financial.capex_per_kwp_brl),
        ("OPEX % CAPEX", financial.opex_pct_capex),
        ("Reajuste tarifário anual", financial.tariff_escalation),
        ("TMA", financial.discount_rate),
        ("Fator CO2 kg/kWh", financial.co2_factor_kg_per_kwh),
        ("Substituição inversor ativa", "Sim" if financial.include_extraordinary_costs else "Não"),
        ("Ano substituição", 12),
        ("Custo substituição R$", 25000),
    ]
    inputs.append([])
    inputs.append(["Campo", "Valor", "Unidade/nota"])
    header(inputs[4])
    for label, value in input_rows:
        inputs.append([label, value, "Premissa editavel"])
    for row in range(5, 25):
        inputs[f"B{row}"].fill = PatternFill("solid", fgColor=YELLOW)
        inputs[f"B{row}"].font = Font(name="Arial", color="0000FF")
    for addr in ["B12", "B14", "B15", "B16", "B17", "B20"]:
        percent_fmt(inputs[addr])
    money_fmt(inputs["B9"])
    money_fmt(inputs["B17"])
    money_fmt(inputs["B24"])
    dv = DataValidation(type="list", formula1='"Residencial,Comercial,Industrial / pequeno negócio,Personalizado"')
    inputs.add_data_validation(dv)
    dv.add(inputs["B5"])
    apply_table_style(inputs, "A4:C24")
    inputs.freeze_panes = "A5"

    style_title(cons, "Consumo")
    cons.append([])
    cons.append(["Mes", "Consumo kWh"])
    header(cons[4])
    for i, row in enumerate(monthly_rows, start=5):
        cons.append([row["month"], row["consumption_kwh"]])
        cons[f"B{i}"] = "=02_Entradas!$B$8"
    apply_table_style(cons, "A4:B16")
    cons.freeze_panes = "A5"

    style_title(gen, "Geração")
    gen.append([])
    gen.append(["Mês", "Dias", "Consumo kWh", "HSP", "Geração kWh", "Déficit/Excedente kWh", "Atendimento"])
    header(gen[4])
    for i, row in enumerate(monthly_rows, start=5):
        gen.append([row["month"], row["days"], None, row["hsp"], None, None, None])
        gen[f"C{i}"] = f"=03_Consumo!B{i}"
        gen[f"E{i}"] = f"=$J$5*D{i}*B{i}*02_Entradas!$B$12*02_Entradas!$B$13"
        gen[f"F{i}"] = f"=E{i}-C{i}"
        gen[f"G{i}"] = f"=MIN(E{i}/C{i},1)"
    gen["I4"] = "Indicador"
    gen["J4"] = "Valor"
    header(gen["I4:J4"][0])
    gen["I5"] = "Potência instalada kWp"
    gen["J5"] = "=CEILING(((02_Entradas!$B$8*12/365)/(AVERAGE(D5:D16)*02_Entradas!$B$12))/(02_Entradas!$B$10/1000),1)*(02_Entradas!$B$10/1000)"
    gen["I6"] = "Módulos"
    gen["J6"] = "=J5/(02_Entradas!$B$10/1000)"
    gen["I7"] = "Área m2"
    gen["J7"] = "=J6*02_Entradas!$B$11"
    gen["I8"] = "DC/AC"
    gen["J8"] = "=J5/02_Entradas!$B$13"
    for row in range(5, 17):
        number_fmt(gen[f"E{row}"])
        percent_fmt(gen[f"G{row}"])
    apply_table_style(gen, "A4:G16")
    apply_table_style(gen, "I4:J8")
    gen.conditional_formatting.add("F5:F16", CellIsRule(operator="lessThan", formula=["0"], fill=PatternFill("solid", fgColor=RED)))

    style_title(costs, "Custos")
    costs.append([])
    costs.append(["Item", "Valor", "Nota"])
    header(costs[4])
    cost_rows = [
        ("CAPEX total", "=04_Geração!J5*02_Entradas!$B$17", "Instalado kWp x R$/kWp"),
        ("CAPEX R$/kWp", "=02_Entradas!$B$17", "Premissa"),
        ("OPEX anual", "=B5*02_Entradas!$B$18", "Percentual do CAPEX"),
        ("Substituição inversor", "=IF(02_Entradas!$B$22=\"Sim\",02_Entradas!$B$24,0)", "Evento opcional"),
    ]
    for row in cost_rows:
        costs.append(row)
    for row in range(5, 9):
        money_fmt(costs[f"B{row}"])
    apply_table_style(costs, "A4:C8")

    style_title(cf, "Fluxo de Caixa")
    cf.append([])
    cf.append(
        [
            "Ano",
            "Geração kWh",
            "Tarifa R$/kWh",
            "Economia bruta",
            "OPEX",
            "Custos extraordinários",
            "Economia líquida",
            "Fluxo de caixa",
            "Fluxo acumulado",
            "Fator desconto",
            "Fluxo descontado",
            "Fluxo descontado acumulado",
        ]
    )
    header(cf[4])
    for i, row in enumerate(range(0, solar.system_life_years + 1), start=5):
        cf[f"A{i}"] = row
        if row == 0:
            formulas = [0, "=02_Entradas!$B$9", 0, 0, 0, 0, "=-05_Custos!$B$5", "=-05_Custos!$B$5", 1, "=-05_Custos!$B$5", "=-05_Custos!$B$5"]
        else:
            formulas = [
                f"=SUM(04_Geração!$E$5:$E$16)*(1-02_Entradas!$B$14)^(A{i}-1)",
                f"=02_Entradas!$B$9*(1+02_Entradas!$B$19)^(A{i}-1)",
                f"=B{i}*C{i}",
                "=05_Custos!$B$7",
                f"=IF(A{i}=02_Entradas!$B$23,05_Custos!$B$8,0)",
                f"=D{i}-E{i}-F{i}",
                f"=G{i}",
                f"=H{i}+I{i-1}",
                f"=1/(1+02_Entradas!$B$20)^A{i}",
                f"=H{i}*J{i}",
                f"=K{i}+L{i-1}",
            ]
        for col, value in enumerate(formulas, start=2):
            cf.cell(i, col).value = value
    for row in range(5, 31):
        for col in [4, 5, 6, 7, 8, 9, 11, 12]:
            money_fmt(cf.cell(row, col))
        percent_fmt(cf.cell(row, 10))
    apply_table_style(cf, "A4:L30")
    cf.freeze_panes = "A5"

    style_title(scen, "Cenários")
    scen.append([])
    keys = ["scenario", "installed_kwp", "annual_generation_kwh", "capex_total_brl", "year_1_savings_brl", "payback_simple_years", "npv_brl", "irr", "lcoe_brl_kwh", "total_net_savings_brl"]
    labels = ["Cenário", "Potência kWp", "Geração anual", "CAPEX", "Economia Ano 1", "Payback", "VPL", "TIR", "LCOE", "Economia total"]
    scen.append(labels)
    header(scen[4])
    for row in scenario_rows:
        scen.append([row[k] for k in keys])
    apply_table_style(scen, "A4:J7")
    for row in range(5, 8):
        money_fmt(scen[f"D{row}"])
        money_fmt(scen[f"E{row}"])
        money_fmt(scen[f"G{row}"])
        money_fmt(scen[f"J{row}"])
        percent_fmt(scen[f"H{row}"])

    style_title(sens, "Sensibilidade")
    sens.append([])
    sens.append(["Variável", "Variação", "Payback", "Payback descontado", "VPL", "TIR", "LCOE", "ROI acumulado"])
    header(sens[4])
    for row in sensitivity_rows:
        sens.append([
            row["variable"],
            row["variation"],
            row["payback_simple_years"],
            row["payback_discounted_years"],
            row["npv_brl"],
            row["irr"],
            row["lcoe_brl_kwh"],
            row["roi_accumulated"],
        ])
    apply_table_style(sens, "A4:H34")
    for row in range(5, 35):
        percent_fmt(sens[f"B{row}"])
        money_fmt(sens[f"E{row}"])
        percent_fmt(sens[f"F{row}"])
        percent_fmt(sens[f"H{row}"])

    style_title(heatmap, "Mapa de calor: CAPEX x tarifa")
    heatmap.append([])
    heatmap.append(["Variação CAPEX", "Variação tarifa", "Payback simples", "VPL", "TIR", "ROI acumulado", "Classificação"])
    header(heatmap[4])
    for row in heatmap_rows:
        heatmap.append([
            row["capex_variation"],
            row["tariff_variation"],
            row["payback_simple_years"],
            row["npv_brl"],
            row["irr"],
            row["roi_accumulated"],
            row["feasibility"],
        ])
    apply_table_style(heatmap, "A4:G29")
    for row in range(5, 30):
        percent_fmt(heatmap[f"A{row}"])
        percent_fmt(heatmap[f"B{row}"])
        money_fmt(heatmap[f"D{row}"])
        percent_fmt(heatmap[f"E{row}"])
        percent_fmt(heatmap[f"F{row}"])

    style_title(prem, "Premissas")
    prem.append([])
    prem.append(["Premissa", "Valor padrao", "Unidade", "Fonte", "Editavel", "Descricao"])
    header(prem[4])
    assumptions = [
        ("Consumo", 4500, "kWh/mês", "Sintético", "Sim", "Cliente comercial fictício."),
        ("Tarifa", 0.95, "R$/kWh", "Premissa sintética", "Sim", "Tarifa compensável configurável. Não é tarifa oficial."),
        ("HSP", 4.87, "h/dia", "Premissa ilustrativa", "Sim", "Média do exemplo."),
        ("Performance Ratio", 0.80, "%", "Premissa técnica", "Sim", "Eficiência global."),
        ("CAPEX", 4200, "R$/kWp", "Premissa ilustrativa", "Sim", "Investimento por kWp."),
        ("OPEX", 0.012, "% CAPEX", "Premissa ilustrativa", "Sim", "Custos anuais."),
        ("CO2", 0.0385, "kg/kWh", "Premissa ilustrativa", "Sim", "Substituir por fonte oficial se usado publicamente."),
    ]
    for row in assumptions:
        prem.append(row)
    apply_table_style(prem, "A4:F11")

    style_title(doc, "Documentação")
    docs = [
        ("Objetivo", "Avaliar viabilidade técnica e financeira de sistema fotovoltaico."),
        ("Limitação", "Modelo simplificado. Não substitui projeto executivo, estudo de conexão ou análise tarifária específica."),
        ("Fórmula FV", "Potência kWp = consumo diário / (HSP x PR)."),
        ("Payback", "Calculado por fluxo acumulado, com interpolação anual."),
        ("VPL", "Soma dos fluxos descontados pela TMA."),
        ("TIR", "Taxa que zera o VPL do fluxo de caixa."),
        ("ROI", "ROI acumulado em 25 anos = economia líquida acumulada / CAPEX."),
        ("LCOE", "Valor presente de CAPEX, OPEX e custos extraordinários dividido pela energia degradada descontada."),
    ]
    doc.append([])
    doc.append(["Topico", "Descricao"])
    header(doc[4])
    for row in docs:
        doc.append(row)
    apply_table_style(doc, "A4:B12")
    doc.column_dimensions["B"].width = 90

    style_title(dash, "Simulador de Viabilidade Técnica e Econômica de Energia Solar")
    dashboard_kpis = [
        ("Potência instalada", "=04_Geração!J5", "kWp"),
        ("Módulos", "=04_Geração!J6", "un"),
        ("Geração anual", "=SUM(04_Geração!E5:E16)", "kWh"),
        ("Economia Ano 1", "=06_Fluxo_Caixa!G6", "R$"),
        ("CAPEX", "=05_Custos!B5", "R$"),
        ("Payback simples", '=MATCH(TRUE,06_Fluxo_Caixa!I5:I30>=0,0)-2+(ABS(INDEX(06_Fluxo_Caixa!I5:I30,MATCH(TRUE,06_Fluxo_Caixa!I5:I30>=0,0)-1))/(INDEX(06_Fluxo_Caixa!I5:I30,MATCH(TRUE,06_Fluxo_Caixa!I5:I30>=0,0))-INDEX(06_Fluxo_Caixa!I5:I30,MATCH(TRUE,06_Fluxo_Caixa!I5:I30>=0,0)-1)))', "anos"),
        ("Payback descontado", '=MATCH(TRUE,06_Fluxo_Caixa!L5:L30>=0,0)-2+(ABS(INDEX(06_Fluxo_Caixa!L5:L30,MATCH(TRUE,06_Fluxo_Caixa!L5:L30>=0,0)-1))/(INDEX(06_Fluxo_Caixa!L5:L30,MATCH(TRUE,06_Fluxo_Caixa!L5:L30>=0,0))-INDEX(06_Fluxo_Caixa!L5:L30,MATCH(TRUE,06_Fluxo_Caixa!L5:L30>=0,0)-1)))', "anos"),
        ("VPL", "=SUM(06_Fluxo_Caixa!K5:K30)", "R$"),
        ("TIR", "=IRR(06_Fluxo_Caixa!H5:H30)", "%"),
        ("ROI acumulado em 25 anos", "=SUM(06_Fluxo_Caixa!G6:G30)/ABS(06_Fluxo_Caixa!H5)", "%"),
        ("LCOE", "=((05_Custos!B5)+SUMPRODUCT(06_Fluxo_Caixa!E6:E30+06_Fluxo_Caixa!F6:F30,06_Fluxo_Caixa!J6:J30))/SUMPRODUCT(06_Fluxo_Caixa!B6:B30,06_Fluxo_Caixa!J6:J30)", "R$/kWh"),
        ("CO2 evitado vida útil", "=SUM(06_Fluxo_Caixa!B6:B30)*02_Entradas!B21/1000", "tCO2e"),
        ("Resultado", '=IF(AND(B12>0,B13>02_Entradas!B20),"Atrativo",IF(OR(B12>0,B13>02_Entradas!B20),"Moderado","Pouco atrativo"))', ""),
    ]
    dash.append([])
    dash.append(["Indicador", "Valor", "Unidade"])
    header(dash[4])
    for row in dashboard_kpis:
        dash.append(row)
    apply_table_style(dash, "A4:C17")
    for row in [8, 11, 12]:
        money_fmt(dash[f"B{row}"])
    for row in [13, 14]:
        percent_fmt(dash[f"B{row}"])
    number_fmt(dash["B5"])
    number_fmt(dash["B7"])
    dash["E4"] = "Resumo"
    dash["E5"] = "Critério: Atrativo quando VPL > 0 e TIR > TMA."
    dash["E6"] = "Tarifa, irradiação, CAPEX e CO2 são premissas configuráveis."
    dash["E4"].font = Font(name="Arial", size=12, bold=True, color=TEXT)

    chart1 = LineChart()
    chart1.title = "Consumo x geração mensal"
    chart1.y_axis.title = "kWh"
    chart1.x_axis.title = "Mês"
    data = Reference(gen, min_col=3, max_col=5, min_row=4, max_row=16)
    cats = Reference(gen, min_col=1, min_row=5, max_row=16)
    chart1.add_data(data, titles_from_data=True)
    chart1.set_categories(cats)
    chart1.height = 7
    chart1.width = 14
    dash.add_chart(chart1, "E8")

    chart2 = BarChart()
    chart2.title = "Fluxo de caixa anual"
    chart2.y_axis.title = "R$"
    chart2.x_axis.title = "Ano"
    data = Reference(cf, min_col=8, max_col=9, min_row=4, max_row=30)
    cats = Reference(cf, min_col=1, min_row=5, max_row=30)
    chart2.add_data(data, titles_from_data=True)
    chart2.set_categories(cats)
    chart2.height = 7
    chart2.width = 14
    dash.add_chart(chart2, "E23")

    chart3 = DoughnutChart()
    chart3.title = "Composição de custos"
    data = Reference(costs, min_col=2, min_row=5, max_row=8)
    cats = Reference(costs, min_col=1, min_row=5, max_row=8)
    chart3.add_data(data, titles_from_data=False)
    chart3.set_categories(cats)
    chart3.height = 7
    chart3.width = 11
    dash.add_chart(chart3, "A20")

    for ws in wb.worksheets:
        for col in range(1, min(ws.max_column, 12) + 1):
            ws.column_dimensions[chr(64 + col)].width = 18
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="center", wrap_text=False)

    wb.save(OUT)
    loaded = load_workbook(OUT, data_only=False)
    formula_errors = []
    for ws in loaded.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and any(err in cell.value for err in ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?"]):
                    formula_errors.append(f"{ws.title}!{cell.coordinate}:{cell.value}")
    if formula_errors:
        raise RuntimeError("\n".join(formula_errors))
    print(f"Excel created: {OUT}")


if __name__ == "__main__":
    build()
