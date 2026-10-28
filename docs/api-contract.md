# Core API Contract (v1)

The framework calls exactly five methods. All payloads are JSON-serializable;
no core objects cross the boundary.

```python
class Core(Protocol):
    installed: bool
    def version(self) -> dict
    def plan(self, query: str, ctx: dict) -> dict
    def retrieve(self, plan: dict, ctx: dict) -> dict
    def reason(self, query: str, evidence: dict, ctx: dict) -> dict
    def verify(self, answer: dict, ctx: dict) -> dict
```

## version

```json
{"version": "1.4.2",
 "capabilities": ["retrieval", "units", "robot-actions",
                  "self-evolution", "self-emotion"]}
```

Semantic version. A minor bump may add optional fields; a major bump may change
semantics. The framework warns on major mismatch and refuses to load on
incompatible majors.

## plan

Request: free text + context.

```json
{
  "queries": ["杯子 抓取", "桌面 物体"],
  "slots": {"object": "cup", "place": "table"},
  "steps": [{"id": 1, "intent": "locate", "target": "cup"}]
}
```

## retrieve

```json
{
  "items": [
    {"title": "…", "snippet": "…", "source": "https://…", "score": 0.82}
  ],
  "errors": []
}
```

Items are evidence, not answers. The core may return an empty list; the answer
status must then be `gap` or `partial`, never `ok`.

## reason

```json
{
  "answer": "建议先移动到桌边，再抓取杯子。",
  "status": "ok",
  "basis": ["object:cup@table", "clearance:0.4m"],
  "actions": [{"type": "move_to", "target": "table_edge"}]
}
```

Status values:

| status | meaning |
|---|---|
| `ok` | supported by evidence / deterministic derivation |
| `partial` | some parts missing; caveats required |
| `gap` | insufficient evidence; no action should be taken |
| `core_missing` | NullCore placeholder |

`actions` are **proposals**. They must be safe to ignore.

## verify

```json
{"ok": true, "reasons": [], "risk": "low"}
```

`ok=false` blocks execution. `risk` is one of `low|medium|high|unknown`.
A missing or failed verifier is treated as `ok=false`.

## reflect (optional, read-only)

```python
def reflect(self, result: dict, ctx: dict) -> dict
```

Called once after `verify`, with `{"answer": ..., "verdict": ...}`. It returns
sandbox self-evaluation, for example:

```json
{
  "emotion": {"valence": 0.2, "arousal": 0.1, "trigger": "reasoning_ok"},
  "quality": "good",
  "notes": ["sandbox_only"]
}
```

Guarantees:

- **Read-only**: it cannot change the answer, verdict or actions; the framework
  attaches it after the gate.
- **Failure is contained**: an exception becomes a trace entry and does not
  affect the decision.
- **No user emotion**: it evaluates the product, never the human.
- **No actuation**: it must not call actuators or write files outside the
  core's own data area.

## Evolution (offline, versioned)

Evolution is not a per-request call. It is a maintenance operation over
feedback/experience:

```
feedback → samples → induction → new rule/lexicon version → audit → rollback if needed
```

It changes **rules, experience, lexicon and weights**, never source code. The
framework only sees new rule versions via `version()` / `plan()`; the five-call
contract is unchanged.

## Errors and timeouts

- The core should raise on programming errors and return `status:"gap"` for
  data gaps.
- The framework records exceptions per step and continues with empty data.
- Respect `ctx["budget_ms"]`; return `partial` instead of blocking.

## Compatibility

- Add fields as optional; never rename existing ones within a major version.
- `jmgo_core` must expose `Core` (class or factory) and set `installed = True`.
- The framework never imports `jmgo_core.*` submodules.
