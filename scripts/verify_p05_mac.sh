#!/bin/bash
# Verify a ThermoScope branch on macOS in an isolated clone (written for P05; bash 3.2 compatible).
#
#   cd "<your ThermoScope checkout>" && bash local/p05-verify/verify_p05_mac.sh
#
# Expects local/p05-verify/branch.bundle and local/p05-verify/expected-sha.txt next to this
# script. It never changes the main checkout's tracked files, uncommitted edits or database: it
# clones the checkout's committed history into local/p05-verify/clone, adds the bundled branch,
# reuses the checkout's pinned toolchains and download caches (new downloads may be added to the
# ignored local/cache, or local/toolchains if a pinned runtime is missing), copies only the
# DATABASE_URL line of .env (never printed), and runs make install, make install-ml, an
# XGBoost/OpenMP probe, make check and make integration (which creates and drops its own
# disposable databases). Nothing is installed system-wide. The report is written to
# local/p05-verify/report.txt with configured secrets redacted, also if the run is interrupted.
set -u
MAIN="$(pwd)"
HERE="$MAIN/local/p05-verify"
DEST="$HERE/clone"
REPORT="$HERE/report.txt"
RAW="$HERE/.report.raw"
if [ ! -f "$MAIN/scripts/run.sh" ] || [ ! -f "$HERE/branch.bundle" ]; then
    echo "Run this from the ThermoScope checkout root (local/p05-verify/branch.bundle must exist)."
    exit 2
fi
EXPECTED="$(tr -d ' \n' < "$HERE/expected-sha.txt")"
rm -f "$REPORT"
(umask 077; : > "$RAW")
finish() { # redact configured secrets into report.txt and remove the raw log, whatever happened
    [ -f "$RAW" ] || return 0
    local py="$DEST/.venv/bin/python"
    [ -x "$py" ] || py="$(ls "$MAIN"/local/toolchains/python/cpython-*/bin/python3 2>/dev/null | head -1)"
    "$py" - "$MAIN/.env" "$RAW" "$REPORT" <<'PY'
import re, sys
env, raw, out = sys.argv[1:]
text = open(raw, errors="replace").read()
secrets = []
try:
    for line in open(env):
        key, _, value = line.strip().partition("=")
        value = value.split(" #")[0].strip().strip("\"'")
        if key.endswith(("KEY", "PASSWORD", "TOKEN")) and len(value) >= 4:
            secrets.append(value)
        if key == "DATABASE_URL":
            m = re.search(r"://[^:/@]+:([^@]+)@", value)
            if m and len(m.group(1)) >= 4:
                secrets.append(m.group(1))
except FileNotFoundError:
    pass
for value in sorted(secrets, key=len, reverse=True):
    text = text.replace(value, "[redacted]")
text = re.sub(r"(postgres(?:ql)?[^\s:]*://[^:\s/@]+:)[^@\s]+@", r"\1[redacted]@", text)
open(out, "w").write(text)
print("Report written to local/p05-verify/report.txt; redacted", len(secrets), "configured value(s).")
PY
    rm -f "$RAW"
}
trap finish EXIT
trap 'exit 130' INT TERM
log() { printf '%s\n' "$*" | tee -a "$RAW"; }
short() { case "$1" in "$HOME"*) printf '~%s' "${1#"$HOME"}" ;; *) printf '%s' "$1" ;; esac; }
# macOS strips DYLD_* variables when a protected program (bash, env) starts, so the fallback is
# passed as TS_OMP_FALLBACK and exported by the shell that directly starts uv and Python.
with_fallback() {
    TS_OMP_FALLBACK="$1" bash scripts/run.sh bash -c \
        'export DYLD_FALLBACK_LIBRARY_PATH="$TS_OMP_FALLBACK:/usr/local/lib:/usr/lib"; exec "$@"' \
        with-fallback "${@:2}"
}
run() { # run <label> <command...>: output to the report, PASS/FAIL line
    local label="$1"; shift
    log ""; log "== $label"
    local started=$SECONDS
    ( "$@" ) >> "$RAW" 2>&1
    local code=$?
    log "-- $label: $([ $code -eq 0 ] && echo PASS || echo "FAIL (exit $code)") in $((SECONDS - started)) s"
    return $code
}

log "ThermoScope macOS verification  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "macOS $(sw_vers -productVersion 2>/dev/null) $(uname -m); expected branch tip $EXPECTED"

rm -rf "$DEST"
run "isolated clone" bash -c '
    git clone --quiet --no-hardlinks "$0" "$1" &&
    git -C "$1" fetch --quiet "$2" "refs/heads/*:refs/remotes/bundle/*" &&
    git -C "$1" checkout --quiet --detach "$3" &&
    test "$(git -C "$1" rev-parse HEAD)" = "$3" && git -C "$1" log --oneline -1' \
    "$MAIN" "$DEST" "$HERE/branch.bundle" "$EXPECTED" || { log "Cannot continue."; exit 1; }

