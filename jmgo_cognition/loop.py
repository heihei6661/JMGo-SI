"""The cognitive loop: sense → plan → retrieve → reason → verify.

The loop is deliberately boring and inspectable: every step is a dict, every
step is timed, and nothing is executed unless the verifier allows it.
"""
from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

from .api import Core, NullCore, load_core


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


def run_loop(
    query: str,
    ctx: dict[str, Any] | None = None,
    core: Core | None = None,
    sensors: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Run one cognitive cycle and return a traceable result.

    Parameters
    ----------
    query:
        User instruction or task text, e.g. ``"把桌上的杯子拿过来"``.
    ctx:
        Free-form context (robot pose, scene id, user id, locale, budget…).
        Must be JSON-serializable if you plan to log it.
    core:
        Injected core (useful for tests). Defaults to :func:`load_core`.
    sensors:
        Optional sensor adapters. ``read()`` results are merged under
        ``ctx["sensors"]``; a sensor failure is recorded, not raised.

    Returns
    -------
    dict with ``query``, ``core``, ``plan``, ``evidence``, ``answer``,
    ``verdict``, ``actions`` and ``trace``. The loop never executes actions;
    the execution layer keeps the final veto.
    """
    core = core or load_core()
    ctx = dict(ctx or {})
    trace: list[dict[str, Any]] = []

    def step(name: str, fn, *args):
        t0 = _now_ms()
        try:
            data = fn(*args)
            status = "ok"
            err = None
        except Exception as exc:  # noqa: BLE001 - trace instead of crash
            data, status, err = None, "error", f"{type(exc).__name__}: {exc}"
        trace.append({
            "step": name,
            "status": status,
            "ms": round(_now_ms() - t0, 2),
            "error": err,
        })
        return data if status == "ok" else None

    # ① sense (optional, open layer)
    if sensors:
        observed: dict[str, Any] = {}
        for sensor in sensors:
            name = getattr(sensor, "name", type(sensor).__name__)
            data = step(f"sense:{name}", sensor.read)
            if data is not None:
                observed[name] = data
        ctx["sensors"] = observed

    # ② plan (core)
    plan = step("plan", core.plan, query, ctx) or {"queries": [query], "slots": {}, "steps": []}

    # ③ retrieve (core)
    evidence = step("retrieve", core.retrieve, plan, ctx) or {"items": [], "errors": []}

    # ④ reason (core)
    answer = step("reason", core.reason, query, evidence, ctx) or {
        "answer": "", "status": "gap", "basis": [], "actions": [],
    }

    # ⑤ verify (core) — a missing/failed verifier cannot authorize action
    verdict = step("verify", core.verify, answer, ctx) or {
        "ok": False, "reasons": ["verify_failed"], "risk": "unknown",
    }

    # ⑥ reflect (optional core capability) — sandbox self-evaluation.
    #    Read-only: it is attached after verify and can never change the
    #    verdict or the actions. A failure is traced, not raised.
    reflection = None
    if hasattr(core, "reflect"):
        reflection = step("reflect", core.reflect,
                          {"answer": answer, "verdict": verdict}, ctx)

    return {
        "query": query,
        "core": {
            "installed": bool(getattr(core, "installed", not isinstance(core, NullCore))),
            **core.version(),
        },
        "plan": plan,
        "evidence": evidence,
        "answer": answer,
        "verdict": verdict,
        "actions": answer.get("actions") or [],
        "reflection": reflection,
        "trace": trace,
    }


def apply_actions(
    result: dict[str, Any],
    actuator: Any,
    allow: bool = False,
) -> list[dict[str, Any]]:
    """Execute proposed actions **only** when explicitly allowed and verified.

    This helper exists so callers do not re-implement the safety check. Even
    then, the actuator is expected to enforce its own limits and emergency stop.
    """
    if not allow:
        return []
    if not (result.get("verdict") or {}).get("ok"):
        return []
    out = []
    for action in result.get("actions") or []:
        try:
            out.append(actuator.execute(action) or {"ok": True})
        except Exception as exc:  # noqa: BLE001 - report, never crash the loop
            out.append({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return out
