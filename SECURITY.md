# Security Policy

## Reporting

Please report vulnerabilities privately to 2690325118@qq.com. Do **not** open a public issue for:

- sandbox escapes or code execution;
- core tamper-detection bypass;
- data loss or destructive behavior;
- credential or key exposure.

We aim to acknowledge within 7 days and to ship a fix or mitigation within
30 days for confirmed issues.

## Runtime posture

- The framework makes **no network calls by default**; no telemetry, no
  license heartbeat, no phone-home.
- The proprietary core performs a **local** integrity check at startup only.
- If the core detects tampering (2-of-3 signals), it disables/destroys **its own
  artifacts and cache only**. It never deletes user data, logs, projects or
  backups. Recovery is reinstalling the core package.
- The framework does not send control commands to hardware; the execution
  layer keeps the final veto and emergency stop.

## Supported versions

Only the latest minor release receives security fixes during the preview
phase.