# Reuse the pinned toolchains and download caches of the main checkout (read-mostly).
mkdir -p "$DEST/local"
ln -s "$MAIN/local/toolchains" "$DEST/local/toolchains"
ln -s "$MAIN/local/cache" "$DEST/local/cache"
if grep -q '^DATABASE_URL=' "$MAIN/.env" 2>/dev/null; then
    (umask 077; grep '^DATABASE_URL=' "$MAIN/.env" > "$DEST/.env")
    log "DATABASE_URL copied into the clone's .env (value not shown)."
else
    log "No DATABASE_URL in .env: database tests will be skipped."
fi
cd "$DEST" || exit 1

run "make install" make install
run "make install-ml" make install-ml

log ""; log "== XGBoost / OpenMP facts"
LIB="$(ls "$DEST"/.venv/lib/python3.*/site-packages/xgboost/lib/libxgboost.dylib 2>/dev/null | head -1)"
log "libxgboost.dylib found: $([ -n "$LIB" ] && echo yes || echo no)"
if [ -n "$LIB" ]; then
    otool -L "$LIB" 2>&1 | sed 's/^/  /' | tee -a "$RAW" >/dev/null
    otool -l "$LIB" 2>&1 | grep -A2 LC_RPATH | grep ' path ' | sed 's/^/  rpath:/' >> "$RAW"
fi
for candidate in /opt/homebrew/opt/libomp/lib/libomp.dylib /usr/local/opt/libomp/lib/libomp.dylib \
    "$HOME/.homebrew/opt/libomp/lib/libomp.dylib" "$HOME/homebrew/opt/libomp/lib/libomp.dylib"; do
    log "  $([ -f "$candidate" ] && echo present || echo absent): $(short "$candidate")"
done
BREW="$(command -v brew || true)"
[ -z "$BREW" ] && [ -x "$HOME/.homebrew/bin/brew" ] && BREW="$HOME/.homebrew/bin/brew"
if [ -n "$BREW" ]; then
    log "  brew: $(short "$BREW"); libomp: $("$BREW" list --versions libomp 2>/dev/null || echo 'not installed')"
else
    log "  brew: not found on PATH or in ~/.homebrew"
fi
SKOMP="$(ls "$DEST"/.venv/lib/python3.*/site-packages/sklearn/.dylibs/libomp.dylib 2>/dev/null | head -1)"
log "  scikit-learn bundled libomp: $([ -n "$SKOMP" ] && echo present || echo absent)"

PROBE='import sys, numpy as np
order = sys.argv[1]
if order == "sklearn-first":
    import sklearn.linear_model  # noqa: F401  (ml.py imports scikit-learn too)
import xgboost
X = np.random.default_rng(0).normal(size=(200, 4)); y = (X[:, 0] > 0).astype(int)
model = xgboost.XGBClassifier(n_estimators=10, max_depth=2, n_jobs=1).fit(X, y)
print("xgboost", xgboost.__version__, "fit ok, train accuracy", round((model.predict(X) == y).mean(), 3))'
XGB_OK=no
for order in xgboost-alone sklearn-first; do
    if run "xgboost probe ($order, project settings only)" bash scripts/run.sh uv run --frozen python -c "$PROBE" "$order"; then
        XGB_OK=yes
    fi
done
FALLBACK=""
if [ "$XGB_OK" = no ]; then
    for dir in "${BREW%/bin/brew}/opt/libomp/lib" "$(dirname "$SKOMP" 2>/dev/null)"; do
        [ -n "$dir" ] && [ -f "$dir/libomp.dylib" ] || continue
        if run "xgboost probe with OpenMP from $(short "$dir")" \
            with_fallback "$dir" uv run --frozen python -c "$PROBE" xgboost-alone; then
            FALLBACK="$dir"; break
        fi
    done
fi

run "make check" make check
if [ -f .env ]; then
    run "make integration (disposable databases)" make integration
    if [ "$XGB_OK" = no ] && [ -n "$FALLBACK" ]; then
        model_tests() {
            export THERMOSCOPE_RUN_DB_TESTS=1
            with_fallback "$FALLBACK" uv run --frozen pytest -q backend/tests/test_ml.py \
                backend/tests/test_p05_db.py
        }
        run "model tests with OpenMP from $(short "$FALLBACK")" model_tests
    fi
fi

log ""; log "== Summary"
grep -E '^-- ' "$RAW" > "$RAW.summary"
tee -a "$RAW" < "$RAW.summary"; rm -f "$RAW.summary"
log "xgboost loads with the project's settings: $XGB_OK${FALLBACK:+; loads with OpenMP from $(short "$FALLBACK")}"

finish
trap - EXIT
echo "Done. The report is ready; the clone in local/p05-verify/clone can be deleted later."
