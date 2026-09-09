"""Cenários do simulador de viabilidade solar."""

from __future__ import annotations

from copy import deepcopy

from .financial_model import FinancialInputs, kpis
from .solar_model import SolarInputs


def base_solar_inputs() -> SolarInputs:
    return SolarInputs(
        profile="Comercial fictício",
        state="SP",
        city="Campinas",
        monthly_consumption_kwh=4500,
        hsp_monthly=[4.8, 5.0, 5.1, 5.0, 4.6, 4.3, 4.5, 4.9, 5.0, 5.2, 5.1, 4.9],
        module_power_wp=600,
        module_area_m2=2.6,
        performance_ratio=0.80,
        losses={
            "temperature": 0.060,
            "mismatch": 0.020,
            "dc_cables": 0.015,
            "ac_cables": 0.010,
            "soiling": 0.025,
            "shading": 0.010,
            "other": 0.010,
        },
        inverter_kw=45,
        degradation_rate=0.006,
        system_life_years=25,
        availability=0.995,
    )


def base_financial_inputs() -> FinancialInputs:
    return FinancialInputs(
        tariff_compensable_brl_kwh=0.95,
        capex_per_kwp_brl=4200,
        opex_pct_capex=0.012,
        tariff_escalation=0.04,
        discount_rate=0.10,
        co2_factor_kg_per_kwh=0.0385,
        extraordinary_costs={12: 25000},
        include_extraordinary_costs=True,
    )


def scenario_variants() -> dict[str, tuple[SolarInputs, FinancialInputs]]:
    base_solar = base_solar_inputs()
    base_financial = base_financial_inputs()

    conservative_solar = deepcopy(base_solar)
    conservative_financial = deepcopy(base_financial)
    conservative_solar = SolarInputs(**{**conservative_solar.__dict__, "performance_ratio": 0.76})
    conservative_financial = FinancialInputs(
        **{
            **conservative_financial.__dict__,
            "capex_per_kwp_brl": base_financial.capex_per_kwp_brl * 1.10,
            "tariff_escalation": 0.02,
            "discount_rate": 0.12,
        }
    )

    optimistic_solar = deepcopy(base_solar)
    optimistic_financial = deepcopy(base_financial)
    optimistic_solar = SolarInputs(**{**optimistic_solar.__dict__, "performance_ratio": 0.84})
    optimistic_financial = FinancialInputs(
        **{
            **optimistic_financial.__dict__,
            "capex_per_kwp_brl": base_financial.capex_per_kwp_brl * 0.92,
            "tariff_escalation": 0.05,
            "discount_rate": 0.09,
        }
    )

    return {
        "Conservador": (conservative_solar, conservative_financial),
        "Base": (base_solar, base_financial),
        "Otimista": (optimistic_solar, optimistic_financial),
    }


def compare_scenarios() -> list[dict[str, float | str | int | None]]:
    rows = []
    for name, (solar, financial) in scenario_variants().items():
        metrics = kpis(solar, financial)
        rows.append({"scenario": name, "cenário": name, **metrics})
    return rows
