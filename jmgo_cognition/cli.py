"""Command-line demo for the open framework.

Examples
--------
    python -m jmgo_cognition.cli "把桌上的杯子拿过来"
    python -m jmgo_cognition.cli --json "巡检 A 区，发现异常就停下"
    python -m jmgo_cognition.cli --require-core "回到充电桩"
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .api import load_core
from .loop import run_loop


def _print_human(result: dict[str, Any]) -> None:
    core = result.get("core") or {}
    print(f"core: {core.get('version', '?')} (installed={core.get('installed')})")
    print(f"query: {result.get('query')}")
    plan = result.get("plan") or {}
    if plan.get("queries"):
        print(f"plan: {', '.join(map(str, plan['queries']))}")
    evidence = result.get("evidence") or {}
    print(f"evidence: {len(evidence.get('items') or [])} item(s)")
    answer = result.get("answer") or {}
    print(f"answer[{answer.get('status', '?')}]: {answer.get('answer', '')}")
    verdict = result.get("verdict") or {}
    print(f"verify: ok={verdict.get('ok')} risk={verdict.get('risk', '?')}")
    if result.get("actions"):
        print(f"proposed actions: {json.dumps(result['actions'], ensure_ascii=False)}")
    reflection = result.get("reflection")
    if reflection and reflection.get("emotion"):
        print(f"self-eval (read-only): {json.dumps(reflection['emotion'], ensure_ascii=False)}")
    print("trace:")
    for item in result.get("trace") or []:
        err = f" error={item['error']}" if item.get("error") else ""
        print(f"  - {item['step']:<22} {item['status']:<6} {item['ms']:>7.2f} ms{err}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jmgo-cognition",
        description="Offline cognitive loop demo (open framework).",
    )
    parser.add_argument("query", nargs="+", help="task or instruction text")
    parser.add_argument("--json", action="store_true", help="print the full trace as JSON")
    parser.add_argument("--ctx", default="{}", help="JSON object merged into the context")
    parser.add_argument("--require-core", action="store_true",
                        help="exit 1 when the proprietary core is not installed")
    args = parser.parse_args(argv)

    try:
        ctx = json.loads(args.ctx)
        if not isinstance(ctx, dict):
            raise ValueError("--ctx must be a JSON object")
    except Exception as exc:  # noqa: BLE001
        print(f"invalid --ctx: {exc}", file=sys.stderr)
        return 2

    core = load_core()
    result = run_loop(" ".join(args.query), ctx=ctx, core=core)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)

    if args.require_core and not result["core"].get("installed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
