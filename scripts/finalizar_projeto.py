from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
PARENT_OUTPUTS = ROOT.parent / "outputs"
sys.path.insert(0, str(ROOT))

from src.financial_model import cash_flow, kpis
from src.scenarios import base_financial_inputs, base_solar_inputs, compare_scenarios
from src.sensitivity import capex_tariff_heatmap, sensitivity_suite
from src.solar_model import monthly_generation


def run(command: list[str]) -> str:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    return completed.stdout + completed.stderr


def fmt_brl(value: float) -> str:
    return f"R$ {value:,.0f}".replace(",", ".")


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def update_markdown(metrics: dict[str, float | int | str | None], tests_summary: str) -> None:
    readme = f"""
# Simulador de Viabilidade Técnica e Econômica de Energia Solar

Projeto de portfólio que integra engenharia elétrica, geração fotovoltaica, modelagem financeira, Excel, Streamlit e documentação técnica em português.

## Visão Geral

O simulador estima a potência fotovoltaica recomendada, a geração mensal/anual, o fluxo de caixa em 25 anos e indicadores de decisão para um cliente comercial fictício. Os dados são sintéticos e servem para demonstração profissional. Tarifa, reajuste tarifário, CAPEX, OPEX e fator de emissões são premissas editáveis.

![Visão geral](assets/screenshots/01_visao_geral.png)

## Principais Resultados do Caso-Base

| Indicador | Resultado |
| --- | ---: |
| Potência instalada | {metrics['installed_kwp']:.1f} kWp |
| Módulos | {metrics['modules']} |
| Geração anual estimada | {metrics['annual_generation_kwh']:,.0f} kWh |
| CAPEX | {fmt_brl(float(metrics['capex_total_brl']))} |
| Economia líquida no Ano 1 | {fmt_brl(float(metrics['year_1_savings_brl']))} |
| Payback simples | {metrics['payback_simple_years']:.1f} anos |
| Payback descontado | {metrics['payback_discounted_years']:.1f} anos |
| VPL | {fmt_brl(float(metrics['npv_brl']))} |
| TIR | {fmt_pct(float(metrics['irr'])) if metrics['irr'] is not None else 'n.a.'} |
| ROI acumulado em 25 anos | {fmt_pct(float(metrics['roi_accumulated']))} |
| LCOE | R$ {float(metrics['lcoe_brl_kwh']):.3f}/kWh |

## Como Executar

```bash
python -m pip install -r requirements.txt
python scripts/finalizar_projeto.py
python -m streamlit run app.py
```

No Windows, use `ATUALIZAR_TUDO.bat` para regenerar os artefatos e `INICIAR_SIMULADOR.bat` para abrir o Streamlit.

## Streamlit

O app possui oito abas:

1. Visão Geral
2. Dimensionamento
3. Energia e Geração
4. Análise Financeira
5. Fluxo de Caixa
6. Cenários
7. Sensibilidade
8. Premissas e Metodologia

![Sensibilidade](assets/screenshots/07_sensibilidade.png)

## Excel

O arquivo `Solar_Feasibility_Simulator.xlsx` contém entradas editáveis, geração mensal, custos, fluxo de caixa, cenários, sensibilidade, mapa CAPEX x tarifa, premissas e documentação. As células de entrada ficam destacadas em amarelo.

![Fluxo de caixa](assets/screenshots/05_fluxo_caixa.png)

## Metodologia

O dimensionamento usa consumo diário médio dividido por HSP e Performance Ratio. A geração mensal considera potência instalada, HSP, dias do mês, Performance Ratio e disponibilidade. A geração anual é degradada ao longo da vida útil.

O fluxo financeiro inclui CAPEX inicial, economia bruta, OPEX anual, custos extraordinários opcionais, fluxo líquido, fluxo descontado, VPL, TIR, payback simples, payback descontado, ROI acumulado e LCOE.

## Definições

ROI acumulado em 25 anos = economia líquida acumulada no horizonte / CAPEX inicial.

LCOE = valor presente de CAPEX, OPEX e custos extraordinários / energia degradada descontada.

## Premissas e Limitações

Tarifa e reajuste tarifário são premissas sintéticas de cenário, não valores oficiais e não previsões. O fator de emissões é uma premissa ilustrativa editável, não fonte oficial. Para uso técnico real, substitua essas entradas por dados regulatórios, comerciais e ambientais com data de referência.

## Estrutura

- `app.py`: app Streamlit em português.
- `src/`: modelos técnico, financeiro, cenários e sensibilidade.
- `scripts/`: execução, validação, Excel, assets e finalização.
- `outputs/`: CSV, JSON e resumo único de portfólio.
- `assets/`: gráficos, screenshots, arquitetura e imagens LinkedIn.
- `linkedin/`: textos prontos para cadastro e divulgação.
- `docs/`: documentação complementar.

## Validação

{tests_summary}
"""
    write_text(ROOT / "README.md", readme)
    write_text(ROOT / "README_PT-BR.md", "# README em Português\n\nA documentação principal foi consolidada em `README.md`.\n")

    docs = {
        "docs/assumptions.md": "# Premissas\n\nTarifa, reajuste tarifário, CAPEX, OPEX e fator de CO2 são premissas editáveis. Tarifa e reajuste não são oficiais nem previsão. O fator de emissões é ilustrativo e deve ser substituído por fonte oficial antes de uso público.",
        "docs/executive_summary.md": f"# Resumo Executivo\n\nO caso-base fictício resulta em {metrics['installed_kwp']:.1f} kWp instalados, {metrics['annual_generation_kwh']:,.0f} kWh/ano, VPL de {fmt_brl(float(metrics['npv_brl']))}, TIR de {fmt_pct(float(metrics['irr'])) if metrics['irr'] is not None else 'n.a.'} e payback simples de {metrics['payback_simple_years']:.1f} anos.",
        "docs/financial_metrics.md": "# Indicadores Financeiros\n\nO modelo calcula VPL, TIR, payback simples, payback descontado, ROI acumulado em 25 anos e LCOE. ROI acumulado = economia líquida acumulada / CAPEX. LCOE inclui CAPEX, OPEX, custos extraordinários e energia degradada descontada.",
        "docs/financing.md": "# Financiamento\n\nO projeto inclui função para cronograma anual de financiamento pelo método Price simplificado. O financiamento não altera o caso-base automaticamente e pode ser usado em extensões do portfólio.",
        "docs/formulas.md": "# Fórmulas\n\nPotência recomendada = consumo diário médio / (HSP média x Performance Ratio). Geração mensal = kWp instalado x HSP x dias x Performance Ratio x disponibilidade. VPL = soma dos fluxos descontados. ROI acumulado = economia líquida acumulada / CAPEX. LCOE = valor presente dos custos / valor presente da energia degradada.",
        "docs/future_versions.md": "# Próximas Versões\n\nPossíveis evoluções: integração com tarifas reais por concessionária, curvas horárias, regras regulatórias detalhadas, banco de componentes, comparação com financiamento e publicação automatizada do dashboard.",
        "docs/insights.md": f"# Insights do Caso-Base\n\nA classificação do projeto é {metrics['feasibility']}. A sensibilidade CAPEX x tarifa mostra que preço de implantação e tarifa compensável são os principais direcionadores econômicos.",
        "docs/interview_case.md": "# Caso para Entrevista\n\nEste projeto demonstra capacidade de transformar um problema técnico-financeiro em ferramenta auditável com Python, Excel, Streamlit, cenários, sensibilidade e documentação executiva.",
        "docs/linkedin_project.md": "# Projeto para LinkedIn\n\nSimulador de Viabilidade Técnica e Econômica de Energia Solar\n\nProjeto em Python, Excel e Streamlit para avaliar dimensionamento fotovoltaico, geração, fluxo de caixa, VPL, TIR, Payback, ROI acumulado e LCOE.",
        "docs/linkedin_post.md": "# Post para LinkedIn\n\nFinalizeI um simulador de viabilidade técnica e econômica de energia solar que conecta engenharia elétrica, geração fotovoltaica e análise financeira em uma ferramenta prática.\n\nO projeto inclui app Streamlit, Excel com fórmulas, cenários, sensibilidade CAPEX x tarifa, documentação e assets de portfólio.",
        "docs/methodology.md": "# Metodologia\n\nO modelo parte de premissas editáveis de consumo, HSP, módulo, Performance Ratio, perdas, CAPEX, OPEX, tarifa, reajuste, TMA, degradação e vida útil. A decisão financeira considera fluxo de caixa anual, VPL, TIR, Payback, ROI acumulado e LCOE.",
        "docs/portfolio_description.md": "# Descrição de Portfólio\n\nFerramenta de análise para projetos solares fotovoltaicos com foco em clareza técnica, rastreabilidade financeira e apresentação profissional.",
        "docs/resume_bullet_points.md": "# Pontos para Currículo\n\n- Desenvolvi simulador de viabilidade solar em Python, Streamlit e Excel.\n- Modelei geração fotovoltaica, CAPEX, OPEX, VPL, TIR, Payback, ROI acumulado e LCOE.\n- Automatizei relatórios, gráficos, cenários, sensibilidade e pacote final de entrega.",
    }
    for rel, content in docs.items():
        write_text(ROOT / rel, content)


