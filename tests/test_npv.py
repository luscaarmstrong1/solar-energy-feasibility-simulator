from src.financial_model import cash_flow, kpis
from src.scenarios import base_financial_inputs, base_solar_inputs


def test_npv_matches_discounted_cash_flow_sum():
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    rows = cash_flow(solar, financial)
    expected = sum(row["discounted_cash_flow_brl"] for row in rows)
    assert abs(kpis(solar, financial)["npv_brl"] - expected) < 0.01
