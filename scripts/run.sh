#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$project_root/local/toolchains/bin:$project_root/local/toolchains/node-v24.21.0-darwin-arm64/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export UV_CACHE_DIR="$project_root/local/cache/uv"
export UV_PYTHON_INSTALL_DIR="$project_root/local/toolchains/python"
export npm_config_cache="$project_root/local/cache/npm"
cd "$project_root"
exec "$@"
