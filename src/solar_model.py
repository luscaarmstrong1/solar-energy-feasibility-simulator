"""Modelo técnico de dimensionamento e geração solar fotovoltaica."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

MONTHS_PT = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


@dataclass(frozen=True)
class SolarInputs:
    """Premissas de entrada para um sistema fotovoltaico conectado à rede."""

    profile: str
    state: str
    city: str
    monthly_consumption_kwh: float
    monthly_consumption_profile_kwh: list[float] | None = None
    hsp_monthly: list[float] = field(default_factory=lambda: [5.0] * 12)
    module_power_wp: float = 600.0
    module_area_m2: float = 2.6
    performance_ratio: float = 0.80
    losses: dict[str, float] = field(default_factory=dict)
    inverter_kw: float = 40.0
    desired_offset: float = 1.0
    user_defined_modules: int | None = None
    degradation_rate: float = 0.006
    system_life_years: int = 25
    availability: float = 0.995
    orientation: str = "Norte"
    tilt_deg: float = 20.0


def validate_solar_inputs(inputs: SolarInputs) -> None:
    if inputs.monthly_consumption_kwh <= 0:
        raise ValueError("monthly_consumption_kwh deve ser positivo")
    if len(inputs.hsp_monthly) != 12:
        raise ValueError("hsp_monthly deve conter 12 valores")
    if any(h <= 0 for h in inputs.hsp_monthly):
        raise ValueError("todos os valores de HSP devem ser positivos")
    if inputs.monthly_consumption_profile_kwh is not None:
        if len(inputs.monthly_consumption_profile_kwh) != 12:
            raise ValueError("monthly_consumption_profile_kwh deve conter 12 valores")
        if any(v < 0 for v in inputs.monthly_consumption_profile_kwh):
            raise ValueError("os consumos mensais não podem ser negativos")
    if not 0.50 <= inputs.performance_ratio <= 0.95:
        raise ValueError("performance_ratio deve estar entre 0,50 e 0,95")
    if inputs.module_power_wp <= 0:
        raise ValueError("module_power_wp deve ser positivo")
    if inputs.module_area_m2 <= 0:
        raise ValueError("module_area_m2 deve ser positiva")
    if inputs.inverter_kw <= 0:
        raise ValueError("inverter_kw deve ser positivo")
    if not 0 <= inputs.degradation_rate < 0.05:
        raise ValueError("degradation_rate deve estar entre 0 e 5%")
    if inputs.system_life_years <= 0:
        raise ValueError("system_life_years deve ser positivo")


def compose_losses(losses: dict[str, float]) -> float:
    """Compõe perdas percentuais independentes de forma multiplicativa."""
    retention = 1.0
    for name, value in losses.items():
        if not 0 <= value < 1:
            raise ValueError(f"a perda {name} deve estar entre 0 e 1")
        retention *= 1 - value
    return 1 - retention


def consumption_profile(inputs: SolarInputs) -> list[float]:
    return inputs.monthly_consumption_profile_kwh or [inputs.monthly_consumption_kwh] * 12


def recommended_capacity_kwp(inputs: SolarInputs) -> float:
    validate_solar_inputs(inputs)
    avg_daily_consumption = sum(consumption_profile(inputs)) / 365.0
    avg_hsp = sum(h * d for h, d in zip(inputs.hsp_monthly, DAYS_IN_MONTH)) / 365.0
    return avg_daily_consumption * inputs.desired_offset / (avg_hsp * inputs.performance_ratio)


def size_system(inputs: SolarInputs) -> dict[str, float | int | str]:
    capacity_kwp = recommended_capacity_kwp(inputs)
    module_kwp = inputs.module_power_wp / 1000.0
    modules = inputs.user_defined_modules or ceil(capacity_kwp / module_kwp)
    installed_kwp = modules * module_kwp
    return {
        "recommended_kwp": capacity_kwp,
        "modules": modules,
        "installed_kwp": installed_kwp,
        "area_m2": modules * inputs.module_area_m2,
        "dc_ac_ratio": installed_kwp / inputs.inverter_kw,
        "performance_ratio": inputs.performance_ratio,
        "total_losses_pct": compose_losses(inputs.losses),
    }


def monthly_generation(inputs: SolarInputs) -> list[dict[str, float | str]]:
    validate_solar_inputs(inputs)
    sizing = size_system(inputs)
    consumption = consumption_profile(inputs)
    rows: list[dict[str, float | str]] = []
    for idx, month in enumerate(MONTHS_PT):
        generation = (
            float(sizing["installed_kwp"])
            * inputs.hsp_monthly[idx]
            * DAYS_IN_MONTH[idx]
            * inputs.performance_ratio
            * inputs.availability
        )
        cons = consumption[idx]
        rows.append(
            {
                "month": month,
                "month_number": idx + 1,
                "days": DAYS_IN_MONTH[idx],
                "consumption_kwh": cons,
                "hsp": inputs.hsp_monthly[idx],
                "generation_kwh": generation,
                "deficit_surplus_kwh": generation - cons,
                "service_rate": min(generation / cons, 1.0) if cons else 0.0,
            }
        )
    return rows


def annual_generation_year(inputs: SolarInputs, year: int) -> float:
    if year < 1:
        raise ValueError("year deve começar em 1")
    year_one = sum(float(row["generation_kwh"]) for row in monthly_generation(inputs))
    return year_one * (1 - inputs.degradation_rate) ** (year - 1)
