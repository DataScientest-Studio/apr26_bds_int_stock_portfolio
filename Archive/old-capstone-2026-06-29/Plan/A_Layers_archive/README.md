# A_Layers_archive

Material removed from `Plan/A_Layers/` during the **minimalism cleanup** (2026-06-17) so that `A_Layers/`
is a lean, self-contained SOT. Kept here, outside the live project, for reference. Nothing here is part of
the build; the live SOT is [`../A_Layers/ENG/Layers_Short_SOT/`](../A_Layers/ENG/Layers_Short_SOT/).

## Contents
- `acceptance_data_transform_cards/` — the 11 printable Master Layer Cards + `card_template.md` + `README_cards.md`
  + the PDF (`Master_Layer_Cards_Print_A4.pdf`) + its `fpdf`-based generator. Duplicated the SOT.
- `ENG_companions/` — the 6 ENG narrative companions (`build_contract`, `detector_algorithm`, `glossary`,
  `quality_gate_spec`, `readme`, `summary_rules`). Narrative / worked examples only; the SOT owns every fact.
- `RAPORT_SPOJNOSCI.md` — a one-off consistency-audit report.

These files are **frozen snapshots**: the `<!--na:…-->` data-state markers were stripped back to plain literal
values, so they are static (the live `tools/numbers.py` no longer generates or checks them).

## Why minimal (the rules going forward, for `A_Layers/`)
- One home per fact: prose facts in `ENG/Layers_Short_SOT/`, data-state numbers in `config/numerical-amounts.json`,
  tunable knobs in `config/params.json`.
- No acceptance cards, audit reports, PDFs, caches, SOT duplicates, or unjustified folders in the live project.
- Tooling stays standard-library only (`tools/numbers.py`); `fpdf2` was the only added dependency and is gone.

## Restore an item
Move it back, e.g.: `git mv Plan/A_Layers_archive/ENG_companions/glossary_eng.md Plan/A_Layers/ENG/glossary_eng.md`,
then restore any links. (Stripped markers would need re-wrapping via `tools/numbers.py init` if you want them live again.)
