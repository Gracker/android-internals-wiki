#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLIC_REPOSITORY="${AIW_PACK_PUBLIC_REPOSITORY:-}"
KEYS_DIR="${AIW_TUF_KEYS_DIR:-}"
MODE="dry-run"
VERSION=""
VERSION_DATE="${AIW_PACK_VERSION_DATE:-}"
REVOKE_VERSION=""
MINIMUM_SAFE_VERSION=""
REASON_CODE=""
ALLOW_DIRTY="false"
OUTPUT_DIR="${AIW_PACK_OUTPUT_DIR:-$REPO_ROOT/dist/knowledge-pack-release}"

usage() {
  cat <<'EOF'
Usage: scripts/update_knowledge_pack.sh [options]

  --dry-run                       Build and verify without publishing (default)
  --publish                       Publish to the checked-out public repository
  --public-repo PATH              Public TUF repository checkout
  --keys-dir PATH                 Directory containing online TUF role keys
  --version YYYY.MM.DD.N          Override the automatically calculated CalVer
  --version-date YYYY.MM.DD       Test/operate the automatic CalVer date
  --revoke VERSION                Publish an emergency revocation
  --minimum-safe-version VERSION  Signed minimum safe version for revocation
  --reason-code CODE              Public machine-readable revocation reason
  --allow-dirty                   Allow local source changes for dry-run only
  --output PATH                   Verified release output directory
EOF
}

record_output() {
  local name="$1"
  local value="$2"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf '%s=%s\n' "$name" "$value" >> "$GITHUB_OUTPUT"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --publish)
      MODE="publish"
      shift
      ;;
    --public-repo)
      PUBLIC_REPOSITORY="$2"
      shift 2
      ;;
    --keys-dir)
      KEYS_DIR="$2"
      shift 2
      ;;
    --version)
      VERSION="$2"
      shift 2
      ;;
    --version-date)
      VERSION_DATE="$2"
      shift 2
      ;;
    --revoke)
      REVOKE_VERSION="$2"
      shift 2
      ;;
    --minimum-safe-version)
      MINIMUM_SAFE_VERSION="$2"
      shift 2
      ;;
    --reason-code)
      REASON_CODE="$2"
      shift 2
      ;;
    --allow-dirty)
      ALLOW_DIRTY="true"
      shift
      ;;
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$PUBLIC_REPOSITORY" ]]; then
  printf '%s\n' "--public-repo or AIW_PACK_PUBLIC_REPOSITORY is required" >&2
  exit 2
fi
if [[ ! -f "$PUBLIC_REPOSITORY/metadata/1.root.json" ]]; then
  printf 'TUF repository is not bootstrapped: %s\n' "$PUBLIC_REPOSITORY" >&2
  exit 2
fi
if [[ "$MODE" == "publish" && -z "$KEYS_DIR" ]]; then
  printf '%s\n' "--keys-dir or AIW_TUF_KEYS_DIR is required for publish" >&2
  exit 2
fi
if [[ "$MODE" == "publish" && "$ALLOW_DIRTY" == "true" ]]; then
  printf '%s\n' "--allow-dirty cannot be used with --publish" >&2
  exit 2
fi

PYTHON="${AIW_PACK_PYTHON:-python3}"

if [[ -n "$REVOKE_VERSION" ]]; then
  if [[ "$MODE" == "dry-run" ]]; then
    args=(
      "$PYTHON" "$REPO_ROOT/scripts/publish_knowledge_pack.py"
      validate-revocation
      --repository "$PUBLIC_REPOSITORY"
      --revoke-version "$REVOKE_VERSION"
    )
    if [[ -n "$MINIMUM_SAFE_VERSION" ]]; then
      args+=(--minimum-safe-version "$MINIMUM_SAFE_VERSION")
    fi
    if [[ -n "$REASON_CODE" ]]; then args+=(--reason-code "$REASON_CODE"); fi
    "${args[@]}"
    printf 'DRY RUN: revocation is valid and no repository files were changed\n'
    record_output "published" "false"
    record_output "revocation_dry_run" "true"
    exit 0
  fi
  args=(
    "$PYTHON" "$REPO_ROOT/scripts/publish_knowledge_pack.py"
    publish
    --repository "$PUBLIC_REPOSITORY"
    --keys-dir "$KEYS_DIR"
    --revoke-version "$REVOKE_VERSION"
  )
  if [[ -n "$MINIMUM_SAFE_VERSION" ]]; then
    args+=(--minimum-safe-version "$MINIMUM_SAFE_VERSION")
  fi
  if [[ -n "$REASON_CODE" ]]; then
    args+=(--reason-code "$REASON_CODE")
  fi
  "${args[@]}"
  record_output "published" "true"
  record_output "revoked_version" "$REVOKE_VERSION"
  exit 0
