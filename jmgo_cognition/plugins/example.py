"""Reference adapters used by the examples and contract tests."""
from __future__ import annotations

from typing import Any


class EchoSensor:
    """Returns a fixed observation; useful for smoke tests."""

    name = "echo"

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or {"text": "hello", "objects": []}

    def read(self) -> dict[str, Any]:
        return dict(self.payload)


class LogActuator:
    """Records actions instead of moving hardware."""

    name = "log"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(action)
        return {"ok": True, "logged": action}


class DemoPlugin:
    """Registers the reference sensor and actuator."""

    name = "demo"

    def register(self, registry) -> None:
        registry.add_sensor(EchoSensor())
        registry.add_actuator(LogActuator())