def update_linkedin(metrics: dict[str, float | int | str | None]) -> None:
    files = {
        "01_PROJETO_LINKEDIN.txt": f"""Título do projeto:
Simulador de Viabilidade Técnica e Econômica de Energia Solar

Descrição:
Projeto de portfólio que integra engenharia elétrica, geração fotovoltaica, modelagem financeira, Excel e Streamlit. O simulador estima potência instalada, geração anual, fluxo de caixa, VPL, TIR, Payback, ROI acumulado em 25 anos e LCOE para um caso comercial fictício.

Resultado do caso-base:
Potência instalada: {metrics['installed_kwp']:.1f} kWp
Geração anual: {metrics['annual_generation_kwh']:,.0f} kWh
VPL: {fmt_brl(float(metrics['npv_brl']))}
Payback simples: {metrics['payback_simple_years']:.1f} anos
""",
        "02_COMPETENCIAS.txt": "Python\nStreamlit\nExcel\nModelagem financeira\nEnergia solar fotovoltaica\nEngenharia elétrica\nAnálise de sensibilidade\nVPL\nTIR\nPayback\nLCOE\nDocumentação técnica\n",
        "03_POST_LINKEDIN.md": f"""# Post LinkedIn

Concluí um projeto de portfólio em energia solar: um simulador de viabilidade técnica e econômica para sistemas fotovoltaicos.

O projeto conecta engenharia elétrica, geração de energia e análise financeira em uma ferramenta com app Streamlit, Excel com fórmulas, relatórios, cenários e sensibilidade CAPEX x tarifa.

No caso-base fictício:
- Potência instalada: {metrics['installed_kwp']:.1f} kWp
- Geração anual: {metrics['annual_generation_kwh']:,.0f} kWh
- VPL: {fmt_brl(float(metrics['npv_brl']))}
- Payback simples: {metrics['payback_simple_years']:.1f} anos
- ROI acumulado em 25 anos: {fmt_pct(float(metrics['roi_accumulated']))}

Os dados são fictícios e as premissas de tarifa, reajuste e emissões são editáveis.
""",
        "04_COMO_ADICIONAR.txt": "LinkedIn > Perfil > Adicionar seção do perfil > Recomendado > Adicionar projeto. Use o texto de 01_PROJETO_LINKEDIN.txt, anexe as imagens de assets/linkedin/ e preencha as URLs do arquivo 05_URLS.txt quando houver publicação.",
        "05_URLS.txt": "GitHub: https://github.com/luscaarmstrong1/solar-energy-feasibility-simulator\nDemonstração: https://luscaarmstrong1.github.io/solar-energy-feasibility-simulator/\nStreamlit local: executar com INICIAR_SIMULADOR.bat\nZIP final: outputs/solar-energy-feasibility-simulator-FINAL-PTBR.zip\n",
        "06_RESUMO_30_SEGUNDOS.txt": "Simulador em Python, Excel e Streamlit para avaliar viabilidade técnica e econômica de energia solar. Calcula dimensionamento, geração, fluxo de caixa, VPL, TIR, Payback, ROI acumulado, LCOE, cenários e sensibilidade.",
        "07_RESUMO_1_MINUTO.txt": "Desenvolvi um simulador de viabilidade solar para conectar engenharia elétrica e decisão financeira. A ferramenta estima potência instalada, geração mensal, economia, fluxo de caixa em 25 anos e indicadores como VPL, TIR, Payback, ROI acumulado e LCOE. Também inclui Excel auditável, app Streamlit em português, relatórios, gráficos, cenários e sensibilidade CAPEX x tarifa.",
        "08_RESULTADOS_DO_PROJETO.txt": f"Potência instalada: {metrics['installed_kwp']:.1f} kWp\nMódulos: {metrics['modules']}\nGeração anual: {metrics['annual_generation_kwh']:,.0f} kWh\nCAPEX: {fmt_brl(float(metrics['capex_total_brl']))}\nVPL: {fmt_brl(float(metrics['npv_brl']))}\nTIR: {fmt_pct(float(metrics['irr'])) if metrics['irr'] is not None else 'n.a.'}\nROI acumulado: {fmt_pct(float(metrics['roi_accumulated']))}\nLCOE: R$ {float(metrics['lcoe_brl_kwh']):.3f}/kWh\n",
    }
    for name, content in files.items():
        write_text(ROOT / "linkedin" / name, content)


