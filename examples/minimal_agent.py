"""Minimal embodied agent: sense → think → verify → (optionally) act.

Run:
    python examples/minimal_agent.py
    python examples/minimal_agent.py "把桌上的杯子拿过来"
"""
from __future__ import annotations

import json
import sys

from jmgo_cognition import load_core, run_loop
from jmgo_cognition.loop import apply_actions
from jmgo_cognition.plugins import EchoSensor, LogActuator


def main() -> int:
    query = " ".join(sys.argv[1:]) or "把桌上的杯子拿过来"

    core = load_core()
    if not getattr(core, "installed", False):
        print("[agent] 核心未安装，运行框架演示。安装 jmgo_core 后可得到真实推演。")

    # A real robot would replace these with camera/lidar/asr adapters.
    sensor = EchoSensor({"text": query, "objects": [{"label": "cup", "x": 0.4, "y": 0.1}]})
    actuator = LogActuator()

    result = run_loop(query, core=core, sensors=[sensor],
                      ctx={"robot": "demo-arm", "locale": "zh-CN"})

    print("\n== answer ==")
    print(result["answer"].get("answer", ""))
    print("\n== verdict ==")
    print(json.dumps(result["verdict"], ensure_ascii=False))

    # Execution stays opt-in and gated. The real actuator must also enforce
    # limits and the emergency stop.
    executed = apply_actions(result, actuator, allow=False)
    print("\n== executed ==")
    print(json.dumps(executed, ensure_ascii=False) or "[] (execution disabled by default)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
