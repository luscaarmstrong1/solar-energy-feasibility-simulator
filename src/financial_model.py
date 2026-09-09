"""Modelo financeiro para análise de viabilidade fotovoltaica."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

import numpy as np
import numpy_financial as npf

from .solar_model import SolarInputs, annual_generation_year, monthly_generation, size_system


@dataclass(frozen=True)
class FinancialInputs:
    tariff_compensable_brl_kwh: float
    capex_total_brl: float | None = None
    capex_per_kwp_brl: float = 4200.0
    opex_annual_brl: float | None = None
    opex_pct_capex: float = 0.012
    tariff_escalation: float = 0.04
    discount_rate: float = 0.10
    co2_factor_kg_per_kwh: float = 0.0385
    autoconsumption_pct: float = 1.0
    extraordinary_costs: dict[int, float] = field(default_factory=lambda: {12: 25000.0})
    include_extraordinary_costs: bool = True


def validate_financial_inputs(inputs: FinancialInputs) -> None:
    if inputs.tariff_compensable_brl_kwh < 0:
        raise ValueError("tariff_compensable_brl_kwh não pode ser negativa")
    if inputs.capex_total_brl is not None and inputs.capex_total_brl < 0:
        raise ValueError("capex_total_brl não pode ser negativo")
    if inputs.capex_per_kwp_brl < 0:
        raise ValueError("capex_per_kwp_brl não pode ser negativo")
    if inputs.opex_annual_brl is not None and inputs.opex_annual_brl < 0:
        raise ValueError("opex_annual_brl não pode ser negativo")
    if inputs.opex_pct_capex < 0:
        raise ValueError("opex_pct_capex não pode ser negativo")
    if inputs.discount_rate <= -1:
        raise ValueError("discount_rate deve ser maior que -100%")
    if not 0 <= inputs.autoconsumption_pct <= 1:
        raise ValueError("autoconsumption_pct deve estar entre 0 e 1")
    if inputs.co2_factor_kg_per_kwh < 0:
        raise ValueError("co2_factor_kg_per_kwh não pode ser negativo")


def capex(solar: SolarInputs, financial: FinancialInputs) -> float:
    validate_financial_inputs(financial)
    if financial.capex_total_brl is not None:
        return financial.capex_total_brl
    return float(size_system(solar)["installed_kwp"]) * financial.capex_per_kwp_brl


def annual_opex(solar: SolarInputs, financial: FinancialInputs) -> float:
    return financial.opex_annual_brl if financial.opex_annual_brl is not None else capex(solar, financial) * financial.opex_pct_capex


def cash_flow(solar: SolarInputs, financial: FinancialInputs) -> list[dict[str, float | int]]:
    validate_financial_inputs(financial)
    total_capex = capex(solar, financial)
    rows: list[dict[str, float | int]] = [
        {
            "year": 0,
            "generation_kwh": 0.0,
            "tariff_brl_kwh": financial.tariff_compensable_brl_kwh,
            "gross_savings_brl": 0.0,
            "opex_brl": 0.0,
            "extraordinary_costs_brl": 0.0,
            "net_savings_brl": 0.0,
            "cash_flow_brl": -total_capex,
            "discount_factor": 1.0,
            "discounted_cash_flow_brl": -total_capex,
        }
    ]
    cumulative = -total_capex
    discounted_cumulative = -total_capex
    rows[0]["cumulative_cash_flow_brl"] = cumulative
    rows[0]["cumulative_discounted_cash_flow_brl"] = discounted_cumulative

    for year in range(1, solar.system_life_years + 1):
        generation = annual_generation_year(solar, year)
        tariff = financial.tariff_compensable_brl_kwh * (1 + financial.tariff_escalation) ** (year - 1)
        gross_savings = generation * tariff * financial.autoconsumption_pct
        opex_value = annual_opex(solar, financial)
        extra = financial.extraordinary_costs.get(year, 0.0) if financial.include_extraordinary_costs else 0.0
        net_savings = gross_savings - opex_value - extra
        discount_factor = 1 / (1 + financial.discount_rate) ** year
        discounted = net_savings * discount_factor
        cumulative += net_savings
        discounted_cumulative += discounted
        rows.append(
            {
                "year": year,
                "generation_kwh": generation,
                "tariff_brl_kwh": tariff,
                "gross_savings_brl": gross_savings,
                "opex_brl": opex_value,
                "extraordinary_costs_brl": extra,
                "net_savings_brl": net_savings,
                "cash_flow_brl": net_savings,
                "cumulative_cash_flow_brl": cumulative,
                "discount_factor": discount_factor,
                "discounted_cash_flow_brl": discounted,
                "cumulative_discounted_cash_flow_brl": discounted_cumulative,
            }
        )
    return rows


def _payback_from_rows(rows: list[dict[str, float | int]], column: str) -> float | None:
    for idx in range(1, len(rows)):
        prev = float(rows[idx - 1][column])
        current = float(rows[idx][column])
        if current >= 0:
            period_flow = current - prev
            fraction = abs(prev) / period_flow if period_flow else 0
            return (idx - 1) + fraction
    return None


def payback_simple(rows: list[dict[str, float | int]]) -> float | None:
    return _payback_from_rows(rows, "cumulative_cash_flow_brl")


def payback_discounted(rows: list[dict[str, float | int]]) -> float | None:
    return _payback_from_rows(rows, "cumulative_discounted_cash_flow_brl")


def lcoe(solar: SolarInputs, financial: FinancialInputs, rows: list[dict[str, float | int]] | None = None) -> float:
    rows = rows or cash_flow(solar, financial)
    total_capex = capex(solar, financial)
    pv_costs = total_capex
    pv_energy = 0.0
    for row in rows[1:]:
        year = int(row["year"])
        factor = 1 / (1 + financial.discount_rate) ** year
        pv_costs += (float(row["opex_brl"]) + float(row["extraordinary_costs_brl"])) * factor
        pv_energy += float(row["generation_kwh"]) * factor
    return pv_costs / pv_energy


def roi(rows: list[dict[str, float | int]]) -> float:
    """ROI acumulado do horizonte analisado: ganho líquido acumulado / CAPEX."""
    investment = abs(float(rows[0]["cash_flow_brl"]))
    total_net_gain = sum(float(row["cash_flow_brl"]) for row in rows[1:])
    return total_net_gain / investment


def feasibility_label(npv: float, irr: float | None, discount_rate: float) -> str:
    if npv > 0 and irr is not None and irr > discount_rate:
        return "Atrativo"
    if npv > 0 or (irr is not None and irr > discount_rate):
        return "Moderado"
    return "Pouco atrativo"


def financing_schedule(
    financed_amount_brl: float,
    annual_interest_rate: float,
    term_years: int,
    grace_years: int = 0,
) -> list[dict[str, float | int]]:
    """Simple annual Price-style financing schedule for portfolio analysis."""
    if financed_amount_brl < 0:
        raise ValueError("financed_amount_brl cannot be negative")
    if annual_interest_rate < 0:
        raise ValueError("annual_interest_rate cannot be negative")
    if term_years <= 0:
        raise ValueError("term_years must be positive")
    if grace_years < 0:
        raise ValueError("grace_years cannot be negative")
    payment = float(npf.pmt(annual_interest_rate, term_years, -financed_amount_brl)) if annual_interest_rate else financed_amount_brl / term_years
    balance = financed_amount_brl
    rows: list[dict[str, float | int]] = []
    for year in range(1, term_years + grace_years + 1):
        if year <= grace_years:
            interest = balance * annual_interest_rate
            principal = 0.0
            installment = interest
        else:
            interest = balance * annual_interest_rate
            principal = min(payment - interest, balance)
            installment = principal + interest
            balance = max(balance - principal, 0.0)
        rows.append(
            {
                "year": year,
                "installment_brl": installment,
                "interest_brl": interest,
                "principal_brl": principal,
                "ending_balance_brl": balance,
            }
        )
    return rows


def kpis(solar: SolarInputs, financial: FinancialInputs) -> dict[str, float | int | str | None]:
    sizing = size_system(solar)
    monthly = monthly_generation(solar)
    rows = cash_flow(solar, financial)
    flows = np.array([float(row["cash_flow_brl"]) for row in rows], dtype=float)
    irr_value = float(npf.irr(flows))
    if not isfinite(irr_value):
        irr_value = None
    npv = float(sum(float(row["discounted_cash_flow_brl"]) for row in rows))
    total_generation = sum(float(row["generation_kwh"]) for row in rows[1:])
    return {
        **sizing,
        "annual_generation_kwh": sum(float(row["generation_kwh"]) for row in monthly),
        "year_1_savings_brl": float(rows[1]["net_savings_brl"]),
        "capex_total_brl": capex(solar, financial),
        "payback_simple_years": payback_simple(rows),
        "payback_discounted_years": payback_discounted(rows),
        "npv_brl": npv,
        "irr": irr_value,
        "roi": roi(rows),
        "roi_accumulated": roi(rows),
        "lcoe_brl_kwh": lcoe(solar, financial, rows),
        "total_net_savings_brl": sum(float(row["net_savings_brl"]) for row in rows[1:]),
        "co2_avoided_tonnes_lifetime": total_generation * financial.co2_factor_kg_per_kwh / 1000,
        "co2_avoided_tonnes_year_1": float(rows[1]["generation_kwh"]) * financial.co2_factor_kg_per_kwh / 1000,
        "feasibility": feasibility_label(npv, irr_value, financial.discount_rate),
    }
