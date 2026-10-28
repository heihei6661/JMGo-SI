# Changelog

## 0.1.0 (unreleased)

- Initial open framework: five-call core API, NullCore, cognitive loop, CLI.
- Plugin protocols for sensors and actuators.
- Contract tests that run without the proprietary core.
- Docs: architecture, API contract, core boundary, rule DSL, vocabulary and
  answer schemas, robot integration.
- Security posture: offline by default, local-only core integrity check,
  core-only self-destruction.
- Optional read-only `reflect()` hook: sandbox self-emotion and quality notes,
  isolated from answer/verdict/actions (with failure containment tests).
- Documented self-evolution: versioned rules/experience/lexicon, no source
  rewriting, offline and reversible.
