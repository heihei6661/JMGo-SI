"""Stable framework ↔ core contract.

Everything crossing this boundary is JSON-serializable. The framework never
imports private modules of the core, never inspects its objects, and never
calls into it more than these five methods.
"""
from __future__ import annotations

import importlib
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
        return NullCore()
