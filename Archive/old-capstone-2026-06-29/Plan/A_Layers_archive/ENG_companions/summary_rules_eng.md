# SOT writing rules

Goal: each SOT file in [`Layers_Short_SOT/`](../../A_Layers/ENG/Layers_Short_SOT/) reads like an account of what
**physically** happens to files, folders and data — no theory, no guesswork. Short, fact-only files that
*own* the canonical facts.

**Division of roles (the inversion).** The **canonical, authoritative source** is now the short
`Layers_Short_SOT/` files — they own every parameter, formula, schema and contract. The verbose companion
docs (`build_contract_eng.md`, `detector_algorithm_eng.md`, `quality_gate_spec_eng.md`, `glossary_eng.md`)
are **subordinate**: narrative, rationale, worked examples and definitions. Their verbose form is also an
example of "how not to" write the SOT: many facts per line, abstractions next to concretes — cognitive
overload. The SOT files are the "how to": **best practice without cognitive overload** — only actions and
physical objects.

## Rules

1. **Write the consecutive actions that happen** — chronologically, as bullets (`-`); details of a given
   action = sub-bullets (indented `-`). Build-critical contracts (schemas, formula tables, parameter tables)
   may be tables — still fact-only.
2. **One sentence = one fact.** Do not glue two facts together with conjunctions ("and", "as well as", "at
   the same time").
3. **Simple sentences, one per line.** Each line carries its information on its own, with no guesswork.
4. **The essence = the object perspective: files, folders, data.** The subject is a file / folder / table /
   column / row — not "the system", "the process", "the logic layer".
5. **Write from a physical-seeing perspective.** Describe what can be seen on disk or in the database: file
   name, path, format, count, naming convention. Zero abstraction without a physical carrier.
6. **Concrete details whenever they exist:** paths (`parquet/<TICKER>/ohlcv.parquet`), naming conventions
   (`<ticker>.zip`, `strategy_<TICKER>.py`), numbers (503, ×10000), formats (CSV without header, BIGINT, zstd).
7. **Each fact has exactly one home (DRY).** A fact is defined in its owner file (the fact-ownership map in
   [`Layers_Short_SOT/README.md`](../../A_Layers/ENG/Layers_Short_SOT/README.md)) and **referenced** everywhere else — even
   within the SOT (e.g. a layer file points to `00_parameters_eng.md` for parameter values rather than
   restating them).
8. **The companions follow the SOT (1:1 direction).** The companion docs must state the same facts as the
   SOT, never different ones; they reference, they do not redefine. **On any divergence, the SOT wins** — fix
   the companion (or the viz) to match the SOT, never the reverse.

## Pattern

```text
- download Alpaca data with the QuantConnect LEAN tool; result = `<ticker>.zip` files
  - one zip = one ticker; inside, one CSV without a header
  - CSV row: `YYYYMMDD HH:MM,open,high,low,close,volume`
- from the zips we load a DuckDB database: table `raw_ohlcv_1h`
  - prices in the table = int ×10000; USD is only visible in the `ohlcv_1h` view
```

## Anti-pattern

"How not to" is shown by the verbose companion docs: sections, tables, roles and invariants are correct as
narrative, but as the SOT they cause cognitive overload — compound sentences, many facts per line,
abstractions next to concretes. The SOT is exclusively an extract of actions and physical objects. Example
sentences we do not write in the SOT:

- "The ingest layer is responsible for the acquisition of market data" — no file, folder or data is visible.
- "The data is processed, validated and stored" — three facts in one sentence and none of them is concrete.
