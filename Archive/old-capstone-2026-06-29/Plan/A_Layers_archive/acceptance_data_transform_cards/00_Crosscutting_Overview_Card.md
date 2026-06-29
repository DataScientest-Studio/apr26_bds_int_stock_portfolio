# 00 · Cross-Cutting Facts Overview — Master Layer Card (Acceptance Form)

## Layer Name
00 · Cross-Cutting (Conventions · Parameters · Input Contract · DoD)

## Purpose (Cel)
List all facts that span L1–L10:
- Notation (notation, naming conventions, global numbers 503/510/8 841 820),
- Global numbers in this project (503 tickers/510 zip files/8 841 820 timestamped rows),
- 17 params, input schema, acceptance checklist; single home for each fact.

## Input / Output
**In**: N/A (foundational).
**Out**: `00_conventions_eng.md`, `00_parameters_eng.md`, `00_input_contract_eng.md`, `00_definition_of_done_eng.md`; referenced by every layer card.

See: [`00_conventions_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_conventions_eng.md) · [`00_parameters_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_parameters_eng.md) · [`00_input_contract_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_input_contract_eng.md) · [`00_definition_of_done_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_definition_of_done_eng.md)

## Notebook / Artifact
- Canonical params file: `config/params.json` (exactly 17 keys + EPS + detector constants + L8 thresholds)
- Input contract: OHLCV table schema + `price_view` + naive-ET→UTC conversion rule (owned in 00_input_contract)
- Definition of Done: 20+ checklist items with layer ownership (owned in 00_definition_of_done)

## Tasks / Steps
1. Define notation & naming (00_conventions).
2. Register all 17+ parameters once (00_parameters).
3. Specify table schema + invariants (00_input_contract).
4. Maintain DoD checklist (00_definition_of_done).
5. Every layer references its owning 00_ file; never duplicates facts.

## QC Gates / DoD Items
- [ ] Every fact has exactly one home in a 00_ file.
- [ ] On divergence SOT wins.
- [ ] 503 tickers, 8 841 820 rows, 510 ZIPs referenced consistently.
- [ ] Causality / determinism / one-shot / gate rules defined once.
- [ ] All layer cards link back to correct 00_ owners.

## Dependencies
- Previous: none
- Next: all L1–L10 (reference these)
- Cross-cutting: all 00_* files

## 3D Visualisation
- Central hub cube or sphere linking all L1–L10 nodes.
- Four walls: conventions, parameters (17 keys), input contract schema, DoD checklist.
- Attached: global numbers panel (503/510/8 841 820) floating above.
- Arrows to each layer node labeled with owning facts.

---

**Footer**: Pin this card to 3D model overview node | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/00_*_eng.md` | Facts only from SOT.
