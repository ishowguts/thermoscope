#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$project_root/local/toolchains/bin:$project_root/local/toolchains/node-v24.21.0-darwin-arm64/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export UV_CACHE_DIR="$project_root/local/cache/uv"
export UV_PYTHON_INSTALL_DIR="$project_root/local/toolchains/python"
export npm_config_cache="$project_root/local/cache/npm"
# macOS: the XGBoost wheel finds Homebrew's OpenMP runtime (libomp) only under /opt/homebrew. When
# Homebrew lives elsewhere (for example ~/.homebrew), let dyld fall back to that libomp. macOS drops
# DYLD_* variables when a system shell starts, so it is set here, just before exec.
if [ "$(uname -s)" = Darwin ] && [ ! -f /opt/homebrew/opt/libomp/lib/libomp.dylib ]; then
    for prefix in "${HOMEBREW_PREFIX:-}" "$HOME/.homebrew" "$HOME/homebrew" /usr/local; do
        if [ -n "$prefix" ] && [ -f "$prefix/opt/libomp/lib/libomp.dylib" ]; then
            export DYLD_FALLBACK_LIBRARY_PATH="$prefix/opt/libomp/lib:/usr/local/lib:/usr/lib"
            break
        fi
    done
fi
cd "$project_root"
exec "$@"
