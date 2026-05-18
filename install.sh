#!/usr/bin/env bash
set -euo pipefail

# HARA skill installer.
# Installs one portable skill plus its knowledge base and deterministic tools.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
if [[ ! -d "$REPO_ROOT/skills" && -d "$(pwd)/skills" ]]; then
  REPO_ROOT="$(pwd)"
fi

TARGET_DIR="${HOME}/.claude"
DRY_RUN=false
UNINSTALL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT_DIR="${2:-}"
      if [[ -z "$PROJECT_DIR" ]]; then
        echo "[ERROR] --project requires a path" >&2
        exit 1
      fi
      TARGET_DIR="${PROJECT_DIR}/.claude"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --uninstall)
      UNINSTALL=true
      shift
      ;;
    -h|--help)
      cat <<HELP
Usage:
  ./install.sh [--dry-run]
  ./install.sh --uninstall
  ./install.sh --project /path/to/project

Installed paths under the target directory:
  Skills (multi-agent architecture):
  - skills/hara-orchestrator (main entry point)
  - skills/hara-stage0 / hara-stage0r
  - skills/hara-stage1 / hara-stage1r
  - skills/hara-stage2 / hara-stage2r
  - skills/hara-stage3a / hara-stage3ar / hara-stage3b / hara-stage3br
  - skills/hara-stage4 / hara-stage4r
  Knowledge base:
  - knowledge-base/automotive/hara
  Tools:
  - tools/hara

Note:
  - tools are installed as a sibling of skills, not inside the skill directory
  - Use tools/hara/check_stage_json.py under the target directory
  - The orchestrator (hara-orchestrator) is the main entry point
  - Individual stage skills can be called directly if needed
  - No agent and no CLAUDE.md are installed
HELP
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

MANIFEST_FILE="${TARGET_DIR}/.hara-skill-install-manifest"

log() { echo "[+] $*"; }
warn() { echo "[!] $*"; }

manifest_add() {
  local path="$1"
  if ! $DRY_RUN; then
    mkdir -p "$(dirname "$MANIFEST_FILE")"
    echo "$path" >> "$MANIFEST_FILE"
  fi
}

remove_path() {
  local path="$1"
  if $DRY_RUN; then
    echo "[DRY-RUN] rm -rf $path"
  else
    rm -rf "$path"
    log "Removed $path"
  fi
}

install_dir() {
  local src="$1"
  local dest="$2"
  if [[ ! -e "$src" ]]; then
    warn "Source not found, skip: $src"
    return
  fi
  if $DRY_RUN; then
    echo "[DRY-RUN] link dir $src -> $dest"
    return
  fi
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  ln -s "$src" "$dest"
  manifest_add "$dest"
  log "Installed $dest"
}

if $UNINSTALL; then
  if [[ -f "$MANIFEST_FILE" ]]; then
    while IFS= read -r path; do
      [[ -z "$path" ]] && continue
      remove_path "$path"
    done < "$MANIFEST_FILE"
    if ! $DRY_RUN; then rm -f "$MANIFEST_FILE"; fi
  else
    # Remove all HARA skills
    remove_path "${TARGET_DIR}/skills/hara-orchestrator"
    remove_path "${TARGET_DIR}/skills/hara-stage0"
    remove_path "${TARGET_DIR}/skills/hara-stage0r"
    remove_path "${TARGET_DIR}/skills/hara-stage1"
    remove_path "${TARGET_DIR}/skills/hara-stage1r"
    remove_path "${TARGET_DIR}/skills/hara-stage2"
    remove_path "${TARGET_DIR}/skills/hara-stage2r"
    remove_path "${TARGET_DIR}/skills/hara-stage3a"
    remove_path "${TARGET_DIR}/skills/hara-stage3ar"
    remove_path "${TARGET_DIR}/skills/hara-stage3b"
    remove_path "${TARGET_DIR}/skills/hara-stage3br"
    remove_path "${TARGET_DIR}/skills/hara-stage3r"  # legacy Stage3R flow
    remove_path "${TARGET_DIR}/skills/hara-stage4"
    remove_path "${TARGET_DIR}/skills/hara-stage4r"
    remove_path "${TARGET_DIR}/skills/hara-byd-analysis"  # legacy
    remove_path "${TARGET_DIR}/knowledge-base/automotive/hara"
    remove_path "${TARGET_DIR}/tools/hara"
  fi
  exit 0
fi

log "Repo root: $REPO_ROOT"
log "Target: $TARGET_DIR"
if $DRY_RUN; then warn "DRY RUN"; fi

if ! $DRY_RUN; then
  mkdir -p "$TARGET_DIR"
  : > "$MANIFEST_FILE"
fi

# Install multi-agent skills
install_dir "${REPO_ROOT}/skills/hara-orchestrator" "${TARGET_DIR}/skills/hara-orchestrator"
install_dir "${REPO_ROOT}/skills/hara-stage0" "${TARGET_DIR}/skills/hara-stage0"
install_dir "${REPO_ROOT}/skills/hara-stage0r" "${TARGET_DIR}/skills/hara-stage0r"
install_dir "${REPO_ROOT}/skills/hara-stage1" "${TARGET_DIR}/skills/hara-stage1"
install_dir "${REPO_ROOT}/skills/hara-stage1r" "${TARGET_DIR}/skills/hara-stage1r"
install_dir "${REPO_ROOT}/skills/hara-stage2" "${TARGET_DIR}/skills/hara-stage2"
install_dir "${REPO_ROOT}/skills/hara-stage2r" "${TARGET_DIR}/skills/hara-stage2r"
install_dir "${REPO_ROOT}/skills/hara-stage3a" "${TARGET_DIR}/skills/hara-stage3a"
install_dir "${REPO_ROOT}/skills/hara-stage3ar" "${TARGET_DIR}/skills/hara-stage3ar"
install_dir "${REPO_ROOT}/skills/hara-stage3b" "${TARGET_DIR}/skills/hara-stage3b"
install_dir "${REPO_ROOT}/skills/hara-stage3br" "${TARGET_DIR}/skills/hara-stage3br"
install_dir "${REPO_ROOT}/skills/hara-stage4" "${TARGET_DIR}/skills/hara-stage4"
install_dir "${REPO_ROOT}/skills/hara-stage4r" "${TARGET_DIR}/skills/hara-stage4r"

# Optional: keep legacy skill for backward compatibility
# install_dir "${REPO_ROOT}/skills/hara-byd-analysis" "${TARGET_DIR}/skills/hara-byd-analysis"

# Install shared resources
install_dir "${REPO_ROOT}/knowledge-base/automotive/hara" "${TARGET_DIR}/knowledge-base/automotive/hara"
install_dir "${REPO_ROOT}/tools/hara" "${TARGET_DIR}/tools/hara"

log "HARA multi-agent skills installed."
log "Main entry: /hara-orchestrator"
log "Try: 帮我对某个功能文档做 HARA 分析，并导出 Excel"
