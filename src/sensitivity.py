"""Análise de sensibilidade do caso-base de viabilidade solar."""

from __future__ import annotations

from dataclasses import replace

from .financial_model import FinancialInputs, kpis
from .solar_model import SolarInputs


def one_way_sensitivity(
    solar: SolarInputs,
    financial: FinancialInputs,
    variable: str,
    variations: list[float] | None = None,
) -> list[dict[str, float | str | None]]:
    variations = variations or [-0.20, -0.10, 0.0, 0.10, 0.20]
    rows: list[dict[str, float | str | None]] = []
    for variation in variations:
        test_solar = solar
        test_financial = financial
        if variable == "capex":
            test_financial = replace(financial, capex_per_kwp_brl=financial.capex_per_kwp_brl * (1 + variation))
        elif variable == "tariff":
            test_financial = replace(
                financial, tariff_compensable_brl_kwh=financial.tariff_compensable_brl_kwh * (1 + variation)
            )
        elif variable == "generation":
            test_solar = replace(solar, performance_ratio=min(solar.performance_ratio * (1 + variation), 0.95))
        elif variable == "discount_rate":
            test_financial = replace(financial, discount_rate=max(financial.discount_rate + variation, 0.0))
        elif variable == "tariff_escalation":
            test_financial = replace(financial, tariff_escalation=max(financial.tariff_escalation + variation, 0.0))
        elif variable == "degradation":
            test_solar = replace(solar, degradation_rate=max(solar.degradation_rate + variation / 100, 0.0))
        else:
            raise ValueError(f"variável de sensibilidade não suportada: {variable}")
        metrics = kpis(test_solar, test_financial)
        rows.append(
            {
                "variable": variable,
                "variation": variation,
                "payback_simple_years": metrics["payback_simple_years"],
                "payback_discounted_years": metrics["payback_discounted_years"],
                "npv_brl": metrics["npv_brl"],
                "irr": metrics["irr"],
                "lcoe_brl_kwh": metrics["lcoe_brl_kwh"],
                "roi_accumulated": metrics["roi_accumulated"],
            }
        )
    return rows


def sensitivity_suite(solar: SolarInputs, financial: FinancialInputs) -> list[dict[str, float | str | None]]:
    variables = ["capex", "tariff", "generation", "discount_rate", "tariff_escalation", "degradation"]
    rows: list[dict[str, float | str | None]] = []
    for variable in variables:
        rows.extend(one_way_sensitivity(solar, financial, variable))
    return rows


def capex_tariff_heatmap(
    solar: SolarInputs,
    financial: FinancialInputs,
    capex_variations: list[float] | None = None,
    tariff_variations: list[float] | None = None,
) -> list[dict[str, float | str | None]]:
    """Matriz de sensibilidade cruzada entre CAPEX e tarifa compensável."""
    capex_variations = capex_variations or [-0.20, -0.10, 0.0, 0.10, 0.20]
    tariff_variations = tariff_variations or [-0.20, -0.10, 0.0, 0.10, 0.20]
    rows: list[dict[str, float | str | None]] = []
    for capex_variation in capex_variations:
        for tariff_variation in tariff_variations:
            test_financial = replace(
                financial,
                capex_per_kwp_brl=financial.capex_per_kwp_brl * (1 + capex_variation),
                tariff_compensable_brl_kwh=financial.tariff_compensable_brl_kwh * (1 + tariff_variation),
            )
            metrics = kpis(solar, test_financial)
            rows.append(
                {
                    "capex_variation": capex_variation,
                    "tariff_variation": tariff_variation,
                    "payback_simple_years": metrics["payback_simple_years"],
                    "npv_brl": metrics["npv_brl"],
                    "irr": metrics["irr"],
                    "roi_accumulated": metrics["roi_accumulated"],
                    "feasibility": metrics["feasibility"],
                }
            )
    return rows
