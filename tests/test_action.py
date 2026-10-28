"""Action-layer contract tests: decomposition, diffusion, rendering, pipeline."""
from __future__ import annotations

import json
import math
import unittest

from jmgo_cognition.diffusion import (
    CallablePolicy,
    DiffusionPlanner,
    PolicyError,
    verify_trajectory,
)
from jmgo_cognition.embodied import run_task
from jmgo_cognition.render import render
from jmgo_cognition.task_axiom import decompose

CTX = {
    "start": [0.0, 0.0],
    "goal": [6.0, 4.0],
    "obstacles": [{"x": 3.0, "y": 2.0, "r": 0.8}, {"x": 4.5, "y": 3.5, "r": 0.6}],
    "constraints": {"max_step": 0.5, "clearance": 0.15, "goal_tol": 0.2,
                    "bounds": (0.0, 8.0, 0.0, 6.0)},
    "horizon": 22,
}


class TaskAxiomTest(unittest.TestCase):
    def test_grasp_chain(self):
        p = decompose("把桌上的杯子拿过来")
        self.assertTrue(p["applicable"])
        kinds = [s["kind"] for s in p["steps"]]
        self.assertIn("locate", kinds)
        self.assertIn("act", kinds)
        self.assertIn("verify", kinds)
        self.assertIn("杯子的位姿", p["missing"])

    def test_known_pose_skips_locate(self):
        p = decompose("把桌上的杯子拿过来", {"goal": [1, 1]})
        kinds = [s["kind"] for s in p["steps"]]
        self.assertNotIn("locate", kinds)
        self.assertEqual(p["missing"], [])

    def test_place_has_deliver(self):
        p = decompose("把杯子放到水槽里")
        self.assertEqual(p["action"], "place")
        self.assertEqual(p["steps"][-1]["kind"], "deliver")

    def test_non_physical_not_applicable(self):
        p = decompose("什么是区块链")
        self.assertFalse(p["applicable"])


class DiffusionTest(unittest.TestCase):
    def test_deterministic_and_safe(self):
        a = DiffusionPlanner(seed=7).sample(CTX, horizon=22)
        b = DiffusionPlanner(seed=7).sample(CTX, horizon=22)
        self.assertEqual(a["trajectory"], b["trajectory"])
        self.assertTrue(a["ok"], a["reasons"])
        self.assertAlmostEqual(a["trajectory"][0][0], 0.0, places=6)
        self.assertLessEqual(math.dist(a["trajectory"][-1], CTX["goal"]), 0.2)

    def test_injected_collision_rejected(self):
        traj = [[0.0, 0.0], [1.0, 1.0], [3.0, 2.0], [6.0, 4.0]]
        v = verify_trajectory(
            traj, [0.0, 0.0], [6.0, 4.0],
            [([3.0, 2.0], 0.8)],
            {"max_step": 0.5, "clearance": 0.15, "goal_tol": 0.2,
             "bounds": (0.0, 8.0, 0.0, 6.0)},
        )
        self.assertFalse(v["ok"])
        self.assertIn("collision", v["reasons"])

    def test_callable_policy_shape_check(self):
        with self.assertRaises(PolicyError):
            CallablePolicy(lambda o, h: [[0.0, 0.0]]).sample(CTX)


class RenderTest(unittest.TestCase):
    def test_human_text(self):
        p = decompose("把桌上的杯子拿过来", {"goal": [1, 1]})
        out = render(p, {"actions": [[0.3, 0.1]] * 5}, {"ok": True, "reasons": []})
        self.assertIn("步", out)
        self.assertIn("安全闸通过", out)
        self.assertIn("尚未执行", out)
        self.assertNotIn("{", out)
        self.assertNotIn("[", out)

    def test_failure_reasons(self):
        p = decompose("把桌上的杯子拿过来")
        out = render(p, {"actions": [[0.1, 0.1]]}, {"ok": False, "reasons": ["collision"]})
        self.assertIn("未通过", out)
        self.assertIn("不执行", out)

    def test_non_physical_none(self):
        self.assertIsNone(render(decompose("什么是区块链")))


class PipelineTest(unittest.TestCase):
    def test_full_cycle(self):
        r = run_task("把桌上的杯子拿过来", CTX)
        self.assertTrue(r["plan"]["applicable"])
        self.assertTrue(r["verdict"]["ok"])
        self.assertIn("安全闸通过", r["text"])
        json.dumps(r, ensure_ascii=False)

    def test_missing_pose(self):
        r = run_task("把桌上的杯子拿过来", {"start": [0.0, 0.0]})
        self.assertIn("还缺", r["text"])
        self.assertIsNone(r["motion"])

    def test_safety_failure(self):
        bad = CallablePolicy(lambda o, h: [[0.0, 0.0], [3.0, 2.0], [6.0, 4.0]])
        r = run_task("把桌上的杯子拿过来", dict(CTX, policy=bad))
        self.assertFalse(r["verdict"]["ok"])
        self.assertIn("不执行", r["text"])


if __name__ == "__main__":
    unittest.main()
