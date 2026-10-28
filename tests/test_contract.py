"""Contract tests that must pass without the proprietary core."""
from __future__ import annotations

import json
import unittest

from jmgo_cognition.api import Core, NullCore, load_core
from jmgo_cognition.loop import apply_actions, run_loop
from jmgo_cognition.plugins import EchoSensor, LogActuator, Registry
from jmgo_cognition.plugins.example import DemoPlugin


class BrokenSensor:
    name = "broken"

    def read(self):
        raise RuntimeError("boom")


class FakeCore:
    """A minimal well-behaved core used to test the loop and the gate."""

    installed = True

    def version(self):
        return {"version": "fake", "capabilities": ["test"]}

    def plan(self, query, ctx):
        return {"queries": [query], "slots": {}, "steps": []}

    def retrieve(self, plan, ctx):
        return {"items": [{"title": "t", "snippet": "s", "source": "u"}], "errors": []}

    def reason(self, query, evidence, ctx):
        return {
            "answer": "ok",
            "status": "ok",
            "basis": ["t"],
            "actions": [{"type": "move", "to": "table"}],
        }

    def verify(self, answer, ctx):
        return {"ok": True, "reasons": [], "risk": "low"}


class ReflectiveCore(FakeCore):
    """Reports a sandbox self-emotion; must stay read-only."""

    def reflect(self, result, ctx):
        return {
            "emotion": {"valence": 0.2, "arousal": 0.1, "trigger": "reasoning_ok"},
            "quality": "good",
            "notes": ["sandbox_only"],
        }


class BrokenReflect(FakeCore):
    def reflect(self, result, ctx):
        raise RuntimeError("reflect boom")


class ContractTest(unittest.TestCase):
    def test_null_core_implements_contract(self):
        self.assertIsInstance(NullCore(), Core)

    def test_missing_core_is_observable_and_never_acts(self):
        result = run_loop("把杯子拿过来", core=NullCore())
        self.assertEqual(result["answer"]["status"], "core_missing")
        self.assertFalse(result["verdict"]["ok"])
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["core"]["installed"], False)
        steps = [t["step"] for t in result["trace"]]
        self.assertEqual(steps,
                         ["plan", "retrieve", "reason", "verify", "reflect"])

    def test_result_is_json_serializable(self):
        result = run_loop("巡检 A 区", core=FakeCore())
        json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["answer"]["status"], "ok")
        self.assertTrue(result["verdict"]["ok"])

    def test_sensor_failure_is_recorded_not_raised(self):
        result = run_loop("test", core=NullCore(), sensors=[BrokenSensor()])
        sense = [t for t in result["trace"] if t["step"].startswith("sense:")]
        self.assertEqual(len(sense), 1)
        self.assertEqual(sense[0]["status"], "error")
        self.assertIn("boom", sense[0]["error"])

    def test_actions_require_explicit_allow_and_verdict(self):
        actuator = LogActuator()
        result = run_loop("move", core=FakeCore())
        self.assertEqual(apply_actions(result, actuator), [])
        self.assertEqual(actuator.calls, [])

        blocked = dict(result)
        blocked["verdict"] = {"ok": False}
        self.assertEqual(apply_actions(blocked, actuator, allow=True), [])
        self.assertEqual(actuator.calls, [])

        out = apply_actions(result, actuator, allow=True)
        self.assertEqual(len(out), 1)
        self.assertEqual(len(actuator.calls), 1)

    def test_reflection_is_read_only(self):
        result = run_loop("move", core=ReflectiveCore())
        self.assertTrue(result["verdict"]["ok"])
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["reflection"]["emotion"]["valence"], 0.2)
        steps = [t["step"] for t in result["trace"]]
        self.assertEqual(steps[-1], "reflect")
        self.assertLess(steps.index("verify"), steps.index("reflect"))

    def test_reflection_failure_does_not_affect_decision(self):
        result = run_loop("move", core=BrokenReflect())
        self.assertTrue(result["verdict"]["ok"])
        self.assertEqual(len(result["actions"]), 1)
        self.assertIsNone(result["reflection"])
        last = result["trace"][-1]
        self.assertEqual(last["step"], "reflect")
        self.assertEqual(last["status"], "error")

    def test_plugin_registry(self):
        reg = Registry().add_plugin(DemoPlugin())
        self.assertIn("echo", reg.sensors)
        self.assertIn("log", reg.actuators)
        self.assertEqual(EchoSensor().read()["text"], "hello")

    def test_loader_falls_back(self):
        core = load_core()
        self.assertIsInstance(core, Core)
        self.assertFalse(getattr(core, "installed", False))


if __name__ == "__main__":
    unittest.main()
