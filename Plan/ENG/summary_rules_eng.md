# Summary writing rules (FLOW/streszczenie)

Goal: a summary reads like an account of what **physically** happens to files,
folders and data — no theory, no guesswork.

**Division of roles:** the full files `FLOW/L*.md` (Polish, in the source project) are the complete reference for a
layer (role, invariants, visualization, links) — and at the same time an example of "how
not to" write a summary: that form causes cognitive overload. `streszczenie/` is the "how
to": **best practice without cognitive overload** — only actions and physical objects.

## Rules

1. **Write the consecutive actions that happen** — chronologically, as bullets (`-`);
   details of a given action = sub-bullets (indented `-`).
2. **One sentence = one fact.** Do not glue two facts together with conjunctions
   ("and", "as well as", "at the same time").
3. **Simple sentences, one per line.** Each line carries its information on its own,
   with no guesswork — the reader does not have to infer anything from context.
4. **The essence of a summary = the object perspective: files, folders, data.**
   The subject of a sentence is a file / folder / table / column / row —
   not "the system", "the process", "the logic layer".
5. **Write from a physical-seeing perspective.** Describe what can be seen on disk
   or in the database: file name, path, format, count, naming convention.
   Zero abstraction without a physical carrier.
6. **Concrete details whenever they exist:** paths (`parquet/<TICKER>/ohlcv.parquet`),
   naming conventions (`<ticker>.zip`, `strategy_<TICKER>.py`), numbers (503, ×10000),
   formats (CSV without header, BIGINT, zstd).
7. **Parameters and decisions by reference only** (spec §7, register C-xx) —
   the summary points to the source, it does not redefine it.
8. **The summary is 1:1 with the full FLOW file:** the same facts, shorter form;
   on any divergence we fix both files in the same commit.

## Pattern

```text
- download Alpaca data with the QuantConnect LEAN tool; result = `<ticker>.zip` files
  - one zip = one ticker; inside, one CSV without a header
  - CSV row: `YYYYMMDD HH:MM,open,high,low,close,volume`
- from the zips we load a DuckDB database: table `raw_ohlcv_1h`
  - prices in the table = int ×10000; USD is only visible in the `ohlcv_1h` view
```

## Anti-pattern

"How not to" is shown by the full files `FLOW/L*.md`: sections, tables, roles
and invariants are correct as a reference, but as a summary they cause cognitive
overload — compound sentences, many facts per line, abstractions next to concretes.
A summary is exclusively an extract of actions and physical objects. Example sentences
we do not write in a summary:

- "The ingest layer is responsible for the acquisition of market data" — no file,
  folder or data is visible; physically it is unclear what was produced.
- "The data is processed, validated and stored" — three facts in one sentence and
  none of them is concrete.
