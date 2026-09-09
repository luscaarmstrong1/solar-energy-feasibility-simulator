from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.financial_model import cash_flow, kpis, lcoe, payback_discounted, payback_simple
from src.scenarios import base_financial_inputs, base_solar_inputs
from src.solar_model import annual_generation_year, monthly_generation, recommended_capacity_kwp


def main() -> None:
    solar = base_solar_inputs()
    financial = base_financial_inputs()
    rows = cash_flow(solar, financial)
    metrics = kpis(solar, financial)

    assert recommended_capacity_kwp(solar) > 0
    assert sum(row["generation_kwh"] for row in monthly_generation(solar)) > 0
    assert annual_generation_year(solar, 2) < annual_generation_year(solar, 1)
    assert rows[0]["cash_flow_brl"] < 0
    assert payback_simple(rows) is not None
    assert payback_discounted(rows) is not None
    assert metrics["npv_brl"] != 0
    assert metrics["irr"] is not None
    assert math.isfinite(lcoe(solar, financial, rows))
    assert metrics["feasibility"] in {"Atrativo", "Moderado", "Pouco atrativo"}
    print("Model validation passed.")


if __name__ == "__main__":
    main()