fi

temporary_dir="$(mktemp -d "${TMPDIR:-/tmp}/aiw-pack-update.XXXXXX")"
trap 'rm -rf "$temporary_dir"' EXIT
development_dir="$temporary_dir/development"
build_args=(
  "$PYTHON" "$REPO_ROOT/scripts/build_knowledge_pack.py"
  --repo "$REPO_ROOT"
  --output "$development_dir"
  --version "0.0.0-dev"
)
if [[ "$ALLOW_DIRTY" == "true" ]]; then
  build_args+=(--allow-dirty)
fi
"${build_args[@]}"
"$PYTHON" "$REPO_ROOT/scripts/verify_knowledge_pack.py" \
  --pack-dir "$development_dir" \
  --golden-queries "$REPO_ROOT/knowledge-pack/golden-queries.yaml"

fingerprint="$("$PYTHON" -c \
  'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["contentFingerprint"])' \
  "$development_dir/manifest.json")"
current_state="$("$PYTHON" "$REPO_ROOT/scripts/publish_knowledge_pack.py" \
  inspect --repository "$PUBLIC_REPOSITORY")"
current_fingerprint="$(printf '%s' "$current_state" | "$PYTHON" -c \
  'import json,sys; value=json.load(sys.stdin).get("channel") or {}; print(value.get("contentFingerprint", ""))')"
if [[ "$fingerprint" == "$current_fingerprint" ]]; then
  current_version="$(printf '%s' "$current_state" | "$PYTHON" -c \
    'import json,sys; print(json.load(sys.stdin)["channel"]["contentVersion"])')"
  printf 'Knowledge Pack is unchanged; stable remains %s\n' "$current_version"
  record_output "published" "false"
  record_output "content_version" "$current_version"
  record_output "reason" "content_fingerprint_unchanged"
  exit 0
fi

if [[ -z "$VERSION" ]]; then
  version_args=(
    "$PYTHON" "$REPO_ROOT/scripts/publish_knowledge_pack.py"
    next-version
    --repository "$PUBLIC_REPOSITORY"
  )
  if [[ -n "$VERSION_DATE" ]]; then
    version_args+=(--date "$VERSION_DATE")
  fi
  VERSION="$("${version_args[@]}" | "$PYTHON" -c \
    'import json,sys; print(json.load(sys.stdin)["nextVersion"])')"
fi

resolved_output="$("$PYTHON" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$OUTPUT_DIR")"
resolved_dist="$("$PYTHON" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$REPO_ROOT/dist")"
case "$resolved_output" in
  "$resolved_dist"/*) ;;
  *)
    printf 'Refusing to clean output outside %s: %s\n' "$resolved_dist" "$resolved_output" >&2
    exit 2
    ;;
esac
rm -rf "$resolved_output"
OUTPUT_DIR="$resolved_output"
mkdir -p "$OUTPUT_DIR"
final_build_args=(
  "$PYTHON" "$REPO_ROOT/scripts/build_knowledge_pack.py"
  --repo "$REPO_ROOT"
  --output "$OUTPUT_DIR"
  --version "$VERSION"
)
if [[ "$ALLOW_DIRTY" == "true" ]]; then
  final_build_args+=(--allow-dirty)
fi
"${final_build_args[@]}"
"$PYTHON" "$REPO_ROOT/scripts/verify_knowledge_pack.py" \
  --pack-dir "$OUTPUT_DIR" \
  --golden-queries "$REPO_ROOT/knowledge-pack/golden-queries.yaml"

if [[ "$MODE" == "dry-run" ]]; then
  printf 'DRY RUN: verified Knowledge Pack %s at %s\n' "$VERSION" "$OUTPUT_DIR"
  record_output "published" "false"
  record_output "content_version" "$VERSION"
  record_output "pack_dir" "$OUTPUT_DIR"
  record_output "reason" "dry_run"
  exit 0
fi

"$PYTHON" "$REPO_ROOT/scripts/publish_knowledge_pack.py" \
  publish \
  --repository "$PUBLIC_REPOSITORY" \
  --pack-dir "$OUTPUT_DIR" \
  --keys-dir "$KEYS_DIR"
record_output "published" "true"
record_output "content_version" "$VERSION"
record_output "pack_dir" "$OUTPUT_DIR"
