from __future__ import annotations

import math

import pytest

from src.financial_model import FinancialInputs, cash_flow, kpis, lcoe
from src.scenarios import base_financial_inputs, base_solar_inputs, compare_scenarios
from src.sensitivity import capex_tariff_heatmap, sensitivity_suite
from src.solar_model import SolarInputs, annual_generation_year, monthly_generation, recommended_capacity_kwp


def test_roi_is_accumulated_net_savings_over_capex() -> None:
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    rows = cash_flow(solar, financial)
    metrics = kpis(solar, financial)
    capex = abs(float(rows[0]["cash_flow_brl"]))
    accumulated_net_savings = sum(float(row["net_savings_brl"]) for row in rows[1:])
    assert metrics["roi"] == pytest.approx(accumulated_net_savings / capex)
    assert metrics["roi_accumulated"] == pytest.approx(metrics["roi"])


def test_degradation_reduces_each_following_year() -> None:
    solar = base_solar_inputs()
    for year in range(2, solar.system_life_years + 1):
        assert annual_generation_year(solar, year) < annual_generation_year(solar, year - 1)


def test_lcoe_independent_cross_check_includes_discounted_costs_and_energy() -> None:
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    rows = cash_flow(solar, financial)
    capex = abs(float(rows[0]["cash_flow_brl"]))
    pv_costs = capex
    pv_energy = 0.0
    for row in rows[1:]:
        discount_factor = float(row["discount_factor"])
        pv_costs += (float(row["opex_brl"]) + float(row["extraordinary_costs_brl"])) * discount_factor
        pv_energy += float(row["generation_kwh"]) * discount_factor
    assert lcoe(solar, financial, rows) == pytest.approx(pv_costs / pv_energy)


def test_sensitivity_suite_contains_expected_variables() -> None:
    rows = sensitivity_suite(base_solar_inputs(), base_financial_inputs())
    variables = {row["variable"] for row in rows}
    assert variables == {"capex", "tariff", "generation", "discount_rate", "tariff_escalation", "degradation"}
    assert len(rows) == 30


def test_capex_tariff_heatmap_recalculates_all_combinations() -> None:
    rows = capex_tariff_heatmap(base_solar_inputs(), base_financial_inputs())
    assert len(rows) == 25
    base_row = next(row for row in rows if row["capex_variation"] == 0.0 and row["tariff_variation"] == 0.0)
    assert base_row["npv_brl"] == pytest.approx(kpis(base_solar_inputs(), base_financial_inputs())["npv_brl"])


def test_scenarios_are_ordered_and_named_in_portuguese() -> None:
    rows = compare_scenarios()
    assert [row["scenario"] for row in rows] == ["Conservador", "Base", "Otimista"]
    assert all(row["feasibility"] in {"Atrativo", "Moderado", "Pouco atrativo"} for row in rows)


def test_invalid_financial_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        kpis(base_solar_inputs(), FinancialInputs(tariff_compensable_brl_kwh=-0.01))


def test_invalid_solar_profile_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        recommended_capacity_kwp(
            SolarInputs(
                profile="Teste",
                state="SP",
                city="Campinas",
                monthly_consumption_kwh=0,
            )
        )


def test_monthly_generation_has_twelve_months_and_positive_energy() -> None:
    rows = monthly_generation(base_solar_inputs())
    assert len(rows) == 12
    assert all(float(row["generation_kwh"]) > 0 for row in rows)
    assert math.isclose(sum(float(row["days"]) for row in rows), 365)
