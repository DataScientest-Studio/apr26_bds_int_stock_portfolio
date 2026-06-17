<!-- Reference FORM only — NOT processed by any generator. {{LAYER_ID}}, {{LAYER_NAME}}, {{STATUS}} are
     placeholder fields a human fills when authoring a new card; they are not registry tokens. Real cards
     (L01..L10 + 00 overview) are archived .md files. Live frozen data-state numbers now live in
     ../A_Layers/config/numerical-amounts.json and are generated only in the live A_Layers tree.
     Do not put literal data-state numbers in this template. -->

# {{LAYER_ID}} · {{LAYER_NAME}} — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: {{STATUS}}

---

## Layer Name
{{LAYER_ID}} · {{LAYER_NAME}}

## Purpose (Cel)
{{PURPOSE}}

## Input / Output
**In**: {{INPUT}}  
**Out**: {{OUTPUT}}

See: [`00_input_contract_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_input_contract_eng.md) · [{{LAYER_SOT_FILE}}](../../A_Layers/ENG/Layers_Short_SOT/{{LAYER_SOT_FILE}})

## Notebook / Artifact
- Notebook / script: {{NOTEBOOK_OR_SCRIPT}}
- Config / params: `config/params.json` ({{PARAM_KEYS}})
- Related: {{RELATED_ARTIFACTS}}

## Tasks / Steps
{{TASKS}}

## QC Gates / DoD Items
{{QC_DOD_CHECKBOXES}}

## Dependencies
- Previous layer: {{PREV_LAYER}} (what feeds data into this layer)
- Next layer: {{NEXT_LAYER}} (what consumes the output of this layer)
- Cross-cutting owners: `00_conventions_eng.md`, `00_parameters_eng.md`, `00_definition_of_done_eng.md` (facts defined once for all layers)

## 3D Visualisation
Suggestions for this layer node in `main_data_flow.html` (rotatable 3D canvas):
- Cube or vertical slab with 4 walls/faces as info panels.
- Front wall: layer name + icon (e.g. download cloud, zip, DB cylinder, parquet stack, split timeline, detector lines, X/Y table, gate shield, Optuna chart, OOS matrix).
- Left wall: incoming data graphic (REST arrow, ZIP folder, parquet files).
- Right wall: outgoing artifact (DB view, snapshot parquet, feature table X + label Y floating plane, strategy.py icon).
- Back/Top wall: key numbers or QC checkboxes (mini table or checkmarks).
- Attached: floating X/Y table mesh or `<universe_size>`×metrics matrix near the node; arrows labeled with row counts or "`<lean_zip_count>` ZIPs".

---

**Footer**: Pin this card to 3D model layer {{LAYER_ID}} | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/{{LAYER_SOT_FILE}}` | Generated from template — facts only from SOT.
