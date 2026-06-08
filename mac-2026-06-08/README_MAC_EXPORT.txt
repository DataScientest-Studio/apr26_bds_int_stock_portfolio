Mac export created on 2026-06-08.

Included:
- fetch_data.py
- app.py
- src/
- requirements.txt
- README.md
- DATA_AUDIT.md

Status:
- Python source files compiled successfully with python3 -m compileall.
- Local credential files were created.
- A smoke-test data download was completed successfully for 20 tickers.

To download data on your Mac:
1. Install dependencies:
   pip install -r requirements.txt
2. Run a smoke test:
   python fetch_data.py --limit 20 --batch-size 10
3. Run the full download when ready:
   python fetch_data.py --batch-size 10

Downloaded files will be written into the data/ folder.
