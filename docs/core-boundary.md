# Open Core Boundary

## What is open (AGPL-3.0-or-later)

- cognitive loop and plugin protocols;
- sensor/actuator adapters, ROS 2 bridge;
- CLI/HTTP shell;
- docs, schemas, contract tests;
- `NullCore` reference.

## What is closed (proprietary binary)

- skeleton/orchestration implementation;
- axiom compiler and evaluator;
- full lexicon/ledgers and growth policy;
- reasoning and synthesis engines;
- retrieval/evidence policy that is not purely mechanical;
- security engine;
- learning loop (self-evolution of rules/experience/lexicon);
- self-emotion (sandbox evaluation, read-only).

## Why

The closed parts are the compounding assets: they encode years of rules,
evidence gates and failure cases. The open parts are the integration surface.
Closing the surface would kill adoption; opening the engine would erase the
advantage.

## Rules for the boundary

1. Five required calls + one optional read-only `reflect`; JSON in/out, no
   private imports.
2. No callbacks from core into framework internals.
3. No network requirement to use the core.
4. The core may not delete user data, logs, projects or backups.
5. Version the contract; keep a changelog for schema changes.
6. Self-evolution never rewrites source code, and self-emotion never gates an
   action. Both are auditable and reversible.

## Delivery

- `jmgo_core` as platform wheels (`cp310`–`cp312`, macOS arm64/x86_64, Linux,
  Windows), built in CI and signed.
- Public type stubs in `core-stubs/` so the framework and IDEs see the contract.
- License: proprietary EULA; not covered by AGPL-3.0-or-later.

## Third-party data

UD treebanks, GeoNames and zhconv keep their own licenses. Do not relicense
them as proprietary. If a ledger includes such data, ship it under the
original terms or keep it out of the binary.
