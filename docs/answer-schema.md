# Answer Object

`reason()` returns one object; `verify()` gates it. The same shape is used for
robot decisions and chat answers.

```json
{
  "answer": "建议先移动到桌边，再抓取杯子。",
  "status": "ok",
  "basis": ["object:cup@table", "clearance:0.4m"],
  "actions": [{"type": "move_to", "target": "table_edge"}],
  "caveats": []
}
```

## Status

| status | meaning | execution |
|---|---|---|
| `ok` | evidence-backed / deterministic | allowed if `verify.ok` |
| `partial` | some facts missing | allowed only for safe, reversible actions |
| `gap` | insufficient evidence | blocked |
| `core_missing` | NullCore | blocked |

## Rules

1. **No fabrication**: every claim in `answer` must trace to `basis` or a
   deterministic calculation.
2. **Units and years**: state them explicitly; if the requested year/unit is
   missing, return `partial` or `gap`, do not substitute silently.
3. **Actions are proposals**: must be safe to ignore; no side effects at
   construction time.
4. **Caveats are visible**: uncertainty goes in `caveats`, not hidden in prose.
5. **Stable ids**: action `type` strings are part of the contract.

## Examples

Partial:

```json
{
  "answer": "只取到 2025 年的值（19498 亿美元），不拿它当 2023 年的答案。",
  "status": "partial",
  "basis": ["year:2025"],
  "actions": [],
  "caveats": ["requested_year_missing:2023"]
}
```

Gap:

```json
{
  "answer": "缺少目标物体的位姿，无法规划抓取。",
  "status": "gap",
  "basis": [],
  "actions": [],
  "caveats": ["missing:object_pose"]
}
```
