#!/usr/bin/env python3
"""Single-source generator + gate for frozen data-state numbers of Pipeline A.

The ONLY hand-edited home for data-state numbers is ./data_state_numbers.json (same directory).
Every other place those numbers appear is a *generated region*:
  - Markdown (the SOT under ENG/Layers_Short_SOT/ + README_A_Layer.md): inline marker regions
        <!--na:KEY-->VALUE<!--/na-->   (HTML comments are invisible when rendered)
  - viz/main_data_flow.html: rendered from config/main_data_flow.html.tmpl, where each
        literal is a {{KEY}} token.

Pure standard library (json/re/sys/pathlib). No third-party dependencies.

Commands
  init    one-time bootstrap: wrap raw literals in Markdown with marker regions, and create
          the viz .tmpl from the current viz .html (literals -> {{KEY}} tokens).
  build   re-render every marker value from the registry and render the viz .tmpl -> .html. Idempotent.
  check   audit gate (no writes, exit!=0 on drift). Three invariants:
            (1) every output equals a fresh render from the registry;
            (2) no "stray" data-state literal exists outside a marker / the tmpl token / the registry;
            (3) excludes the registry and the generated viz .html (scanned: the SOT under
                ENG/Layers_Short_SOT/ + README_A_Layer.md).
          Genuine non-data-state coincidences (none exist today) can be allow-listed in
          config/data_state_allowlist.txt.

Run from anywhere:  python3 config/data_state_gate.py {init|build|check}
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # .../A_Layers
TOOLS = Path(__file__).resolve().parent
REGISTRY = ROOT / "config" / "data_state_numbers.json"
VIZ_HTML = ROOT / "viz" / "main_data_flow.html"
VIZ_TMPL = ROOT / "config" / "main_data_flow.html.tmpl"
ALLOWLIST = ROOT / "config" / "data_state_allowlist.txt"

# Ordered data-state literal rules: (compiled regex matching the raw literal, registry key).
# Order matters: longer / context-specific tokens first so they win before bare \b503\b etc.
RULES = [
    (re.compile(r'8 841 820'), 'duckdb_row_count_str'),
    (re.compile(r'8841820'), 'duckdb_row_count'),
    (re.compile(r'8\.84M'), 'duckdb_row_count_short'),
    (re.compile(r'\b139\b(?= MB)'), 'lean_zip_size_mb'),
    (re.compile(r'\b166\b(?= MB)'), 'duckdb_size_mb'),
    (re.compile(r'(?:(?<=[×x/])|(?<=times ))10000'), 'price_scale'),
    (re.compile(r'\[5,\s*9\]'), 'candles_per_day_range_str'),
    (re.compile(r'(?<=~)7\b'), 'candles_per_day_typical'),
    (re.compile(r'\b510\b'), 'lean_zip_count'),
    (re.compile(r'\b503\b'), 'universe_size'),
]

MARKER_RE = re.compile(r'<!--na:(\w+)-->(.*?)<!--/na-->')
BRACE_RE = re.compile(r'\{\{(\w+)\}\}')


def load_registry():
    raw = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return {k: v for k, v in raw.items() if not k.startswith('_')}


def md_files():
    # A_Layers is a self-contained SOT: scan every Markdown file (the SOT + README_A_Layer.md).
    return sorted(ROOT.rglob('*.md'))


def load_allowlist():
    if not ALLOWLIST.exists():
        return []
    pats = []
    for line in ALLOWLIST.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            pats.append(line)
    return pats


# ---------- init (one-time tokenization) ----------

def tokenize(text, reg, mode):
    """Replace each raw data-state literal. mode='marker' -> <!--na:KEY-->VALUE<!--/na-->
    (VALUE taken from the registry, so this also unifies formatting). mode='brace' -> {{KEY}}."""
    for rx, key in RULES:
        repl = '<!--na:{k}-->{v}<!--/na-->'.format(k=key, v=reg[key]) if mode == 'marker' else '{{' + key + '}}'
        text = rx.sub(lambda m, r=repl: r, text)
    return text


def cmd_init(reg):
    # One-time bootstrap (already run): wrap raw literals into markers + create the viz .tmpl.
    # Kept for onboarding any newly added file; safe to re-run (skips files that already have markers).
    changed = 0
    for p in md_files():
        src = p.read_text(encoding='utf-8')
        if '<!--na:' in src:
            print('skip (already has markers):', p.relative_to(ROOT))
            continue
        out = tokenize(src, reg, 'marker')
        if out != src:
            p.write_text(out, encoding='utf-8')
            changed += 1
            print('wrapped:', p.relative_to(ROOT))
    if VIZ_HTML.exists() and not VIZ_TMPL.exists():
        VIZ_TMPL.write_text(tokenize(VIZ_HTML.read_text(encoding='utf-8'), reg, 'brace'), encoding='utf-8')
        print('created viz template:', VIZ_TMPL.relative_to(ROOT))
    print('init done; files wrapped:', changed)


# ---------- build ----------

def render_markers(text, reg):
    def sub(m):
        key = m.group(1)
        if key not in reg:
            raise KeyError('unknown registry key in marker: ' + key)
        return '<!--na:{k}-->{v}<!--/na-->'.format(k=key, v=reg[key])
    return MARKER_RE.sub(sub, text)


def render_braces(text, reg):
    def sub(m):
        key = m.group(1)
        if key not in reg:
            raise KeyError('unknown registry key in viz tmpl: ' + key)
        return str(reg[key])
    return BRACE_RE.sub(sub, text)


def cmd_build(reg):
    n = 0
    for p in md_files():
        src = p.read_text(encoding='utf-8')
        out = render_markers(src, reg)
        if out != src:
            p.write_text(out, encoding='utf-8')
            n += 1
            print('rebuilt markers:', p.relative_to(ROOT))
    if VIZ_TMPL.exists():
        html = render_braces(VIZ_TMPL.read_text(encoding='utf-8'), reg)
        if not VIZ_HTML.exists() or VIZ_HTML.read_text(encoding='utf-8') != html:
            VIZ_HTML.write_text(html, encoding='utf-8')
            print('rendered viz:', VIZ_HTML.relative_to(ROOT))
    else:
        print('WARN: missing viz template', VIZ_TMPL.relative_to(ROOT))
    print('build done; markdown files updated:', n)


# ---------- check ----------

def strip_markers_line(line):
    return MARKER_RE.sub(lambda m: '', line)


def cmd_check(reg):
    errors = []
    allow = load_allowlist()

    def allowed(rel, lineno, line):
        tag = '{}:{}'.format(rel, lineno)
        return any(a == tag or a in line for a in allow)

    if str(reg['duckdb_row_count']) != reg['duckdb_row_count_str'].replace(' ', ''):
        errors.append('registry: duckdb_row_count_str != duckdb_row_count digits')

    # Markdown: (1) markers in sync, (2) no stray literal outside markers
    for p in md_files():
        rel = p.relative_to(ROOT)
        src = p.read_text(encoding='utf-8')
        if render_markers(src, reg) != src:
            errors.append('{}: marker region(s) out of sync with registry (run build)'.format(rel))
        for i, line in enumerate(src.splitlines(), 1):
            bare = strip_markers_line(line)
            for rx, key in RULES:
                if rx.search(bare) and not allowed(rel, i, line):
                    errors.append('{}:{}: stray data-state literal ({}) outside marker: {}'
                                  .format(rel, i, key, line.strip()[:90]))
                    break

    # viz: tmpl exists, has no stray literal, and renders byte-equal to committed html
    if not VIZ_TMPL.exists():
        errors.append('viz: missing main_data_flow.html.tmpl')
    else:
        tmpl = VIZ_TMPL.read_text(encoding='utf-8')
        for i, line in enumerate(tmpl.splitlines(), 1):
            stripped = BRACE_RE.sub('', line)
            for rx, key in RULES:
                if rx.search(stripped) and not allowed('config/main_data_flow.html.tmpl', i, line):
                    errors.append('viz tmpl:{}: stray literal ({}) not tokenized: {}'
                                  .format(i, key, line.strip()[:90]))
                    break
        rendered = render_braces(tmpl, reg)
        if not VIZ_HTML.exists():
            errors.append('viz: missing rendered main_data_flow.html (run build)')
        elif VIZ_HTML.read_text(encoding='utf-8') != rendered:
            errors.append('viz: main_data_flow.html differs from a fresh render (run build)')

    if errors:
        print('CHECK FAILED ({} issue(s)):'.format(len(errors)))
        for e in errors:
            print('  -', e)
        return 1
    print('CHECK OK: registry is the single source; all regions in sync; no stray literals.')
    return 0


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in ('init', 'build', 'check'):
        print(__doc__)
        return 2
    reg = load_registry()
    if args[0] == 'init':
        cmd_init(reg)
        return 0
    if args[0] == 'build':
        cmd_build(reg)
        return 0
    return cmd_check(reg)


if __name__ == '__main__':
    sys.exit(main())
