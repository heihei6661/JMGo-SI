"""embodied.py —— 三层串起来：任务拆解公理 → 通用扩散公理 → 文本渲染。

    task text
      → task_axiom.decompose()      前置条件链 + 缺口
      → diffusion_policy.sample()   任意计划 + 能量/约束 + 安全闸
      → action_render.render()      人话：步骤/依据/缺口/未执行

运行：
    python -m jmgo_cognition.embodied --demo
    python3 embodied.py "把桌上的杯子拿过来"
"""
from __future__ import annotations

import contextlib
import json
import sys
from typing import Any

from . import diffusion as DIFF
from . import render as RENDER
from . import task_axiom as TASK
from .console import utf8_stdio


def run_task(task: str, ctx: dict[str, Any] | None = None,
             core: Any | None = None) -> dict[str, Any]:
    ctx = dict(ctx or {})
    # If the binary advertises the task op, let it run the whole action layer.
    if core is not None and hasattr(core, "task"):
        with contextlib.suppress(Exception):
            out = core.task(task, ctx)
            if isinstance(out, dict) and out.get("text") is not None:
                return out
    plan = TASK.decompose(task, ctx)

    motion = verdict = None
    if plan.get("applicable") and "start" in ctx and "goal" in ctx:
        obs = {
            "start": ctx["start"],
            "goal": ctx["goal"],
            "obstacles": ctx.get("obstacles") or [],
            "constraints": ctx.get("constraints") or {},
        }
        policy = ctx.get("policy") or DIFF.DiffusionPlanner(seed=int(ctx.get("seed", 0)))
        motion = policy.sample(obs, horizon=int(ctx.get("horizon", 22)))
        verdict = {"ok": bool(motion.get("ok")),
                   "reasons": list(motion.get("reasons") or [])}

    text = RENDER.render(plan, motion, verdict, executed=bool(ctx.get("executed")))
    return {"task": task, "plan": plan, "motion": motion,
            "verdict": verdict, "text": text}


def _selftest():
    ok = 0
    base = {
        "start": [0.0, 0.0],
        "goal": [6.0, 4.0],
        "obstacles": [{"x": 3.0, "y": 2.0, "r": 0.8},
                      {"x": 4.5, "y": 3.5, "r": 0.6}],
        "constraints": {"max_step": 0.5, "clearance": 0.15, "goal_tol": 0.2,
                        "bounds": (0.0, 8.0, 0.0, 6.0)},
        "horizon": 22,
    }
    r = run_task("把桌上的杯子拿过来", base)
    _n = len(r["plan"]["steps"])
    ok += bool(r["text"] and f"{_n} 步" in r["text"] and "安全闸通过" in r["text"]
               and "还缺" not in r["text"])
    print("① 抓取任务 →\n" + (r["text"] or ""))

    r2 = run_task("什么是区块链", base)
    ok += (not r2["plan"]["applicable"]) and r2["text"] is None
    print("\n② 非物理任务 → applicable=False, text=None")

    r3 = run_task("把桌上的杯子拿过来", {"start": [0.0, 0.0]})
    ok += bool(r3["text"] and "还缺" in r3["text"] and "安全闸通过" not in r3["text"])
    print("\n③ 缺位姿 →\n" + (r3["text"] or ""))

    bad = DIFF.CallablePolicy(lambda o, h: [[0.0, 0.0], [3.0, 2.0], [6.0, 4.0]],
                              name="bad-demo")
    r4 = run_task("把桌上的杯子拿过来", dict(base, policy=bad))
    ok += bool(r4["text"] and "未通过" in r4["text"] and "不执行" in r4["text"])
    print("\n④ 安全闸失败 →\n" + (r4["text"] or ""))

    json.dumps(r, ensure_ascii=False)
    ok += True
    print("\n⑤ 结果可 JSON 序列化 → True")

    n = int(ok)
    print(f"\n== 判定汇总：{n}/5 ==")
    print(f"PASS {n}/5" if n == 5 else "FAIL")
    return n == 5


def _demo():
    ctx = {
        "start": [0.0, 0.0],
        "goal": [6.0, 4.0],
        "obstacles": [{"x": 3.0, "y": 2.0, "r": 0.8},
                      {"x": 4.5, "y": 3.5, "r": 0.6}],
        "constraints": {"max_step": 0.5, "clearance": 0.15, "goal_tol": 0.2,
                        "bounds": (0.0, 8.0, 0.0, 6.0)},
        "horizon": 22,
    }
    task = " ".join(sys.argv[2:]) or "把桌上的杯子拿过来"
    r = run_task(task, ctx)
    print(r["text"] or "（非物理任务，交回对话层）")
    if r.get("motion"):
        print("\n轨迹示意：")
        print(DIFF._ascii(ctx, r["motion"]["trajectory"]))


if __name__ == "__main__":
    utf8_stdio()
    if "--demo" in sys.argv:
        _demo()
    else:
        raise SystemExit(0 if _selftest() else 1)
