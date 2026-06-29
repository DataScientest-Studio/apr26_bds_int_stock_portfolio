#!/usr/bin/env bash
# Build REPORT.pdf from REPORT.md using pandoc + eisvogel + xelatex.
#
# Usage:
#   ./build_pdf.sh                 # build REPORT.pdf in this folder
#   ./build_pdf.sh --watch         # rebuild on every save (needs fswatch)
#   ./build_pdf.sh --output X.pdf  # custom output path
#
# Dependencies (macOS):
#   brew install pandoc
#   brew install --cask mactex-no-gui     # gives xelatex (~1.5 GB; or use basictex)
#   # then install the eisvogel template (see install_eisvogel below)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configurable bits
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
# REPORT.md lives in Formalities/Rendering1 (reports/ holds only code).
RENDERING_DIR="$(cd -- "${SCRIPT_DIR}/../../../Formalities/Rendering1" &>/dev/null && pwd)"
INPUT="${RENDERING_DIR}/REPORT.md"
OUTPUT="${RENDERING_DIR}/report_v1_June_03_2026.pdf"
TEMPLATE_NAME="eisvogel"
# Eisvogel ships as a .latex file. Pandoc looks for it under
# ~/.pandoc/templates/eisvogel.latex (or ~/.local/share/pandoc/templates/...)
TEMPLATE_PATH="${HOME}/.pandoc/templates/eisvogel.latex"
PDF_ENGINE="xelatex"
# Syntax highlighting is handled by eisvogel via `listings: true` in REPORT.md YAML.

# Parse flags
WATCH=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --watch)  WATCH=1; shift ;;
    --output) OUTPUT="$2"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown flag: $1" >&2
      exit 2
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "❌  Missing dependency: $1" >&2
    echo "   $2" >&2
    exit 1
  }
}

require pandoc       "Install with: brew install pandoc"
require "$PDF_ENGINE" "Install xelatex with: brew install --cask mactex-no-gui (or 'basictex' for a smaller install)"

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  cat >&2 <<EOF
❌  Eisvogel template not found at: $TEMPLATE_PATH

Install Eisvogel v3.4.0 (current latest) with:

  mkdir -p ~/.pandoc/templates
  curl -L https://github.com/Wandmalfarbe/pandoc-latex-template/releases/download/v3.4.0/Eisvogel.tar.gz \\
    | tar -xz --strip-components=1 -C ~/.pandoc/templates Eisvogel-3.4.0/eisvogel.latex

Verify with:

  ls -la ~/.pandoc/templates/eisvogel.latex   # should be ~31 KB
EOF
  exit 1
fi

if [[ ! -f "$INPUT" ]]; then
  echo "❌  REPORT.md not found at: $INPUT" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
build_once() {
  local started
  started=$(date +%s)
  echo "🔧  Building $(basename "$OUTPUT") …"

  pandoc "$INPUT" \
    --from=markdown+yaml_metadata_block+tex_math_dollars+pipe_tables+grid_tables+raw_tex \
    --to=pdf \
    --pdf-engine="$PDF_ENGINE" \
    --template="$TEMPLATE_NAME" \
    --toc \
    --metadata=date:"$(date '+%Y-%m-%d')" \
    --output="$OUTPUT"

  local elapsed=$(( $(date +%s) - started ))
  echo "✅  Built $OUTPUT  (${elapsed}s)"
}

# ---------------------------------------------------------------------------
# Watch mode (optional)
# ---------------------------------------------------------------------------
if [[ "$WATCH" -eq 1 ]]; then
  require fswatch "Install with: brew install fswatch"
  echo "👀  Watching $(basename "$INPUT") — Ctrl-C to stop."
  build_once || true
  fswatch -o "$INPUT" | while read -r _; do
    echo ""
    build_once || echo "⚠️  Build failed, waiting for next save…"
  done
else
  build_once
fi
