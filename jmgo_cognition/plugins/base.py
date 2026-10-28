"""Open plugin protocols: sensors in, actuators out.

Keep adapters thin. They translate hardware <-> dicts; they do not reason and
they do not decide. The execution layer must enforce its own limits and the
emergency stop even when the verifier says ``ok``.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SensorAdapter(Protocol):
    name: str

    def read(self) -> dict[str, Any]:
        """Return a JSON-serializable observation."""


@runtime_checkable
class ActuatorAdapter(Protocol):
    name: str

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute one proposed action and return a JSON-serializable result."""


@runtime_checkable
class Plugin(Protocol):
    name: str

    def register(self, registry: "Registry") -> None:
        """Attach sensors/actuators to the registry."""


class Registry:
    """Tiny registry so plugins can compose without import cycles."""

    def __init__(self) -> None:
        self.sensors: dict[str, SensorAdapter] = {}
        self.actuators: dict[str, ActuatorAdapter] = {}

    def add_sensor(self, sensor: SensorAdapter) -> "Registry":
        self.sensors[getattr(sensor, "name", type(sensor).__name__)] = sensor
        return self

    def add_actuator(self, actuator: ActuatorAdapter) -> "Registry":
        self.actuators[getattr(actuator, "name", type(actuator).__name__)] = actuator
        return self

    def add_plugin(self, plugin: Plugin) -> "Registry":
        plugin.register(self)
        return self
