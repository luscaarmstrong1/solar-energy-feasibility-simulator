import pytest

from src.scenarios import base_solar_inputs
from src.solar_model import SolarInputs, annual_generation_year, monthly_generation, recommended_capacity_kwp, size_system


def test_recommended_capacity_and_monthly_generation_are_positive():
    solar = base_solar_inputs()
    assert recommended_capacity_kwp(solar) > 0
    assert size_system(solar)["modules"] > 0
    assert sum(row["generation_kwh"] for row in monthly_generation(solar)) > 0


def test_degradation_reduces_generation():
    solar = base_solar_inputs()
    assert annual_generation_year(solar, 10) < annual_generation_year(solar, 1)


def test_invalid_consumption_is_rejected():
    with pytest.raises(ValueError):
        recommended_capacity_kwp(SolarInputs(profile="x", state="SP", city="x", monthly_consumption_kwh=-1))
