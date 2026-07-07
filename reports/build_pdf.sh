#!/usr/bin/env bash
# Build report PDFs from Markdown using pandoc + eisvogel + xelatex.
#
# Usage:
#   ./build_pdf.sh                 # build all reports below (REPORT.md + MODELING_REPORT_010726.md)
#   ./build_pdf.sh --watch         # rebuild REPORT.md on every save (needs fswatch)
#   ./build_pdf.sh --input X.md --output X.pdf  # build a single custom report
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
# Reports built by default when no --input/--output is given (md:pdf pairs).
DEFAULT_REPORTS=(
  "REPORT.md:REPORT.pdf"
  "MODELING_REPORT_010726.md:MODELING_REPORT_010726.pdf"
)
INPUT=""
OUTPUT=""
TEMPLATE_NAME="eisvogel"
# Eisvogel ships as a .latex file. Pandoc looks for it under
# ~/.pandoc/templates/eisvogel.latex (or ~/.local/share/pandoc/templates/...)
TEMPLATE_PATH="${HOME}/.pandoc/templates/eisvogel.latex"
PDF_ENGINE="xelatex"
# Syntax highlighting is handled by eisvogel via `listings: true` in each report's YAML.

# Parse flags
WATCH=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --watch)  WATCH=1; shift ;;
    --input)  INPUT="$2"; shift 2 ;;
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

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
build_once() {
  local input="$1"
  local output="$2"
  local started
  started=$(date +%s)

  if [[ ! -f "$input" ]]; then
    echo "❌  Input not found at: $input" >&2
    exit 1
  fi

  echo "🔧  Building $(basename "$output") …"

  # Only the single growing report (REPORT.md) gets a build-time date — its
  # own YAML sets date: "\today", meaning "whenever this was last compiled".
  # Frozen milestone deliverables (e.g. MODELING_REPORT_010726.md) already
  # pin their own submission date in YAML and must not have it overwritten.
  local date_flag=""
  if [[ "$(basename "$input")" == "REPORT.md" ]]; then
    date_flag="date:$(date '+%Y-%m-%d')"
  fi

  # Shared layout defaults (pdf_style.yaml) keep config noise out of the human-readable
  # markdown; a report's own YAML block always takes precedence over these defaults.
  local style_flag=""
  if [[ -f "${SCRIPT_DIR}/pdf_style.yaml" ]]; then
    style_flag="${SCRIPT_DIR}/pdf_style.yaml"
  fi

  pandoc "$input" \
    --from=markdown+yaml_metadata_block+tex_math_dollars+pipe_tables+grid_tables+raw_tex \
    --to=pdf \
    --pdf-engine="$PDF_ENGINE" \
    --template="$TEMPLATE_NAME" \
    --toc \
    ${style_flag:+--metadata-file="$style_flag"} \
    ${date_flag:+--metadata="$date_flag"} \
    --output="$output"

  local elapsed=$(( $(date +%s) - started ))
  echo "✅  Built $output  (${elapsed}s)"
}

# ---------------------------------------------------------------------------
# Watch mode (optional) — always watches/builds a single report
# ---------------------------------------------------------------------------
if [[ "$WATCH" -eq 1 ]]; then
  WATCH_INPUT="${INPUT:-${SCRIPT_DIR}/REPORT.md}"
  WATCH_OUTPUT="${OUTPUT:-${SCRIPT_DIR}/REPORT.pdf}"
  require fswatch "Install with: brew install fswatch"
  echo "👀  Watching $(basename "$WATCH_INPUT") — Ctrl-C to stop."
  build_once "$WATCH_INPUT" "$WATCH_OUTPUT" || true
  fswatch -o "$WATCH_INPUT" | while read -r _; do
    echo ""
    build_once "$WATCH_INPUT" "$WATCH_OUTPUT" || echo "⚠️  Build failed, waiting for next save…"
  done
elif [[ -n "$INPUT" || -n "$OUTPUT" ]]; then
  # Single custom report requested via --input/--output.
  [[ -n "$INPUT" ]] || { echo "❌  --output given without --input" >&2; exit 2; }
  [[ -n "$OUTPUT" ]] || OUTPUT="${INPUT%.md}.pdf"
  build_once "$INPUT" "$OUTPUT"
else
  # Default: build every report in DEFAULT_REPORTS.
  for pair in "${DEFAULT_REPORTS[@]}"; do
    md="${pair%%:*}"
    pdf="${pair##*:}"
    build_once "${SCRIPT_DIR}/${md}" "${SCRIPT_DIR}/${pdf}"
  done
fi