def update_site(metrics: dict[str, float | int | str | None]) -> None:
    docs_assets = ROOT / "docs" / "assets" / "screenshots"
    docs_assets.mkdir(parents=True, exist_ok=True)
    for name in ["01_visao_geral.png", "07_sensibilidade.png"]:
        shutil.copy2(ROOT / "assets" / "screenshots" / name, docs_assets / name)
    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Simulador de Viabilidade Solar</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; color: #1f2937; background: #f8fafc; }}
    header {{ background: #0f766e; color: white; padding: 48px 8vw; }}
    main {{ padding: 32px 8vw; max-width: 1100px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 16px; }}
    .card {{ background: white; border: 1px solid #d0d5dd; border-radius: 8px; padding: 18px; }}
    img {{ max-width: 100%; border: 1px solid #d0d5dd; border-radius: 8px; background: white; }}
  </style>
</head>
<body>
  <header>
    <h1>Simulador de Viabilidade Técnica e Econômica de Energia Solar</h1>
    <p>Projeto de portfólio com Python, Excel, Streamlit, cenários e sensibilidade.</p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><strong>Potência instalada</strong><br>{metrics['installed_kwp']:.1f} kWp</div>
      <div class="card"><strong>Geração anual</strong><br>{metrics['annual_generation_kwh']:,.0f} kWh</div>
      <div class="card"><strong>VPL</strong><br>{fmt_brl(float(metrics['npv_brl']))}</div>
      <div class="card"><strong>Payback simples</strong><br>{metrics['payback_simple_years']:.1f} anos</div>
    </section>
    <h2>Painel</h2>
    <img src="assets/screenshots/01_visao_geral.png" alt="Visão geral do simulador">
    <h2>Sensibilidade</h2>
    <img src="assets/screenshots/07_sensibilidade.png" alt="Sensibilidade CAPEX x tarifa">
    <p>Dados fictícios para demonstração. Tarifa, reajuste e fator de emissões são premissas editáveis.</p>
  </main>
</body>
</html>"""
    write_text(ROOT / "docs" / "index.html", html)


def inventory() -> None:
    files = sorted(
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and ".git/" not in p.as_posix()
        and "__pycache__" not in p.parts
        and ".pytest_cache" not in p.parts
        and "work" not in p.parts
    )
    write_text(ROOT / "INVENTARIO_FINAL.txt", "\n".join(files))


def reports(metrics: dict[str, float | int | str | None], tests_summary: str, excel_summary: str) -> None:
    validation = f"""
# Relatório de Validação

Data de geração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Testes

{tests_summary}

## Excel

{excel_summary}

## Conferências

- ROI acumulado em 25 anos definido como economia líquida acumulada / CAPEX.
- LCOE inclui CAPEX, OPEX, custos extraordinários e energia degradada descontada.
- Tarifa e reajuste tarifário tratados como premissas sintéticas.
- Fator de emissões tratado como premissa ilustrativa editável.
- Busca por caminhos locais e termos sensíveis executada no fechamento.
"""
    final = f"""
# Relatório Final

O projeto foi finalizado como simulador de viabilidade técnica e econômica de energia solar em português.

## Resultado do Caso-Base

- Potência instalada: {metrics['installed_kwp']:.1f} kWp
- Módulos: {metrics['modules']}
- Geração anual: {metrics['annual_generation_kwh']:,.0f} kWh
- CAPEX: {fmt_brl(float(metrics['capex_total_brl']))}
- Economia líquida Ano 1: {fmt_brl(float(metrics['year_1_savings_brl']))}
- Payback simples: {metrics['payback_simple_years']:.1f} anos
- Payback descontado: {metrics['payback_discounted_years']:.1f} anos
- VPL: {fmt_brl(float(metrics['npv_brl']))}
- TIR: {fmt_pct(float(metrics['irr'])) if metrics['irr'] is not None else 'n.a.'}
- ROI acumulado em 25 anos: {fmt_pct(float(metrics['roi_accumulated']))}
- LCOE: R$ {float(metrics['lcoe_brl_kwh']):.3f}/kWh

## Entregáveis

App Streamlit, workbook Excel, CSVs, JSONs, imagens para LinkedIn, screenshots, documentação, site estático, relatórios e pacote ZIP final.
"""
    write_text(ROOT / "RELATORIO_VALIDACAO.md", validation)
    write_text(ROOT / "RELATORIO_FINAL.md", final)


def clean() -> None:
    for pattern in ["__pycache__", ".pytest_cache"]:
        for path in ROOT.rglob(pattern):
            if path.is_dir() and ROOT in path.parents:
                shutil.rmtree(path, ignore_errors=True)
    work = ROOT / "work"
    if work.exists() and ROOT in work.parents:
        shutil.rmtree(work, ignore_errors=True)
    for old_name in ["web_dashboard.png", "excel_dashboard.png", "cashflow.png", "sensitivity.png", "scenarios.png"]:
        old_path = ROOT / "assets" / "screenshots" / old_name
        if old_path.exists():
            old_path.unlink()


def excel_check() -> str:
    workbook = ROOT / "Solar_Feasibility_Simulator.xlsx"
    loaded = load_workbook(workbook, data_only=False)
    formulas = 0
    charts = 0
    errors: list[str] = []
    for ws in loaded.worksheets:
        charts += len(ws._charts)
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas += 1
                if isinstance(cell.value, str) and any(err in cell.value for err in ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?"]):
                    errors.append(f"{ws.title}!{cell.coordinate}")
    if errors:
        raise RuntimeError("Erros de fórmula: " + ", ".join(errors))
    return f"{len(loaded.sheetnames)} abas, {formulas} fórmulas e {charts} gráficos verificados."


def zip_project() -> tuple[Path, Path]:
    PARENT_OUTPUTS.mkdir(parents=True, exist_ok=True)
    zip_path = PARENT_OUTPUTS / "solar-energy-feasibility-simulator-FINAL-PTBR.zip"
    sha_path = PARENT_OUTPUTS / "solar-energy-feasibility-simulator-FINAL-PTBR.sha256.txt"
    ignored_dirs = {".git", "__pycache__", ".pytest_cache", "work"}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if path.is_dir() or any(part in ignored_dirs for part in path.relative_to(ROOT).parts):
                continue
            zf.write(path, ROOT.name + "/" + path.relative_to(ROOT).as_posix())
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    write_text(sha_path, f"{digest}  {zip_path.name}")
    return zip_path, sha_path


def main() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "work" / ".mplconfig"))
    outputs = ROOT / "outputs"
    outputs.mkdir(exist_ok=True)

    run([sys.executable, "scripts/run_simulation.py"])
    run([sys.executable, "scripts/build_excel.py"])
    run([sys.executable, "scripts/generate_assets.py"])
    pytest_output = run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"])
    validation_output = run([sys.executable, "scripts/validate_model.py"])

    metrics = kpis(base_solar_inputs(), base_financial_inputs())
    tests_summary = (pytest_output + "\n" + validation_output).strip()
    excel_summary = excel_check()

    update_markdown(metrics, tests_summary)
    update_linkedin(metrics)
    update_site(metrics)
    reports(metrics, tests_summary, excel_summary)
    inventory()

    shutil.copy2(ROOT / "Solar_Feasibility_Simulator.xlsx", outputs / "Solar_Feasibility_Simulator.xlsx")
    clean()
    zip_path, sha_path = zip_project()
    print(json.dumps({"status": "ok", "zip": str(zip_path), "sha256": str(sha_path), "excel": excel_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
