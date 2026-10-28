"""Plugin protocols and examples."""
from .base import ActuatorAdapter, Plugin, Registry, SensorAdapter
from .example import DemoPlugin, EchoSensor, LogActuator

__all__ = [
    "ActuatorAdapter",
    "DemoPlugin",
    "EchoSensor",
    "LogActuator",
    "Plugin",
    "Registry",
    "SensorAdapter",
]
