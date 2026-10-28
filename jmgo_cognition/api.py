"""Stable framework ↔ core contract.

Everything crossing this boundary is JSON-serializable. The framework never
imports private modules of the core, never inspects its objects, and never
calls into it more than these five methods.
"""
from __future__ import annotations

import contextlib
import importlib
import json
import os
import subprocess
import threading
from typing import Any, Protocol, runtime_checkable


class CoreUnavailable(RuntimeError):
    """Raised when a strict core load is requested but the core is missing."""


@runtime_checkable
class Core(Protocol):
    """The only surface the framework depends on. Versioned as a whole."""

    installed: bool

    def version(self) -> dict[str, Any]:
        """Return ``{"version": str, "capabilities": [str, ...]}``."""

    def plan(self, query: str, ctx: dict[str, Any]) -> dict[str, Any]:
        """Turn a request into a plan.

        Returns ``{"queries": [str], "slots": dict, "steps": [dict]}``.
        """

    def retrieve(self, plan: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        """Collect evidence for a plan.

        Returns ``{"items": [{"title", "snippet", "source"}], "errors": [str]}``.
        """

    def reason(
        self,
        query: str,
        evidence: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Derive an answer from evidence.

        Returns ``{"answer": str, "status": str, "basis": [str],
        "actions": [dict]}``. ``status`` is one of ``ok``, ``partial``,
        ``gap``, ``core_missing``.
        """

    def verify(self, answer: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        """Gate the answer / proposed actions.

        Returns ``{"ok": bool, "reasons": [str], "risk": str}``.
        """


@runtime_checkable
class ReflectiveCore(Protocol):
    """Optional capability: evaluate the **product**, after the decision.

    A reflective core may report a sandbox self-emotion (valence/arousal/
    trigger) and quality notes. The framework records it read-only; it must
    never change the answer, the verdict or the actions.
    """

    def reflect(self, result: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        """Return ``{"emotion": {...}, "quality": str, "notes": [...]}``."""


class BinaryCore:
    """Five-call adapter for the proprietary core binary (JSON Lines).

    Discovered via ``JMGO_CORE_BIN`` or ``~/.jmgo/bin/jmgo_core``. Retrieval
    stays in the open framework; the binary does plan/reason/verify.
    """

    installed = True

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._start()

    def _start(self) -> None:
        self._proc = subprocess.Popen(
            [self.path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

    def _stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        with contextlib.suppress(OSError):
            proc.kill()
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            proc.wait(timeout=2)
        for stream in (proc.stdin, proc.stdout):
            if stream is not None:
                with contextlib.suppress(OSError):
                    stream.close()

    def _call(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for attempt in (0, 1):
                try:
                    if self._proc is None or self._proc.poll() is not None:
                        self._start()
                    assert self._proc is not None
                    assert self._proc.stdin is not None and self._proc.stdout is not None
                    self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    self._proc.stdin.flush()
                    line = self._proc.stdout.readline()
                    if not line:
                        raise RuntimeError("core closed the stream")
                    return json.loads(line)
                except Exception:
                    self._stop()
                    if attempt:
                        raise
        raise CoreUnavailable("core call failed")

    def version(self) -> dict[str, Any]:
        return self._call({"op": "version"})

    def plan(self, query: str, ctx: dict[str, Any]) -> dict[str, Any]:
        return self._call({"op": "plan", "query": query,
                           "subject": (ctx or {}).get("subject")})

    def retrieve(self, plan: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        from .retrieval import search
        queries = [q for q in ((plan or {}).get("queries") or []) if q][:3]
        items: list[dict[str, Any]] = []
        errors: list[str] = []
        seen: set[str] = set()
        if queries:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(queries)) as ex:
                results = list(ex.map(lambda q: search(q, limit=4), queries))
        else:
            results = []
        for res in results:
            errors.extend(res.get("errors") or [])
            for it in res.get("items") or []:
                key = (it.get("title") or "").strip()
                if key and key not in seen:
                    seen.add(key)
                    items.append(it)
        return {"items": items[:8], "errors": errors[:3]}

    def reason(self, query: str, evidence: dict[str, Any],
               ctx: dict[str, Any]) -> dict[str, Any]:
        return self._call({"op": "reason", "query": query,
                           "subject": (ctx or {}).get("subject"),
                           "goal": (ctx or {}).get("goal"),
                           "evidence": evidence or {}})

    def verify(self, answer: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        return self._call({"op": "verify", "answer": answer or {}})

    def task(self, task: str, ctx: dict[str, Any]) -> dict[str, Any]:
        """Optional: decomposition + diffusion + rendering inside the binary."""
        return self._call({"op": "task", "task": task, "ctx": ctx or {}})

    def reflect(self, result: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        return {"available": False, "emotion": None, "notes": ["binary_core"]}

    def close(self) -> None:
        self._stop()

    def __del__(self) -> None:  # pragma: no cover - best effort
        self._stop()


class NullCore:
    """Framework demo core. It never invents an answer and never acts."""

    installed = False

    def version(self) -> dict[str, Any]:
        return {"version": "null", "capabilities": []}

    def plan(self, query: str, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"queries": [query], "slots": {}, "steps": []}

    def retrieve(self, plan: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        return {"items": [], "errors": ["core_missing"]}

    def reason(
        self,
        query: str,
        evidence: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "answer": (
                "核心未安装：当前运行的是框架演示（NullCore）。"
                "请安装 jmgo_core 后重试。"
            ),
            "status": "core_missing",
            "basis": [],
            "actions": [],
        }

    def verify(self, answer: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        # A missing core can never authorize an action.
        return {"ok": False, "reasons": ["core_missing"], "risk": "unknown"}

    def reflect(self, result: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        return {"available": False, "emotion": None,
                "notes": ["core_missing"]}


def _binary_path() -> str | None:
    env = os.environ.get("JMGO_CORE_BIN")
    exe = "jmgo_core.exe" if os.name == "nt" else "jmgo_core"
    if env:
        # Explicit override wins: never silently use a different binary.
        return env if os.path.isfile(env) else None
    cands = []
    cands.append(os.path.expanduser(os.path.join("~", ".jmgo", "bin", exe)))
    cands.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "core", exe))
    for p in cands:
        if p and os.path.isfile(p):
            return p
    return None


def load_core(strict: bool = False) -> Core:
    """Import the proprietary core if present.

    The core package must expose a zero-argument factory named ``Core`` (or a
    module-level object) and implement :class:`Core`. Any import or contract
    failure falls back to :class:`NullCore` unless ``strict=True``.
    """
    try:
        mod = importlib.import_module("jmgo_core")
        factory = getattr(mod, "Core", None)
        if factory is None:
            raise CoreUnavailable("jmgo_core does not expose Core")
        core = factory() if callable(factory) else factory
        if not isinstance(core, Core):
            raise CoreUnavailable("jmgo_core.Core does not implement the contract")
        return core
    except Exception as exc:
        if strict:
            raise CoreUnavailable(str(exc)) from exc

    path = _binary_path()
    if path:
        try:
            core = BinaryCore(path)
            core.version()          # handshake: reject a broken binary
            return core
        except Exception as exc:
            if strict:
                raise CoreUnavailable(f"binary core failed: {exc}") from exc
    return NullCore()
