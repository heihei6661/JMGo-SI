# Core Binary (v0.1)

The reasoning core ships as a standalone binary, downloaded from GitHub
Releases. The framework discovers it automatically and talks to it over JSON
Lines (one request per line).

## What the v0.1.1 binary does

| op | behavior |
|---|---|
| `version` | version + capabilities |
| `plan` | query planning (1–2 term queries, slots) |
| `reason` | evidence → answer (units/years/subject gates) |
| `verify` | gate the answer (`ok` / `gap`) |
| `task` | task decomposition → diffusion motion → safety gate → rendered text |
| `retrieve` | returns empty in v0.1; retrieval is open, in `retrieval.py` |

Keeping retrieval in the open framework keeps the binary small (no 150 MB
geodata, no browser stack) and lets teams swap in an internal index or a
robot's local knowledge base.

## Install

```bash
bash scripts/install_core.sh          # macOS / Linux
pwsh scripts/install_core.ps1         # Windows
```

Installs to `~/.jmgo/bin/jmgo_core` (Windows: `jmgo_core.exe`). Override with:

```bash
export JMGO_CORE_BIN=/path/to/jmgo_core
```

The framework falls back to `NullCore` when the binary is missing or fails its
version handshake, so installation problems never crash the loop.

## Protocol

```json
{"op":"plan","query":"2024年中国GDP是多少"}
{"queries":["2024年 GDP","中国 GDP"],"slots":{},"steps":[]}
```

```json
{"op":"reason","query":"2024年中国GDP是多少","subject":"中国GDP",
 "evidence":{"items":[{"title":"2024年，中国GDP为134.91万亿。"}]}}
{"answer":"2024 年中国GDP约 134.91万亿元。","status":"ok","basis":[],"actions":[]}
```

```json
{"op":"task","task":"把桌上的水拿过来",
 "ctx":{"start":[0,0],"goal":[6,4],"obstacles":[],"horizon":22}}
{"plan":{...},"motion":{...},"verdict":{"ok":true},"text":"把「把桌上的水…」拆成 4 步…"}
```

Unknown ops return `{"error": ...}`; the framework treats that as a failed step.

## Platforms and assets

```
jmgo_core-0.1.1-macos-arm64.tar.gz
jmgo_core-0.1.1-macos-x86_64.tar.gz
jmgo_core-0.1.1-linux-x86_64.tar.gz
jmgo_core-0.1.1-windows-x86_64.zip
SHA256SUMS
```

macOS arm64 is built locally with Nuitka. Linux/Windows are built by the
private core CI (the source is not in the public repository) and uploaded to
the same public release.

## Security posture

- Compiled with Nuitka (C), stripped; no Python source in the archive.
- Optional integrity guard: 2-of-3 signals (hash/debugger/injection) →
  disable and destroy **core artifacts only**; user data is never touched.
- Public download ≠ public source. Commercial use requires a license
  (`COMMERCIAL.md`); AGPL compliance is the alternative.
- Self-protection is deterrence, not DRM; a determined attacker can patch it.

## Build (maintainers)

```bash
cd logic
python -m nuitka --standalone --assume-yes-for-downloads \
  --include-data-files=ud_grammar.json=ud_grammar.json \
  core_entry.py
# rename core_entry → jmgo_core, tar, sign, upload
```

Linux/Windows builds run in a private repository with the same entry point.
