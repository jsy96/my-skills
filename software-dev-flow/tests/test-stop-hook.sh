#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$ROOT/assets/templates/.hooks/stop-devcheck.sh"

command -v bash >/dev/null 2>&1 || { echo "FAIL: bash is required" >&2; exit 1; }
[ -f "$HOOK" ] || { echo "FAIL: hook script not found: $HOOK" >&2; exit 1; }
chmod +x "$HOOK" 2>/dev/null || true

cd "$ROOT"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/software-dev-stop-hook-test.XXXXXX")"
fake_bin="$test_root/bin"
minimal_bin="$test_root/minimal-bin"
marker_root="/tmp/software-dev-stopcheck-${UID}"
markers=""
mkdir -p "$fake_bin" "$minimal_bin"

# fake codex reports a controllable version
cat > "$fake_bin/codex" <<'EOF'
#!/bin/sh
printf 'codex-cli %s\n' "${SOFTWARE_DEV_FLOW_FAKE_CODEX_VERSION:-0.145.0}"
EOF
chmod +x "$fake_bin/codex"

# minimal bin: a shebang-wrapped cat only (no jq) to exercise the safe-pass path.
# On MSYS/Git Bash a copied binary cannot load its DLLs without /usr/bin in PATH,
# so cat is a #!/bin/sh wrapper exec-ing the absolute real cat, and the hook is
# launched via "$BASH" (absolute path, DLLs found next to the real binary).
real_cat="$(command -v cat)"
{ printf '#!/bin/sh\nexec '; printf '%s' "$real_cat"; printf ' "$@"\n'; } > "$minimal_bin/cat"
chmod +x "$minimal_bin/cat"

marker_for() {
  local tool="$1"
  local session="$2"
  local scope="$3"
  printf '%s/%s-%s-%s-%s-%s' \
    "$marker_root" "$tool" "${#session}" "$session" "${#scope}" "$scope"
}

remember_marker() {
  local marker="$1"
  markers="${markers}
${marker}"
  rmdir "$marker" 2>/dev/null || true
}

cleanup() {
  printf '%s\n' "$markers" | while IFS= read -r marker; do
    [ -n "$marker" ] && rmdir "$marker" 2>/dev/null || true
  done
  rm -rf "$test_root"
}
trap cleanup EXIT

failures=0
pass_count=0

expect_continue() {
  local label="$1"
  local got="$2"
  case "$got" in
    *'"continue":true'*) pass_count=$((pass_count + 1)); printf 'ok   %s\n' "$label" ;;
    *) failures=$((failures + 1)); printf 'FAIL %s — got: %s\n' "$label" "$got" >&2 ;;
  esac
}

run_raw() {
  local tool="$1"
  local version="$2"
  local payload="$3"
  printf '%s' "$payload" |
    env PATH="$fake_bin:$PATH" SOFTWARE_DEV_FLOW_FAKE_CODEX_VERSION="$version" \
      bash "$HOOK" "$tool" 2>/dev/null || true
}

run_no_jq() {
  local tool="$1"
  local payload="$2"
  printf '%s' "$payload" |
    env PATH="$minimal_bin" \
      "$BASH" "$HOOK" "$tool" 2>/dev/null || true
}

# ---------- Safe-pass paths (always runnable, jq not required) ----------

got="$(printf '' | bash "$HOOK" claude 2>/dev/null || true)"
expect_continue "claude: empty stdin" "$got"

got="$(printf 'not-json' | bash "$HOOK" claude 2>/dev/null || true)"
expect_continue "claude: invalid json" "$got"

got="$(printf '{}' | bash "$HOOK" claude 2>/dev/null || true)"
expect_continue "claude: missing session/scope fields" "$got"

got="$(printf '%s' '{"session_id":"s-ok-1","prompt_id":"p-ok-1"}' | bash "$HOOK" unknown-tool 2>/dev/null || true)"
expect_continue "unknown tool: safe pass" "$got"

bad_id="$(printf '%s' '{"session_id":"bad;rm -rf","prompt_id":"p1"}' | bash "$HOOK" claude 2>/dev/null || true)"
expect_continue "claude: unsafe id characters rejected" "$bad_id"

got="$(run_no_jq claude '{"session_id":"s-nojq","prompt_id":"p-nojq"}')"
expect_continue "claude: missing jq → safe pass" "$got"

if ! command -v jq >/dev/null 2>&1; then
  echo ""
  echo "SKIP: jq not installed on this machine — only safe-pass paths verified."
  echo "      Install jq and re-run for full gate/marker assertions."
  if [ "$failures" -gt 0 ]; then exit 1; fi
  printf '\n%d passed, 0 failed (subset)\n' "$pass_count"
  exit 0
