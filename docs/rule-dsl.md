# Rule DSL (specification)

The evaluator is proprietary; the rule format is open so teams can author,
review and version rules. Rules are data, not code.

## Shape

```json
{
  "id": "safety.battery.low",
  "version": 3,
  "scope": ["robot", "safety"],
  "priority": 100,
  "when": {
    "all": [
      {"fact": "battery.level", "op": "<", "value": 0.15},
      {"fact": "robot.docked", "op": "==", "value": false}
    ]
  },
  "then": {
    "conclusion": "battery_low",
    "action": {"type": "dock", "reason": "battery_low"},
    "confidence": 0.95
  },
  "source": "ops-handbook-v2",
  "notes": "Safety rule; overrides productivity rules."
}
```

## Operators

`== != < <= > >= in not_in matches exists`

`all` / `any` / `not` compose conditions. Facts are dotted paths into the
context or into derived facts produced by the core.

## Priority and conflict resolution

1. **Safety scope wins** over productivity, regardless of priority.
2. Higher `priority` wins inside the same scope.
3. More specific rules (more conditions) win over generic ones.
4. If still tied, higher `confidence` wins; if equal, the newer `version` wins.
5. Unresolved conflicts are surfaced in `verify.reasons`; the action is blocked.

The evaluator is deterministic: same facts + same rules → same result.

## Authoring rules

- One behavior per rule; keep conditions explicit.
- Never encode secrets or user data in a rule.
- Add `notes` and `source`; rules are audited.
- Bump `version` on behavior changes; keep old versions for replay.
- Safety rules must have a conservative default (stop / hold / ask).

## Testing

Provide a fixture: `{facts, rules, expected_conclusion, expected_action}`.
The open repo ships fixtures and a schema validator; the closed core runs them.
