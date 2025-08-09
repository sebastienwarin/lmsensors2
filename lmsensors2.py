#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2025 Sascha <you@example.com>
# GPL v3+

import json
import enum

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Service,
    Result,
    State,
    Metric,
)


class SensorType(enum.Enum):
    TEMP      = "temp"
    IN        = "in"
    FAN       = "fan"
    CPU       = "cpu"
    POWER     = "power"
    CURR      = "curr"
    ENERGY    = "energy"
    INTRUSION = "intrusion"
    HUMIDITY  = "humidity"


class Sensor:
    def __init__(self):
        self.name       = None
        self.sensor_type= None
        self.value      = None
        self.warn_value = None
        self.crit_value = None


class Chip:
    def __init__(self):
        self.name    = None
        self.adapter = None
        self.sensors = []


def str_to_float(val: str) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_lmsensors2(string_table: list[list[str]]) -> list[Chip]:
    raw = "\n".join(" ".join(row) for row in string_table)
    data = json.loads(raw)
    chips: list[Chip] = []

    for chip_name, info in data.items():
        chip = Chip()
        chip.name    = chip_name
        chip.adapter = info.get("Adapter", "")

        for sensor_name, vals in info.items():
            if sensor_name == "Adapter":
                continue

            s = Sensor()
            s.name = sensor_name

            for key, v in vals.items():
                if key.endswith("_input"):
                    s.value = str_to_float(v)
                    for st in SensorType:
                        if key.startswith(st.value):
                            s.sensor_type = st
                elif key.endswith("max"):
                    s.warn_value = str_to_float(v)
                elif key.endswith("crit"):
                    s.crit_value = str_to_float(v)

            if s.sensor_type:
                chip.sensors.append(s)

        chips.append(chip)

    return chips


def _discover_lmsensors2(chips: list[Chip], sensor_type: SensorType):
    for chip in chips:
        for sensor in chip.sensors:
            if sensor.sensor_type == sensor_type:
                svc = f"{chip.name} {chip.adapter} {sensor.name}"
                yield Service(item=svc)


def check_lmsensors2_common(
    item: str,
    section: list[Chip],
    metric_name: str,
):
    for chip in section:
        for sensor in chip.sensors:
            svc = f"{chip.name} {chip.adapter} {sensor.name}"
            if svc != item:
                continue

            val = sensor.value
            if val is None:
                yield Result(state=State.WARN, summary="no sensor value")
                return

            # use sensor-supplied thresholds
            lower = sensor.warn_value
            upper = sensor.crit_value

            state = State.OK
            if upper is not None and val >= upper:
                state = State.CRIT
            elif lower is not None and val >= lower:
                state = State.WARN

            yield Result(state=state, summary=f"value is {val}")
            yield Metric(metric_name, val, boundaries=(lower, upper))
            return


def discover_lmsensors2_temp(section: list[Chip]):
    yield from _discover_lmsensors2(section, SensorType.TEMP)


def discover_lmsensors2_fan(section: list[Chip]):
    yield from _discover_lmsensors2(section, SensorType.FAN)


def discover_lmsensors2_volt(section: list[Chip]):
    yield from _discover_lmsensors2(section, SensorType.IN)


def check_lmsensors2_temp(item: str, section: list[Chip]):
    yield from check_lmsensors2_common(item, section, metric_name="temperature")


def check_lmsensors2_fan(item: str, section: list[Chip]):
    yield from check_lmsensors2_common(item, section, metric_name="fan_speed")


def check_lmsensors2_volt(item: str, section: list[Chip]):
    yield from check_lmsensors2_common(item, section, metric_name="volt")


# Register the agent section
agent_section_lmsensors2 = AgentSection(
    name="lmsensors2",
    parse_function=parse_lmsensors2,
)

# Temperature check plugin
check_plugin_lmsensors2_temp = CheckPlugin(
    name="lmsensors2_temp",
    service_name="LM Sensors2 Temperature %s",
    sections=[agent_section_lmsensors2.name],
    discovery_function=discover_lmsensors2_temp,
    check_function=check_lmsensors2_temp,
)

# Fan-speed check plugin
check_plugin_lmsensors2_fan = CheckPlugin(
    name="lmsensors2_fan",
    service_name="LM Sensors2 Fan Speed %s",
    sections=[agent_section_lmsensors2.name],
    discovery_function=discover_lmsensors2_fan,
    check_function=check_lmsensors2_fan,
)

# Voltage check plugin
check_plugin_lmsensors2_volt = CheckPlugin(
    name="lmsensors2_volt",
    service_name="LM Sensors2 Voltage %s",
    sections=[agent_section_lmsensors2.name],
    discovery_function=discover_lmsensors2_volt,
    check_function=check_lmsensors2_volt,
)
