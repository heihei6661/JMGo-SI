# -*- coding: utf-8 -*-
"""action_render.py —— 文本渲染层：把“任务拆解 + 动作块 + 安全结论”讲成人话。

原则：
  · 不贴 JSON、不贴轨迹数组；
  · 先讲步骤（为什么这个顺序），再讲动作块结论，最后讲缺口/未执行；
  · 不冒充执行：只输出“计划”，执行权在执行层。
"""
from __future__ import annotations

import math
from typing import Any

_REASON_ZH = {
    "collision": "会撞到障碍",
    "step_limit": "单步超过限幅",
    "goal_not_reached": "一个动作块到不了目标",
    "out_of_bounds": "越出工作空间",
    "start_moved": "起点被改动",
    "non_finite": "轨迹出现非法数值",
    "bad_shape": "轨迹形状不合法",
}


def _max_step(motion: dict[str, Any]) -> float:
    acts = motion.get("actions") or []
    return max((math.hypot(a[0], a[1]) for a in acts), default=0.0)


def render(
    plan: dict[str, Any],
    motion: dict[str, Any] | None = None,
    verdict: dict[str, Any] | None = None,
    executed: bool = False,
) -> str | None:
    """返回中文说明；非物理任务/无计划 → None（交回对话层）。"""
    if not plan or not plan.get("applicable"):
        return None
    steps = plan.get("steps") or []
    if not steps:
        return None

    lines = [f"把「{plan.get('task', '')}」拆成 {len(steps)} 步（按前置条件排序）："]
    for s in steps:
        lines.append(f"{s.get('id')}. {s.get('label')}")

    missing = plan.get("missing") or []
    if missing:
        lines.append("还缺：" + "、".join(missing) + "；补上后再重规划，先不动。")

    if motion is not None:
        n = len(motion.get("actions") or [])
        ms = _max_step(motion)
        if verdict and verdict.get("ok"):
            lines.append(
                f"动作块：{n} 个增量，最大步长 {ms:.2f} m；"
                "安全闸通过（无碰撞、不越界、终点在容差内）。"
            )
        else:
            reasons = (verdict or {}).get("reasons") or ["unknown"]
            zh = "、".join(_REASON_ZH.get(r, r) for r in reasons)
            lines.append(f"动作块：{n} 个增量；安全闸未通过（{zh}），不执行。")

    if executed:
        lines.append("执行层已受理；急停与限幅仍然生效。")
    else:
        lines.append("以上是计划，尚未执行；执行层保留限幅与急停。")
    return "\n".join(lines)


if __name__ == "__main__":
    plan = {
        "task": "把桌上的杯子拿过来",
        "applicable": True,
        "steps": [
            {"id": 1, "label": "定位「杯子」"},
            {"id": 2, "label": "移动到可操作「杯子」的位姿"},
            {"id": 3, "label": "抓取「杯子」"},
            {"id": 4, "label": "确认「杯子」状态符合预期"},
            {"id": 5, "label": "把「杯子」送到「用户/交付点」"},
        ],
        "missing": [],
    }
    motion = {"actions": [[0.3, 0.1]] * 8}
    ok = 0
    t1 = render(plan, motion, {"ok": True, "reasons": []})
    ok += bool(t1 and "5 步" in t1 and "安全闸通过" in t1 and "{" not in t1)
    print("① 正常计划 →\n" + t1)

    t2 = render(plan, motion, {"ok": False, "reasons": ["collision", "step_limit"]})
    ok += bool(t2 and "未通过" in t2 and "会撞到障碍" in t2 and "单步超过限幅" in t2)
    print("\n② 安全闸失败 →\n" + t2)

    p3 = dict(plan, missing=["杯子的位姿"])
    t3 = render(p3)
    ok += bool(t3 and "还缺" in t3 and "杯子的位姿" in t3)
    print("\n③ 缺口 →\n" + t3)

    ok += render({"applicable": False}) is None
    print("\n④ 非物理任务 → None")

    ok += bool(t1 and "尚未执行" in t1)
    t5 = render(plan, motion, {"ok": True, "reasons": []}, executed=True)
    ok += bool(t5 and "已受理" in t5 and "急停" in t5)
    print("⑤ 未执行/已受理话术 →", "尚未执行" in t1, "已受理" in t5)

    ok += bool(t1 and "[" not in t1 and "{" not in t1)
    print("⑥ 不贴 JSON/数组 →", "[" not in t1 and "{" not in t1)

    n = int(ok)
    total = 7
    print(f"\n== 判定汇总：{n}/{total} ==")
    print(f"PASS {n}/{total}" if n == total else "FAIL")
