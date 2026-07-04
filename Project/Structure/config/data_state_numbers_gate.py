#!/usr/bin/env python3
"""Single-source generator + gate for the pipeline's derived documentation numbers.

The numbers in the docs are DERIVED, never hand-typed: feature counts come live from
Features/*/feature_registry.json (implemented==true) and config values come live from
config/*.json. Every place they appear is a *generated region*:
  - Markdown (root README.md + Project/endproduct/*.md): inline marker regions
        <!--na:KEY-->VALUE<!--/na-->   (HTML comments are invisible when rendered)
  - Plan/procedure_lego.html: rendered from Plan/procedure_lego.html.tmpl, where each
        literal is a {{KEY}} token (live feature counts + live config values).
  - Plan/configurations.html: rendered from Plan/configurations.html.tmpl — every config value
        (pipeline_parameters.json + xgboost_optuna_search_space.json + feature_namespaces.json
        registries) as a {{KEY}} token, so the page can never drift from config/.

The raw bars are the full upstream S&P 500 universe copied verbatim into liora.duckdb
(build_db.py) — not a committed set, so no bar/ticker count is frozen here.

Deliberately NOT scanned: anything under Assets/ (runtime artifacts).

Pure standard library (json/re/sys/pathlib). No third-party dependencies.

Commands
  init    one-time bootstrap: wrap raw literals in the scanned Markdown with marker regions.
          Safe to re-run (skips files that already have markers).
  build   re-render every marker value from the registry and render each Plan/*.html.tmpl
          -> Plan/*.html. Idempotent (writes only on change).
  check   audit gate (no writes, exit!=0 on drift). Invariants:
            (1) every marker region and generated HTML equals a fresh render from the registry;
            (2) no stray data-state literal exists outside a marker / {{token}};
            (3) Procedure Lego <-> SOT crossmatch: the MODULES ids and depends in the .tmpl [J1]
                match the "Kontrakt replikacji" blocks in Project/endproduct/Layers_Short_SOT.md.

Run from anywhere:  python3 config/data_state_numbers_gate.py {init|build|check}
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent           # .../Project/Structure
REPO = ROOT.parent.parent                                # repo root
PLAN = REPO / "Plan"

PIPELINE_PARAMETERS_JSON = ROOT / "config" / "pipeline_parameters.json"
XGBOOST_OPTUNA_SEARCH_SPACE_JSON = ROOT / "config" / "xgboost_optuna_search_space.json"
FEATURE_NAMESPACES_JSON = ROOT / "config" / "feature_namespaces.json"
SOT_MD = REPO / "Project" / "endproduct" / "Layers_Short_SOT.md"

LEGO_HTML = PLAN / "procedure_lego.html"
LEGO_TMPL = PLAN / "procedure_lego.html.tmpl"
CONFIG_HTML = PLAN / "configurations.html"
CONFIG_TMPL = PLAN / "configurations.html.tmpl"

# Ordered data-state literal rules: (compiled regex matching the raw literal, context key).
# Kept deliberately narrow — only unambiguous phrasings; everything else is structural
# (markers / tokens written by hand or by init).
RULES = [
    (re.compile(r'\b56\b(?=(-feature|\s+(X\b|features?\b|numeric features\b|namespaced features\b|effective)))'),
     'n_features_total'),
]

MARKER_RE = re.compile(r'<!--na:(\w+)-->(.*?)<!--/na-->')
BRACE_RE = re.compile(r'\{\{(\w+)\}\}')


def strict_json_loads(text):
    """json.loads that rejects duplicate keys (a silent-drift vector in hand-edited registries)."""
    def no_dupes(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError('duplicate JSON key: ' + k)
            d[k] = v
        return d
    return json.loads(text, object_pairs_hook=no_dupes)


def feature_counts():
    """Live implemented-feature counts from the machine registries (never hand-declared)."""
    ns_cfg = strict_json_loads(FEATURE_NAMESPACES_JSON.read_text(encoding='utf-8'))
    counts, total = {}, 0
    for ns in ns_cfg['namespace_order']:
        reg = strict_json_loads((ROOT / ns_cfg['namespaces'][ns]['registry']).read_text(encoding='utf-8'))
        n = sum(1 for f in reg['features'] if f.get('implemented', True))
        counts['n_features_{}'.format(ns)] = n
        total += n
    counts['n_features_total'] = total
    return counts


def marker_context():
    """Render context for the Markdown `na:` markers: live feature counts (implemented==true)."""
    return feature_counts()


def _fmt(v):
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, list):
        return ', '.join(_fmt(x) for x in v)
    return str(v)


def flatten_config():
    """Every config value flattened into `{{KEY}}` tokens (live — the pages can never drift):
    pipeline_parameters.json scalars as `KEY`, nested dicts as `BLOCK_KEY` (e.g. `splits_train_start`,
    `KELLY_CALIBRATION_grid_points`); the search space as `xgb_<name>_{type,low,high,log}` +
    `xgb_obj_<k>`; friendly aliases `n_trials` / `cv_folds`."""
    ctx = {}
    params = strict_json_loads(PIPELINE_PARAMETERS_JSON.read_text(encoding='utf-8'))
    for k, v in params.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                ctx['{}_{}'.format(k, kk)] = _fmt(vv)
        else:
            ctx[k] = _fmt(v)
    space = strict_json_loads(XGBOOST_OPTUNA_SEARCH_SPACE_JSON.read_text(encoding='utf-8'))
    for p in space['parameters']:
        n = p['name']
        ctx['xgb_{}_type'.format(n)] = _fmt(p.get('suggest'))
        ctx['xgb_{}_low'.format(n)] = _fmt(p.get('low'))
        ctx['xgb_{}_high'.format(n)] = _fmt(p.get('high'))
        ctx['xgb_{}_log'.format(n)] = 'log' if p.get('log') else '—'
    for k, v in space['objective'].items():
        ctx['xgb_obj_{}'.format(k)] = _fmt(v)
    ctx['n_trials'] = _fmt(params['N_TRIALS'])
    ctx['cv_folds'] = _fmt(space['objective']['cv_folds'])
    return ctx


def page_context():
    """One render context for both generated pages: data-state + feature counts + config."""
    ctx = marker_context()
    ctx.update(flatten_config())
    return ctx


def md_files():
    """Authored Markdown under the gate: root README.md + Project/endproduct/*.md.
    Excludes the frozen dated report and anything under Assets/ (see module docstring)."""
    paths = [REPO / 'README.md']
    endproduct = REPO / 'Project' / 'endproduct'
    if endproduct.is_dir():
        paths += [p for p in sorted(endproduct.glob('*.md'))]
    return [p for p in paths if p.exists() and 'Assets' not in p.parts]


# ---------- init (one-time tokenization) ----------

def tokenize_markers(text, reg):
    for rx, key in RULES:
        repl = '<!--na:{k}-->{v}<!--/na-->'.format(k=key, v=reg[key])
        text = rx.sub(lambda m, r=repl: r, text)
    return text


def cmd_init(reg):
    changed = 0
    for p in md_files():
        src = p.read_text(encoding='utf-8')
        if '<!--na:' in src:
            print('skip (already has markers):', p.relative_to(REPO))
            continue
        out = tokenize_markers(src, reg)
        if out != src:
            p.write_text(out, encoding='utf-8')
            changed += 1
            print('wrapped:', p.relative_to(REPO))
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
            raise KeyError('unknown token in template: ' + key)
        return str(reg[key])
    return BRACE_RE.sub(sub, text)


def render_html(tmpl_path, html_path, ctx):
    if not tmpl_path.exists():
        print('WARN: missing template', tmpl_path.relative_to(REPO))
        return
    html = render_braces(tmpl_path.read_text(encoding='utf-8'), ctx)
    if not html_path.exists() or html_path.read_text(encoding='utf-8') != html:
        html_path.write_text(html, encoding='utf-8')
        print('rendered:', html_path.relative_to(REPO))


def cmd_build(marker_ctx, page_ctx):
    n = 0
    for p in md_files():
        src = p.read_text(encoding='utf-8')
        out = render_markers(src, marker_ctx)
        if out != src:
            p.write_text(out, encoding='utf-8')
            n += 1
            print('rebuilt markers:', p.relative_to(REPO))
    render_html(LEGO_TMPL, LEGO_HTML, page_ctx)
    render_html(CONFIG_TMPL, CONFIG_HTML, page_ctx)
    print('build done; markdown files updated:', n)


# ---------- check ----------

def check_html(tmpl_path, html_path, ctx, errors):
    rel = tmpl_path.relative_to(REPO)
    if not tmpl_path.exists():
        errors.append('{}: missing template'.format(rel))
        return
    tmpl = tmpl_path.read_text(encoding='utf-8')
    for i, line in enumerate(tmpl.splitlines(), 1):
        stripped = BRACE_RE.sub('', line)
        for rx, key in RULES:
            if rx.search(stripped):
                errors.append('{}:{}: stray literal ({}) not tokenized: {}'.format(rel, i, key, line.strip()[:90]))
                break
    rendered = render_braces(tmpl, ctx)
    if not html_path.exists():
        errors.append('{}: missing rendered output (run build)'.format(html_path.relative_to(REPO)))
    elif html_path.read_text(encoding='utf-8') != rendered:
        errors.append('{}: differs from a fresh render (run build)'.format(html_path.relative_to(REPO)))


MODULE_ID_RE = re.compile(r'\{id:"([^"]+)"')
DEPENDS_RE = re.compile(r'depends:\[([^\]]*)\]')
SOT_BLOCK_RE = re.compile(r'^## Kontrakt replikacji — (\S+)', re.M)
SOT_DEPENDS_RE = re.compile(r'^- \*\*DEPENDS:\*\* upstream: ([^·]*)·', re.M)


def _parse_lego_modules(tmpl_text, errors):
    """Module ids + depends from the [J1] MODULES literal of the Procedure Lego template."""
    m = re.search(r'const MODULES\s*=\s*\[(.*?)\n\s*\];', tmpl_text, re.S)
    if not m:
        errors.append('procedure_lego.html.tmpl: cannot locate the MODULES literal ([J1])')
        return {}
    body = m.group(1)
    modules = {}
    starts = [(x.start(), x.group(1)) for x in MODULE_ID_RE.finditer(body)]
    for i, (pos, mid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(body)
        dm = DEPENDS_RE.search(body, pos, end)
        deps = []
        if dm and dm.group(1).strip():
            deps = [d.strip().strip('"') for d in dm.group(1).split(',')]
        modules[mid] = deps
    return modules


def _parse_sot_blocks(sot_text):
    """Block ids + upstream depends from the SOT 'Kontrakt replikacji' sections."""
    ids = SOT_BLOCK_RE.findall(sot_text)
    blocks = {}
    sections = re.split(r'^## Kontrakt replikacji — ', sot_text, flags=re.M)[1:]
    for sec in sections:
        mid = sec.split(None, 1)[0]
        ups = []
        dm = SOT_DEPENDS_RE.search(sec)
        if dm:
            raw = dm.group(1).strip()
            if raw and raw != '—':
                ups = [x.strip() for x in raw.split(',') if x.strip() and x.strip() != '—']
        blocks[mid] = ups
    return ids, blocks


def check_lego_sot_crossmatch(errors):
    """Fail-closed: the Lego MODULES ([J1]) must mirror the SOT blocks 1:1 (ids + depends)."""
    if not LEGO_TMPL.exists() or not SOT_MD.exists():
        errors.append('crossmatch: missing {} or {}'.format(LEGO_TMPL.name, SOT_MD.name))
        return
    modules = _parse_lego_modules(LEGO_TMPL.read_text(encoding='utf-8'), errors)
    if not modules:
        return
    sot_ids, sot_deps = _parse_sot_blocks(SOT_MD.read_text(encoding='utf-8'))
    only_lego = sorted(set(modules) - set(sot_ids))
    only_sot = sorted(set(sot_ids) - set(modules))
    if only_lego:
        errors.append('crossmatch: MODULES without a SOT block: {}'.format(', '.join(only_lego)))
    if only_sot:
        errors.append('crossmatch: SOT blocks without a MODULE: {}'.format(', '.join(only_sot)))
    for mid in sorted(set(modules) & set(sot_deps)):
        if sorted(modules[mid]) != sorted(sot_deps[mid]):
            errors.append('crossmatch: {} depends mismatch: lego={} sot={}'
                          .format(mid, modules[mid], sot_deps[mid]))


def strip_markers_line(line):
    return MARKER_RE.sub(lambda m: '', line)


def cmd_check(marker_ctx, page_ctx):
    errors = []

    for p in md_files():
        rel = p.relative_to(REPO)
        src = p.read_text(encoding='utf-8')
        if render_markers(src, marker_ctx) != src:
            errors.append('{}: marker region(s) out of sync with registry (run build)'.format(rel))
        for i, line in enumerate(src.splitlines(), 1):
            bare = strip_markers_line(line)
            for rx, key in RULES:
                if rx.search(bare):
                    errors.append('{}:{}: stray data-state literal ({}) outside marker: {}'
                                  .format(rel, i, key, line.strip()[:90]))
                    break

    check_html(LEGO_TMPL, LEGO_HTML, page_ctx, errors)
    check_html(CONFIG_TMPL, CONFIG_HTML, page_ctx, errors)
    check_lego_sot_crossmatch(errors)

    if errors:
        print('CHECK FAILED ({} issue(s)):'.format(len(errors)))
        for e in errors:
            print('  -', e)
        return 1
    print('CHECK OK: derived numbers in sync; no stray literals; lego<->SOT crossmatch holds.')
    return 0


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in ('init', 'build', 'check'):
        print(__doc__)
        return 2
    mctx = marker_context()
    if args[0] == 'init':
        cmd_init(mctx)
        return 0
    pctx = page_context()
    if args[0] == 'build':
        cmd_build(mctx, pctx)
        return 0
    return cmd_check(mctx, pctx)


if __name__ == '__main__':
    sys.exit(main())
