# Security & Core Protection

## Posture

- **Offline by default**: no telemetry, no license heartbeat, no phone-home.
- **Local integrity check only**: the core verifies itself once at startup.
- **Core-only destruction**: tampering may delete core artifacts and cache.
  It never touches user data, logs, projects or backups.
- **No remote trigger**: there is no admin port and no inbound command channel.

## Tamper signals (2-of-3)

1. core file hashes differ from the signed manifest;
2. a debugger/tracer is attached (`sys.gettrace`, `PYTHONINSPECT`, `sys.flags.debug`);
3. dynamic library injection (`DYLD_INSERT_LIBRARIES`, `LD_PRELOAD`).

Two independent signals are required, to avoid false positives from antivirus,
profiling tools or OS updates.

## What destruction means

- zeroize in-memory key material;
- delete the core's own cache and, by default, `core/` artifacts;
- remove the core manifest and local key;
- write a `TAMPERED` marker and refuse to load.

Explicitly **not** allowed: deleting user files, databases, logs, backups;
network beacons; spawning processes; remote wipe of other machines.

## Recovery

Reinstall the core wheel, or run the guard's `reset --force` in a trusted
environment. The message shown to users must say the data was not deleted.

## Reporting

See `SECURITY.md`. Do not open public issues for bypasses or data-loss bugs.
