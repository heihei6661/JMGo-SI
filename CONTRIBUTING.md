# Contributing

Thanks for helping. This repository is the **open framework**; the reasoning
core (`jmgo_core`) is proprietary and not part of contributions.

## What we welcome

- Sensor / actuator adapters (ROS 2, serial, camera, audio, lidar)
- Plugins that implement the protocols in `jmgo_cognition/plugins/`
- Documentation, examples, diagrams, translations
- Contract tests that run against `NullCore`
- Bug reports with a minimal reproduction

## What we cannot accept

- Code copied from the proprietary core
- Changes that require network access at runtime
- Telemetry, analytics or "phone home" behavior
- Anything that deletes or modifies user data
- Anti-bot evasion, CAPTCHA bypass, proxy pools or fingerprint spoofing

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
python -m jmgo_cognition.cli "把桌上的杯子拿过来"
```

Keep the five-call API backward compatible. If a change needs a new field,
add it as optional and bump the minor version.

## Commit style

Conventional commits are appreciated:

```
feat(plugin): add ros2 lidar adapter
fix(loop): keep trace when verify fails
docs: clarify core boundary
```

By contributing you agree to license your contribution under AGPL-3.0-or-later,
to the Developer Certificate of Origin (sign off with `git commit -s`), and to the
short-form CLA in [CLA.md](CLA.md) (needed so the project can also offer commercial
licenses). Commercial licensing: 成都维舜骅呈科技有限公司, 2690325118@qq.com.
