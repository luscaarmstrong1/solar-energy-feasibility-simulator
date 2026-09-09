from src.financial_model import kpis, lcoe
from src.scenarios import base_financial_inputs, base_solar_inputs


def test_lcoe_is_positive_and_matches_kpi():
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    assert lcoe(solar, financial) > 0
    assert abs(lcoe(solar, financial) - kpis(solar, financial)["lcoe_brl_kwh"]) < 0.0001
