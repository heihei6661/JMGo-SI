#!/usr/bin/env bash
# Install the proprietary core binary from GitHub Releases.
set -euo pipefail

VERSION="${JMGO_CORE_VERSION:-0.1.0}"
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS/$ARCH" in
  Darwin/arm64)   ASSET="macos-arm64" ;;
  Darwin/x86_64)  ASSET="macos-x86_64" ;;
  Linux/x86_64)   ASSET="linux-x86_64" ;;
  Linux/aarch64)  ASSET="linux-arm64" ;;
  *) echo "unsupported platform: $OS/$ARCH" >&2; exit 1 ;;
esac

BASE="https://github.com/heihei6661/JMGo-SI/releases/download/v${VERSION}"
FILE="jmgo_core-${VERSION}-${ASSET}.tar.gz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "downloading $FILE ..."
curl -fL "$BASE/$FILE" -o "$TMP/$FILE"
curl -fL "$BASE/SHA256SUMS" -o "$TMP/SHA256SUMS"
( cd "$TMP" && grep " $FILE\$" SHA256SUMS | shasum -a 256 -c - )

mkdir -p "$HOME/.jmgo/core/$VERSION" "$HOME/.jmgo/bin"
tar -xzf "$TMP/$FILE" -C "$HOME/.jmgo/core/$VERSION" --strip-components=1
chmod +x "$HOME/.jmgo/core/$VERSION/jmgo_core"
ln -sf "$HOME/.jmgo/core/$VERSION/jmgo_core" "$HOME/.jmgo/bin/jmgo_core"

echo "installed: $HOME/.jmgo/bin/jmgo_core"
echo "verify:    jmgo-cognition --json \"把桌上的杯子拿过来\""
