from src.financial_model import annual_opex, capex, cash_flow
from src.scenarios import base_financial_inputs, base_solar_inputs


def test_capex_and_opex_are_positive():
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    assert capex(solar, financial) > 0
    assert annual_opex(solar, financial) > 0


def test_cashflow_starts_with_negative_investment():
    rows = cash_flow(base_solar_inputs(), base_financial_inputs())
    assert rows[0]["year"] == 0
    assert rows[0]["cash_flow_brl"] < 0
    assert rows[1]["generation_kwh"] > 0
    assert rows[-1]["cumulative_cash_flow_brl"] > rows[0]["cumulative_cash_flow_brl"]
