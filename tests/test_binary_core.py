"""Binary core protocol tests (POSIX only; Windows uses the same JSON lines)."""
from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from jmgo_cognition.api import BinaryCore, load_core

FAKE = r'''#!/usr/bin/env python3
import json, sys
for line in sys.stdin:
    req = json.loads(line)
    op = req.get("op")
    if op == "version":
        out = {"version": "fake-0.1", "capabilities": ["plan", "reason", "verify"]}
    elif op == "plan":
        out = {"queries": [req.get("query", "")], "slots": {}, "steps": []}
    elif op == "reason":
        out = {"answer": "fake answer", "status": "ok", "basis": [], "actions": []}
    elif op == "verify":
        out = {"ok": True, "reasons": [], "risk": "low"}
    elif op == "task":
        out = {"task": "t", "plan": {"applicable": True}, "motion": None,
               "verdict": {"ok": True}, "text": "from binary"}
    else:
        out = {"error": "unknown"}
    print(json.dumps(out, ensure_ascii=False), flush=True)
'''


@unittest.skipIf(os.name == "nt", "fake executable uses a POSIX shebang")
class BinaryCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "jmgo_core"
        cls.path.write_text(FAKE, encoding="utf-8")
        cls.path.chmod(cls.path.stat().st_mode | stat.S_IXUSR)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_protocol(self):
        core = BinaryCore(str(self.path))
        try:
            self.assertEqual(core.version()["version"], "fake-0.1")
            plan = core.plan("test", {})
            self.assertEqual(plan["queries"], ["test"])
            answer = core.reason("test", {"items": []}, {})
            self.assertEqual(answer["status"], "ok")
            self.assertTrue(core.verify(answer, {})["ok"])
            self.assertEqual(core.task("把水拿过来", {})["text"], "from binary")
        finally:
            core.close()

    def test_load_core_env(self):
        old = os.environ.get("JMGO_CORE_BIN")
        os.environ["JMGO_CORE_BIN"] = str(self.path)
        try:
            core = load_core()
            self.assertTrue(getattr(core, "installed", False))
            self.assertEqual(core.version()["version"], "fake-0.1")
            core.close()
        finally:
            if old is None:
                os.environ.pop("JMGO_CORE_BIN", None)
            else:
                os.environ["JMGO_CORE_BIN"] = old

    def test_bad_binary_falls_back(self):
        old = os.environ.get("JMGO_CORE_BIN")
        os.environ["JMGO_CORE_BIN"] = str(Path(self.tmp.name) / "missing")
        try:
            self.assertFalse(getattr(load_core(), "installed", False))
        finally:
            if old is None:
                os.environ.pop("JMGO_CORE_BIN", None)
            else:
                os.environ["JMGO_CORE_BIN"] = old


if __name__ == "__main__":
    unittest.main()
