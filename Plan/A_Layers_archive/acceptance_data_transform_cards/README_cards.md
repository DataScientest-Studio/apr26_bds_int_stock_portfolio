> **ARCHIVED — historical snapshot. Do not run.** These cards and the build/PDF/marker instructions below describe the former in-`A_Layers` layout and are no longer active. The live, self-contained SOT is [`../../A_Layers/ENG/Layers_Short_SOT/`](../../A_Layers/ENG/Layers_Short_SOT/); see [`../README.md`](../README.md).

# acceptance_data_transform_cards — Master Layer Cards (Printable Approval Forms)

This folder holds the **Master Layer Cards** — one self-contained, printable card per layer L1–L10 (plus cross-cutting overview). Each card is a fact-only summary derived strictly from the SOT in `../ENG/Layers_Short_SOT/`. 

Cards are designed to be:
- Printed individually (A5 landscape / 148×210 mm recommended, high-contrast dark/light themes supported via print CSS).
- Physically pinned or attached to the corresponding layer in the 3D pipeline model.
- Used as official approval / sign-off artifacts (checkboxes for QC/DoD items, signature block).
- A single source of consistent documentation that improves traceability in `../viz/main_data_flow.html` and aligns with `../../B_Features/ENG/Stages_Short_SOT/` (F-stages inline matching L facts).

## Governance
- Every fact on a card comes from exactly one SOT file (the layer file or a `00_*_eng.md`).
- On divergence, the SOT wins — update the card to match the SOT.
- Cards are subordinate to the SOT; they restate no new facts.
- Style: dense bullets/tables, one fact per line, no prose rationale.
- **Frozen data-state numbers** (tickers, zip count, row count, store sizes, candles/day, price scale)
  originally came from [`../config/numerical-amounts.json`](../../A_Layers/config/numerical-amounts.json).
  This archive is a static snapshot; live generation now happens only in `../A_Layers/`.

## Contents
- `card_template.md` — the reusable form template with sections and print-ready layout.
- `L01_Source_Alpaca_Card.md` … `L10_OOS_Test_Card.md` — one card per layer, populated from the corresponding SOT.
- `00_Crosscutting_Overview_Card.md` — master card covering 00_ files (conventions, parameters, input contract, DoD).
- This `README_cards.md`.

## How to Use / Print
1. Open a card `.md` in a Markdown viewer or convert to PDF/HTML (e.g. via pandoc, VSCode print, or browser with print CSS).
2. Use the template for any future layers or updates.
3. Check the QC/DoD checkboxes during self-review.
4. Pin the printed card to the physical 3D layer node.
5. Reference cards from `../viz/main_data_flow.html` tooltips or legend (future enhancement).

## Relation to Visualization & B_Features
The cards complement `../viz/main_data_flow.html` (the rotatable 3D canvas of L1–L10 flow) by providing the detailed, approvable layer contracts next to each visual node. They also ensure consistency with `../../B_Features/ENG/Stages_Short_SOT/` where F-stages (F1/F7/F8/F11) directly inline the L5/L7/L8/L10 facts.

See parent [`../README_A_Layer.md`](../../A_Layers/README_A_Layer.md) and SOT [`../ENG/Layers_Short_SOT/README.md`](../../A_Layers/ENG/Layers_Short_SOT/README.md).

---

**Project**: liora-project-ml-engineering / Pipeline A (L1–L10)  
**Print tip**: `@media print { ... }` keeps sections bordered, checkboxes visible, footer with "Pin to 3D L#" and link to viz.
