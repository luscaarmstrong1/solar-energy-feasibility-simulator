from src.financial_model import kpis
from src.scenarios import base_financial_inputs, base_solar_inputs


def test_irr_is_calculated_from_project_cashflows():
    metrics = kpis(base_solar_inputs(), base_financial_inputs())
    assert metrics["irr"] is not None
    assert metrics["irr"] > 0
