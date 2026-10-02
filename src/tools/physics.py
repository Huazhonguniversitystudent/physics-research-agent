import math


ELEMENTARY_CHARGE_C = 1.602176634e-19


def electron_energy_from_voltage(voltage_v: float) -> dict[str, float]:
    """Return the energy gained by one electron across a voltage."""
    if isinstance(voltage_v, bool):
        raise ValueError("电势差必须是有限数值。")

    try:
        voltage = float(voltage_v)
    except (TypeError, ValueError) as exc:
        raise ValueError("电势差必须是有限数值。") from exc

    if not math.isfinite(voltage):
        raise ValueError("电势差必须是有限数值。")

    return {
        "voltage_v": voltage,
        "energy_ev": voltage,
        "energy_j": ELEMENTARY_CHARGE_C * voltage,
    }
