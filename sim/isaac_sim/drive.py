"""SI differential-drive commands shared by both simulator checks."""
from pathlib import Path
import json
import math

CONFIG = json.loads((Path(__file__).resolve().parent / "simulation_config.json").read_text())


def wheel_speeds(linear_m_s, yaw_rad_s):
    """Return [left, right] rad/s. +X forward, positive yaw turns left."""
    if not all(math.isfinite(v) for v in (linear_m_s, yaw_rad_s)):
        raise ValueError("Commands must be finite")
    if abs(linear_m_s) > CONFIG["initial_speed_m_s"] + 1e-9:
        raise ValueError("Command exceeds the initial 0.15m/s design limit")
    if abs(yaw_rad_s) > CONFIG["initial_yaw_rate_rad_s"] + 1e-9:
        raise ValueError("Command exceeds the initial 0.3rad/s design limit")
    half = yaw_rad_s * CONFIG["track_m"] / 2
    return [(linear_m_s-half)/CONFIG["wheel_radius_m"], (linear_m_s+half)/CONFIG["wheel_radius_m"]]


def ramp(previous, requested, dt):
    """Limit each wheel's tread-speed change to the design acceleration."""
    step = CONFIG["acceleration_limit_m_s2"] * dt / CONFIG["wheel_radius_m"]
    return [a+max(-step, min(step, b-a)) for a, b in zip(previous, requested)]
