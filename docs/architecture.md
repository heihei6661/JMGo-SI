# Architecture

## One cycle

```
            ┌────────────────── open framework ───────────────────┐
sensors ──▶ │ sense ──▶ plan ──▶ retrieve ──▶ reason ──▶ verify   │ ──▶ decision
            │                                      │              │
            │                                      └─▶ reflect*   │  (read-only)
            └──────────────────────┬───────────────────────────────┘
                                   │ five-call API
                       ┌───────────▼────────────┐
                       │   proprietary core     │
                       │   skeleton / laws /    │
                       │   lexicon / reasoning /│
                       │   synthesis / security │
                       │   learning / emotion   │
                       └────────────────────────┘
```

`reflect` is optional and **read-only**: it runs after `verify` and can never
change the answer, the verdict or the actions.

- `sense` is open: any `SensorAdapter` returning a dict.
- `plan/retrieve/reason/verify` are core calls.
- The loop returns a **decision**; it does not drive motors.
- Every step is timed and traced; a failed step is recorded, not raised.

## The six core blocks (closed)

| Block | Responsibility |
|---|---|
| Skeleton | control flow, dispatch, budgets, session state |
| Laws | axiom store, conflict resolution, goal taxonomy |
| Lexicon | word/grammar/geo ledgers, growth policy |
| Reasoning | evidence → facts → conclusion, unit/year/subject gates |
| Synthesis | content plan → sentence plan → surface realization |
| Security | integrity, tamper detection, core-only destruction |
| Learning | feedback/experience → samples → induction → versioned rules/lexicon |
| Self-emotion | post-hoc evaluation of the **product** (valence/arousal/trigger) |

### Learning loop (closed)

- Evolves **rules, experience, lexicon and weights**, never source code.
- Every change is versioned, sourced and reversible.
- Offline: no cloud training, no upload of user text by default.
- Robot effect: policies get more stable over time; execution limits and the
  emergency stop are unchanged.

### Self-emotion (closed, hard-isolated)

- Evaluated **after** reasoning, on the produced answer, not on the user.
- Effects are whitelisted: tone, quality label, log line.
- Never participates in syntax, entities, intent, dispatch, retrieval,
  evidence, verification or actions.
- Failure samples may enter the learning pool, **without** emotion numbers.

## The open layer

- adapters for sensors and actuators;
- the CLI/HTTP shell;
- plugin protocols;
- docs, schemas and contract tests;
- a `NullCore` so the framework is runnable and testable on its own.

## Failure model

| Failure | Behavior |
|---|---|
| core missing | `NullCore`, status `core_missing`, verifier refuses actions |
| sensor raises | trace entry `error`, cycle continues |
| core raises | step `error`, downstream sees empty data, verifier blocks |
| verifier rejects | decision returned, actions not executed |
| reflect raises | trace entry `error`; answer/verdict/actions unchanged |
| evolution conflict | keep current rule version, surface the conflict |
| tampered core | core disables itself (see `docs/security.md`) |

## Budgets

Put a wall-clock budget in `ctx["budget_ms"]` and enforce it in the execution
layer. The open loop does not silently extend deadlines; the core is expected
to return `partial` rather than block forever.
