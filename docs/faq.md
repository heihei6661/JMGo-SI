# FAQ

**Is this open source?**
The framework is AGPL-3.0-or-later. The reasoning core (`jmgo_core`) is proprietary and
distributed as a binary wheel. This is an open-core project, not a fully open
source one.

**Does it self-evolve its source code?**
No. It evolves **rules, experience, lexicon and weights** from feedback, with
versioning and rollback. Source code is never rewritten at runtime.

**Does it need network access for evolution?**
No. Evolution is local and offline; user text is not uploaded by default.

**Does it detect my emotions?**
No. The self-emotion is a **sandbox self-evaluation of the product** (was this
answer good? was evidence enough?), not a user emotion classifier.

**Does emotion affect robot behavior?**
No. `reflect()` runs after verification and is read-only: it cannot change the
answer, the verdict or the actions. It is for logs, tone and quality labels.
Use it for offline tuning, not for motion.

**Does it need network access?**
No. The loop and the core run offline. There is no telemetry, no license
heartbeat, no phone-home.

**Can I use it commercially?**
The framework is AGPL-3.0-or-later. You may use it commercially if you comply with
the AGPL (including source disclosure for network use). If you cannot comply,
you need a written commercial license from 成都维舜骅呈科技有限公司
(2690325118@qq.com). The proprietary core always requires a commercial license.
See `COMMERCIAL.md`.

**Why is the core closed?**
It is the compounding asset (laws, evidence gates, reasoning, synthesis). The
integration surface stays open so the ecosystem can extend it without
reimplementing the engine.

**Can I add my own sensors/actuators?**
Yes. Implement `SensorAdapter`/`ActuatorAdapter` and register them. See
`examples/minimal_agent.py`.

**Does it control my robot directly?**
No. It returns decisions and proposed actions. Your execution layer keeps the
final veto, limits and emergency stop.

**What happens if the core is tampered with?**
The core verifies itself locally at startup. On two independent tamper signals
it disables/destroys **its own artifacts and cache only**. User data, logs,
projects and backups are never touched. Reinstall the core to recover.

**Which platforms are supported?**
macOS arm64/x86_64, Linux x86_64, Windows x86_64; Python 3.10–3.12. The core is
built per platform/Python version.

**Can I run it without the core?**
Yes, with `NullCore`: the loop runs, answers report `core_missing`, and the
verifier blocks actions. This is useful for integration and CI.

**How do I report a security issue?**
Privately, per `SECURITY.md`. Do not open a public issue.
