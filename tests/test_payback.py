from src.financial_model import cash_flow, payback_discounted, payback_simple
from src.scenarios import base_financial_inputs, base_solar_inputs


def test_paybacks_use_cumulative_flows():
    rows = cash_flow(base_solar_inputs(), base_financial_inputs())
    simple = payback_simple(rows)
    discounted = payback_discounted(rows)
    assert simple is not None
    assert discounted is not None
    assert discounted >= simple
