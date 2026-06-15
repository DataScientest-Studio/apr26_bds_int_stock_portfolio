# Plan — S&P 500 ML pipeline snapshot (English)

Minimal, self-contained snapshot of the sister project's pipeline documentation and its
interactive visualization. Both parts open standalone — no build step, no dependencies.

## Provenance

- Source project: `/opt/to_liora_school/liora-project-ml-pipeline-and-visualisation-sp500`
- Source branch / commit: `viz/redesign-self-explaining` @ `25f06a1`
- Snapshot taken: 2026-06-15
- This is a copy; the source project remains the single source of truth.

## Contents

- [`ENG/`](ENG/) — English 1:1 summaries of the 10-layer pipeline (L1–L10) plus the
  writing standard. Start at [`ENG/readme_eng.md`](ENG/readme_eng.md).
- [`viz/index.html`](viz/index.html) — the interactive 3D pipeline visualization
  (single self-contained HTML, ~147 KB; all 10 layers and views embedded).

## Open the visualization

- Double-click [`viz/index.html`](viz/index.html), or open it in any modern browser.
- For full interaction, serve over HTTP from this folder, e.g. `python3 -m http.server`
  then open `viz/index.html`.
- Deep-links: `viz/index.html#1` … `#9` (views), `#setup` (L6), `#dq` (L8), `#L6` (layer contract).
- Controls: drag = rotate · scroll = zoom · click element = details · keys `1–9` = views.

## Notes

- The full Polish reference docs (`FLOW/L*.md`) and the live pipeline code stay in the
  source project — they are intentionally not part of this minimal snapshot.
- The visualization is frozen at the source commit above; refresh by re-copying
  `viz/index.html` from the source project.
