# Robot Integration

## Design rule

> Cognition proposes; execution disposes.

The cognitive loop returns a decision (`answer`, `verdict`, `actions`). A
separate execution node applies limits, checks the emergency stop, and decides
whether to move. Never wire `actions` straight into motor drivers.

## Mapping perception into context

`ctx` is a plain dict. Suggested keys:

```json
{
  "robot": {"id": "arm-01", "pose": [0.0, 0.0, 0.0], "battery": 0.62},
  "scene": {"id": "kitchen-3", "objects": [{"label": "cup", "xyz": [0.4, 0.1, 0.8]}]},
  "human": {"present": true, "distance_m": 1.2},
  "locale": "zh-CN",
  "budget_ms": 800
}
```

Keep it small and JSON-serializable. Summarize high-rate sensor streams (do not
paste 30 Hz point clouds); the core reasons over structured facts.

## ROS 2 topics

| Topic | Type | Direction |
|---|---|---|
| `/perception/objects` | `vision_msgs/Detection3DArray` | in |
| `/perception/asr` | `std_msgs/String` | in |
| `/odom` | `nav_msgs/Odometry` | in |
| `/cognition/request` | `std_msgs/String` (JSON) | in |
| `/cognition/decision` | `std_msgs/String` (JSON) | out |

`examples/ros2_bridge.py` is a template. It publishes a decision, not a
trajectory.

## Rates and budgets

- Perception: 10–30 Hz (outside the loop).
- Cognition: 1–5 Hz, or event-triggered (new object, new instruction).
- Set `ctx["budget_ms"]`; on timeout return `partial` and let execution hold
  position.
- Cache the last stable scene summary; do not re-plan on every frame.

## Safety

1. **Stale data**: if the newest observation is older than N ms, treat the
   cycle as `gap`; do not act.
2. **Uncertainty**: `verify` must return `ok=false` when the target is
   ambiguous or a human is inside the workspace.
3. **E-stop**: hardware/software emergency stop always wins, independent of
   the cognitive loop.
4. **Limits**: velocity/force limits live in the execution layer, not in the
   core.
5. **Audit**: log the trace (step, status, ms) for every executed decision.

## Self-evaluation and evolution

- `reflect()` (optional) returns a **read-only** self-evaluation: sandbox
  valence/arousal, quality label, notes. It runs after `verify`.
- Do **not** wire it to motion. It must not change the verdict, the actions or
  the emergency stop. Log it; use it for offline tuning.
- Evolution happens between runs: feedback/experience → new rule/lexicon
  versions → audit → rollback if needed. It never rewrites source code and
  never changes the execution layer's limits.
- For fleet deployment, version the rule set per robot and keep the previous
  version for replay.

## Offline behavior

The framework and core run without network. If a task needs external
knowledge, the core returns `partial`/`gap` with a reason; the robot should
degrade to a safe behavior rather than wait indefinitely.

## Integration checklist

- [ ] Sensors return dicts; failures are caught and traced.
- [ ] `ctx` includes pose, scene summary, human presence, budget.
- [ ] Actions are proposals; execution enforces limits + e-stop.
- [ ] Stale/ambiguous inputs lead to `gap`, not motion.
- [ ] Decision + trace are logged.
