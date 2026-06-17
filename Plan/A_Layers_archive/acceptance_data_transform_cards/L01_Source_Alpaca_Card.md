# L1 · Source: Alpaca — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L1 · Source: Alpaca

## Purpose (Cel)
Download raw 1h OHLCV for 503 S&P 500 tickers from Alpaca (sip feed) via LEAN CLI; incremental hourly top-ups; store as LEAN ZIPs. Source of truth for all downstream layers.

## Input / Output
**In**: Alpaca Market Data API (REST, sip consolidated tape), `config/universe.txt` (503 tickers), cron schedule.  
**Out**: 510 ZIP files (`<ticker>.zip`), one per ticker, CSV rows `YYYYMMDD HH:MM,open×10000,high×10000,low×10000,close×10000,volume` (naive ET).

See: [`00_input_contract_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_input_contract_eng.md) · [L1_source_alpaca_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L1_source_alpaca_eng.md)

## Notebook / Artifact
- Tool: QuantConnect LEAN downloader CLI (headless REST client)
- Config files: `config/universe.txt` + `config/params.json` (no hardcoded thresholds anywhere)
- Related schedule: hourly cron at `:05` ET (session guard: no-op outside RTH)

## Tasks / Steps
1. Authorize with Alpaca API key (headless).
2. Download full history for 503 tickers (RTH 09:00–16:00 ET only, ~7 candles/day).
3. Incremental upsert every hour (lookback ~5 days).
4. Guard: outside ET market hours → no-op.
5. Verify `volume` column present (hard fail QC if absent).

## QC Gates / DoD Items
- [ ] 503 tickers downloaded, 510 ZIPs created.
- [ ] All CSVs have required columns and ×10000 integer prices.
- [ ] Timestamps naive ET, no TZ.
- [ ] Idempotent re-runs produce identical state.
- [ ] Session guard active (Mon–Fri RTH only).

## Dependencies
- Previous: none (L0 = external API, data origin)
- Next: L2 (LEAN ZIP store, first durable archive)
- Cross-cutting owners: `00_conventions_eng.md`, `00_parameters_eng.md` (global rules and numbers)

## 3D Visualisation
- Cube node: front wall = Alpaca cloud icon + "L1 Source".
- Left wall: REST API arrow graphic.
- Right wall: 510 ZIP folder icons (one per ticker).
- Back wall: "503 tickers · hourly cron" text panel.
- Attached: incoming data flow lines from external API sphere.

---

**Footer**: Pin this card to 3D model layer L1 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L1_source_alpaca_eng.md` | Facts only from SOT.