fi

# ---------- Full assertions (jq required) ----------

CLAUDE_PAYLOAD='{"session_id":"sess-100","prompt_id":"turn-100"}'
CODEX_PAYLOAD='{"session_id":"sess-200","turn_id":"turn-200"}'

# 1) claude first stop in a fresh scope → decision:block with self-check reason
m="$(marker_for claude sess-100 turn-100)"
got="$(run_raw claude 0.145.0 "$CLAUDE_PAYLOAD")"
case "$got" in
  *'"decision":"block"'*)
    case "$got" in
      *收工自检*门禁*flow/进展.md*)
        pass_count=$((pass_count + 1)); printf 'ok   claude: first stop blocks with reason\n' ;;
      *)
        failures=$((failures + 1)); printf 'FAIL claude first stop — reason missing expected content: %s\n' "$got" >&2 ;;
    esac
    ;;
  *) failures=$((failures + 1)); printf 'FAIL claude first stop — got: %s\n' "$got" >&2 ;;
esac
markers="${markers}
${m}"

# 2) same scope again → continue (single continuation per turn)
got="$(run_raw claude 0.145.0 "$CLAUDE_PAYLOAD")"
expect_continue "claude: repeat stop in same scope continues" "$got"

# 3) stop_hook_active=true → continue
got="$(printf '%s' '{"session_id":"sess-101","prompt_id":"turn-101","stop_hook_active":true}' |
  env PATH="$fake_bin:$PATH" bash "$HOOK" claude 2>/dev/null || true)"
expect_continue "claude: stop_hook_active continues" "$got"
rmdir "$(marker_for claude sess-101 turn-101)" 2>/dev/null || true

# 4) different session/scope is isolated → blocks again
m="$(marker_for claude sess-999 turn-999)"
got="$(run_raw claude 0.145.0 '{"session_id":"sess-999","prompt_id":"turn-999"}')"
case "$got" in
  *'"decision":"block"'*) pass_count=$((pass_count + 1)); printf 'ok   claude: different scope blocks\n' ;;
  *) failures=$((failures + 1)); printf 'FAIL claude different scope — got: %s\n' "$got" >&2 ;;
esac
markers="${markers}
${m}"

# 5) codex below 0.145.0 → safe pass (known-bad 0.144.1)
got="$(run_raw codex 0.144.1 "$CODEX_PAYLOAD")"
expect_continue "codex 0.144.1: safe pass" "$got"

# 6) codex unparseable version → safe pass
got="$(run_raw codex "unknown-version" "$CODEX_PAYLOAD")"
expect_continue "codex unparseable version: safe pass" "$got"

# 7) codex >= 0.145.0 first stop → block, then repeat continues
m="$(marker_for codex sess-200 turn-200)"
got="$(run_raw codex 0.145.0 "$CODEX_PAYLOAD")"
case "$got" in
  *'"decision":"block"'*) pass_count=$((pass_count + 1)); printf 'ok   codex 0.145.0: first stop blocks\n' ;;
  *) failures=$((failures + 1)); printf 'FAIL codex first stop — got: %s\n' "$got" >&2 ;;
esac
got="$(run_raw codex 0.145.0 "$CODEX_PAYLOAD")"
expect_continue "codex 0.145.0: repeat stop continues" "$got"
markers="${markers}
${m}"

# 8) codex 1.x (major > 0) also passes the version gate
m="$(marker_for codex sess-201 turn-201)"
got="$(run_raw codex 1.2.3 '{"session_id":"sess-201","turn_id":"turn-201"}')"
case "$got" in
  *'"decision":"block"'*) pass_count=$((pass_count + 1)); printf 'ok   codex 1.2.3: version gate passes\n' ;;
  *) failures=$((failures + 1)); printf 'FAIL codex 1.2.3 — got: %s\n' "$got" >&2 ;;
esac
markers="${markers}
${m}"

# 9) claude payload carrying turn_id instead of prompt_id → no fallback, safe pass
got="$(run_raw claude 0.145.0 '{"session_id":"sess-300","turn_id":"turn-300"}')"
expect_continue "claude: turn_id not accepted (no cross-tool fallback)" "$got"

echo ""
if [ "$failures" -gt 0 ]; then
  printf 'FAIL: %d assertion(s) failed\n' "$failures" >&2
  exit 1
fi
printf '%d passed, 0 failed\n' "$pass_count"
