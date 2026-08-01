#!/usr/bin/env python3
"""Render a ZMK ErgoDox keymap into a self-contained visual layout tour (HTML).

Reads config/slicemk_ergodox.keymap and emits a single index.html with all CSS
and JS inlined (works as a GitHub Pages site and as a standalone file).

Usage: render_keymap.py <keymap-file> [--out index.html] [--commit SHA]
                        [--date ISO] [--repo-url URL]
"""
import argparse
import html
import re
import sys

# ---------------------------------------------------------------------------
# Physical position map (from the keymap's own comment). col 1..7 left->right,
# row 1..5 top->bottom, per half.
# ---------------------------------------------------------------------------
# Each half is three grids inside one container: the outer 6 columns, the inner
# column, and the thumb cluster — each positioned by translation/rotation.
U, GAP, PITCH = 52, 6, 58                 # 1u key, gap, pitch
U15 = 81                                  # 1.5u = 1.5*PITCH - GAP
MAIN_W = U15 + 5 * U + 5 * GAP            # width of the 6-column outer grid (371)

# --- Outer 6 columns: pos -> (col 1..6, row 1..5). Col 1 is the 1.5u outer
#     pinky column on the left half; on the right it's col 6. ---
OUTER_L = {
    1: (1, 1), 2: (2, 1), 3: (3, 1), 4: (4, 1), 5: (5, 1), 6: (6, 1),
    15: (1, 2), 16: (2, 2), 17: (3, 2), 18: (4, 2), 19: (5, 2), 20: (6, 2),
    29: (1, 3), 30: (2, 3), 31: (3, 3), 32: (4, 3), 33: (5, 3), 34: (6, 3),
    41: (1, 4), 42: (2, 4), 43: (3, 4), 44: (4, 4), 45: (5, 4), 46: (6, 4),
    55: (1, 5), 56: (2, 5), 57: (3, 5), 58: (4, 5), 59: (5, 5),
}
OUTER_R = {
    9: (1, 1), 10: (2, 1), 11: (3, 1), 12: (4, 1), 13: (5, 1), 14: (6, 1),
    23: (1, 2), 24: (2, 2), 25: (3, 2), 26: (4, 2), 27: (5, 2), 28: (6, 2),
    35: (1, 3), 36: (2, 3), 37: (3, 3), 38: (4, 3), 39: (5, 3), 40: (6, 3),
    49: (1, 4), 50: (2, 4), 51: (3, 4), 52: (4, 4), 53: (5, 4), 54: (6, 4),
    60: (2, 5), 61: (3, 5), 62: (4, 5), 63: (5, 5), 64: (6, 5),
}
# columnar stagger (px) per display column 1..6 — ErgoDox finger curve
OFF_L6 = {1: 9, 2: 9, 3: -2, 4: -9, 5: -2, 6: 3}
OFF_R6 = {1: 3, 2: -2, 3: -9, 4: -2, 5: 9, 6: 9}

# --- Inner column: (pos, top_y_px, height_px). Edges align to the adjacent
#     alpha column: Hyper (1u) on the numeral row; middle key top = T/Y top;
#     lower key bottom = B/N bottom. ---
INNER_L = [(7, 3, U), (21, 61, U15), (47, 148, U15)]
INNER_R = [(8, 3, U), (22, 61, U15), (48, 148, U15)]

# --- Thumb cluster: pos -> (col, row, colspan, rowspan). Nothing above the
#     OUTER big key; the inner column is a 3-tall strip nearest the centre. ---
THUMB_L = {
    65: (2, 1, 1, 1), 66: (3, 1, 1, 1),
    69: (1, 2, 1, 2), 70: (2, 2, 1, 2),
    71: (3, 2, 1, 1), 75: (3, 3, 1, 1),
}
THUMB_R = {
    68: (2, 1, 1, 1), 67: (1, 1, 1, 1),
    73: (2, 2, 1, 2), 74: (3, 2, 1, 2),
    72: (1, 2, 1, 1), 76: (1, 3, 1, 1),
}

LAYER_NODES = {
    "base_layer": ("BASE", 0),
    "symbol_layer": ("SYMB", 1),
    "nav_layer": ("NAVI", 2),
    "nav3_layer": ("NAV3", 3),
}
LAYER_SHORT = {0: "BASE", 1: "SYMB", 2: "NAVI", 3: "NAV3"}
LAYER_BY_NAME = {"BASE": "BASE", "SYMB": "SYMB", "NAVI": "NAVI", "NAV3": "NAV3"}


def layer_label(arg):
    """Resolve a layer reference that may be a #define name or a number."""
    if arg in LAYER_BY_NAME:
        return LAYER_BY_NAME[arg]
    try:
        return LAYER_SHORT.get(int(arg), arg)
    except ValueError:
        return arg

# ---------------------------------------------------------------------------
# Keycode -> printable label
# ---------------------------------------------------------------------------
KEY = {
    "ESC": "esc", "TAB": "tab", "BSPC": "⌫", "DEL": "del", "RET": "⏎",
    "SPACE": "␣", "GRAVE": "`", "MINUS": "-", "EQUAL": "=", "UNDER": "_",
    "PLUS": "+", "LBKT": "[", "RBKT": "]", "LBRC": "{", "RBRC": "}",
    "LPAR": "(", "RPAR": ")", "BSLH": "\\", "PIPE": "|", "SEMI": ";",
    "SQT": "'", "COLON": ":", "COMMA": ",", "DOT": ".", "FSLH": "/",
    "QMARK": "?", "EXCL": "!", "AT": "@", "HASH": "#", "DLLR": "$",
    "PRCNT": "%", "CARET": "^", "AMPS": "&", "ASTRK": "*", "TILDE": "~",
    "LT": "<", "GT": ">",
    "LEFT": "←", "RIGHT": "→", "UP": "↑", "DOWN": "↓",
    "PG_UP": "PgUp", "PG_DN": "PgDn", "HOME": "Home", "END": "End",
    "CAPS": "Caps",
    "C_VOL_UP": "Vol +", "C_VOL_DN": "Vol −", "C_MUTE": "Mute",
    "C_AC_SEARCH": "Search",
    "C_AC_DESKTOP_SHOW_ALL_WINDOWS": "Exposé",
    "C_VOICE_COMMAND": "Voice",
    "KP_PLUS": "＋", "KP_MULTIPLY": "×", "KP_MINUS": "−",
    "LSHFT": "⇧", "RSHFT": "⇧", "LCTRL": "⌃", "RCTRL": "⌃",
    "LALT": "⌥", "RALT": "⌥", "LGUI": "⌘", "RGUI": "⌘",
}
MOD_SYM = {"LS": "⇧", "RS": "⇧", "LC": "⌃", "RC": "⌃",
           "LA": "⌥", "RA": "⌥", "LG": "⌘", "RG": "⌘"}


def resolve_code(code):
    """Return (label, category) for a single keycode / modifier expression."""
    code = code.strip()
    if code in ("LS(LC(LALT))",):
        return "Meh", "mod"
    if code in ("LS(LC(LA(LGUI)))",):
        return "Hyper", "mod"
    m = re.match(r"^([LR][SCAG])\((.*)\)$", code)
    if m:
        mods = []
        inner = code
        while True:
            mm = re.match(r"^([LR][SCAG])\((.*)\)$", inner)
            if not mm:
                break
            mods.append(MOD_SYM[mm.group(1)])
            inner = mm.group(2)
        inner_label, _ = resolve_code(inner)
        # dedupe while preserving order
        seen, ordered = set(), []
        for s in mods:
            if s not in seen:
                seen.add(s)
                ordered.append(s)
        return "".join(ordered) + inner_label, "shortcut"
    if re.fullmatch(r"N\d", code):
        return code[1], "num"
    if re.fullmatch(r"F\d+", code):
        return code, "num"
    if code in KEY:
        cat = "mod" if code in ("LSHFT", "RSHFT", "LCTRL", "RCTRL",
                                "LALT", "RALT", "LGUI", "RGUI") else "sym"
        if code.startswith("C_"):
            cat = "media"
        if code.startswith("KP_"):
            cat = "num"
        return KEY[code], cat
    if re.fullmatch(r"[A-Z]", code):
        return code, "alpha"
    return code, "sym"


def key_from_binding(token):
    """token like 'kp ESC' / 'mt LGUI BSPC'. Returns dict for rendering."""
    parts = token.split()
    beh = parts[0]
    args = parts[1:]
    d = {"main": "", "hold": "", "sub": "", "cat": "sym", "raw": "&" + token}

    if beh == "kp":
        lbl, cat = resolve_code(" ".join(args))
        d.update(main=lbl, cat=cat)
    elif beh == "sk":
        lbl, _ = resolve_code(" ".join(args))
        d.update(main=lbl, sub="sticky", cat="mod")
    elif beh == "sl":
        d.update(main=layer_label(args[0]), sub="→layer", cat="layer")
    elif beh == "mo":
        d.update(main=layer_label(args[0]), sub="hold", cat="layer")
    elif beh == "to":
        d.update(main=layer_label(args[0]), sub="switch", cat="layer")
    elif beh == "mt":
        holdlbl, _ = resolve_code(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=holdlbl, main=taplbl, cat="mod")
    elif beh == "lm":
        lay = layer_label(args[0])
        modlbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=modlbl, main=lay, sub="hold", cat="layer")
    elif beh == "df0":          # hold modifier / tap key
        holdlbl, _ = resolve_code(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=holdlbl, main=taplbl, cat="mod")
    elif beh == "df1":          # hold layer / tap key
        lay = layer_label(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=lay, main=taplbl, cat="layer")
    elif beh == "dfk":          # hold key / tap key
        holdlbl, _ = resolve_code(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=holdlbl, main=taplbl, cat="sym")
    elif beh == "df11":         # hold mouse btn / tap mouse btn
        d.update(hold="R‑clk", main="L‑clk", cat="mouse")
    elif beh in ("td_left", "td_right", "td_up", "td_down"):
        arrow = {"td_left": "←", "td_right": "→", "td_up": "↑", "td_down": "↓"}[beh]
        d.update(main=arrow, sub="mouse", cat="mouse")
    elif beh == "st_macro_0":
        d.update(main="-> ", sub="macro", cat="macro")
    elif beh == "st_macro_1":
        d.update(main="=> ", sub="macro", cat="macro")
    elif beh == "trans":
        d.update(main="▽", cat="trans")
    elif beh == "none":
        d.update(main="", cat="none")
    elif beh == "bootloader":
        d.update(main="BOOT", cat="system")
    elif beh == "caps_word":
        d.update(main="Caps", sub="word", cat="system")
    else:
        d.update(main=beh, cat="sym")
    return d


# ---------------------------------------------------------------------------
# Parse keymap
# ---------------------------------------------------------------------------
def strip_comment(block):
    """Strip the /* */ delimiters but PRESERVE the comment's internal
    indentation (dedented to the common margin) so nested notes stay legible."""
    block = block.strip()
    if block.startswith("/*"):
        block = block[2:]
    if block.endswith("*/"):
        block = block[:-2]
    raw = block.splitlines()
    # drop a leading "* " only on lines that use the star-column comment style
    lines = [re.sub(r"^\s*\*\s?", "", ln) if ln.lstrip().startswith("*") else ln
             for ln in raw]
    # the first line's text followed "/*", so it carries no column indent
    if lines:
        lines[0] = lines[0].lstrip()
    # dedent the continuation lines by their common leading whitespace
    cont = [l for l in lines[1:] if l.strip()]
    if cont:
        cut = min(len(l) - len(l.lstrip(" ")) for l in cont)
        lines = [lines[0]] + [l[cut:] if l.strip() else "" for l in lines[1:]]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(l.rstrip() for l in lines)


def parse_layers(text):
    layers = []
    for node, (short, idx) in LAYER_NODES.items():
        m = re.search(r"(/\*(?:[^*]|\*(?!/))*\*/)\s*" + node
                      + r"\s*\{\s*bindings\s*=\s*<(.*?)>;", text, re.S)
        if not m:
            continue
        desc = strip_comment(m.group(1))
        body = m.group(2)
        tokens = [t.strip() for t in body.split("&") if t.strip()]
        # tokens[0] == 'bootloader' (position 0), then positions 1..76
        binds = {}
        for i, tok in enumerate(tokens):
            binds[i] = tok
        layers.append({"short": short, "idx": idx, "desc": desc, "binds": binds})
    layers.sort(key=lambda x: x["idx"])
    return layers


def parse_combos(text):
    m = re.search(r"combos\s*\{(.*?)\n    \};", text, re.S)
    block = m.group(1) if m else ""
    groups = []
    cur = None
    pending_desc = None
    for raw in block.splitlines():
        line = raw.strip()
        hdr = re.match(r"/\*\s*(?:---\s*)?(.*?)\s*(?:---\s*)?\*/$", line)
        # section / group headers (single-line comments that are not the ➔ desc)
        if hdr and "➔" not in line and "key-positions" not in raw:
            title = hdr.group(1).strip()
            if title:
                cur = {"title": title, "combos": []}
                groups.append(cur)
            continue
        if "➔" in line:
            pending_desc = line.lstrip("*/ ").strip()
            continue
        cm = re.search(r"(c_\w+)\s*\{.*?key-positions\s*=\s*<([^>]*)>.*?"
                       r"bindings\s*=\s*<([^>]*)>.*?timeout-ms\s*=\s*<(\d+)>", raw)
        if cm and pending_desc is not None:
            tag = ""
            body = pending_desc
            mt = re.match(r"(LHS|RHS)\s+(.*)$", pending_desc)
            if mt:
                tag, body = mt.group(1), mt.group(2)
            if cur is None:
                cur = {"title": "", "combos": []}
                groups.append(cur)
            cur["combos"].append({
                "tag": tag, "text": body.strip(),
                "positions": cm.group(2).split(),
                "timeout": cm.group(4),
            })
            pending_desc = None
    # drop empty groups
    return [g for g in groups if g["combos"]]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def esc(s):
    return html.escape(s, quote=True)


def kc(label):
    """A mini keycap chip for the combos section."""
    label = label.strip()
    cls = "kc wide" if len(label) > 2 else "kc"
    return f'<span class="{cls}">{esc(label) or "&nbsp;"}</span>'


def render_key(token, style="", extra=""):
    if token is None:
        return ""
    d = key_from_binding(token)
    cls = ["key", "cat-" + d["cat"]]
    if extra:
        cls.append(extra)
    if d["cat"] in ("trans", "none"):
        cls.append("ghost")
    hold = f'<span class="k-hold">{esc(d["hold"])}</span>' if d["hold"] else ""
    sub = f'<span class="k-sub">{esc(d["sub"])}</span>' if d["sub"] else ""
    main = esc(d["main"]) or "&nbsp;"
    meaning = describe(d)
    title = esc(d["raw"] + ("  —  " + meaning if meaning else ""))
    return (f'<div class="{" ".join(cls)}" style="{style}" title="{title}">'
            f'{hold}<span class="k-main">{main}</span>{sub}</div>')


def describe(d):
    bits = []
    if d["hold"]:
        bits.append(f'hold {d["hold"]}')
    if d["main"]:
        verb = "tap " if d["hold"] else ""
        bits.append(verb + d["main"])
    if d["sub"]:
        bits.append("(" + d["sub"] + ")")
    return " / ".join(bits)


def render_half(binds, side, layer_short):
    outer = OUTER_L if side == "left" else OUTER_R
    off = OFF_L6 if side == "left" else OFF_R6
    inner = INNER_L if side == "left" else INNER_R
    thumb = THUMB_L if side == "left" else THUMB_R

    # grid 1: outer 6 columns (with per-column stagger)
    cells = [f'<div class="cell" style="grid-column:{c};grid-row:{r}">'
             + render_key(binds.get(p), f"transform:translateY({off[c]}px)")
             + "</div>" for p, (c, r) in outer.items()]
    g_main = f'<div class="g-main">{"".join(cells)}</div>'

    # grid 2: inner column (absolute keys, edges aligned to the alpha column)
    ikeys = [render_key(binds.get(p), f"top:{top}px;height:{h}px",
                        "tall" if h > U else "") for p, top, h in inner]
    g_inner = f'<div class="g-inner">{"".join(ikeys)}</div>'

    # grid 3: thumb cluster (its own grid, positioned + rotated via CSS)
    tcells = [f'<div class="cell" style="grid-column:{c} / span {cs};'
              f'grid-row:{r} / span {rs}">'
              + render_key(binds.get(p), "", "big" if rs > 1 else "") + "</div>"
              for p, (c, r, cs, rs) in thumb.items()]
    g_thumb = f'<div class="g-thumb">{"".join(tcells)}</div>'

    label = "LHS" if side == "left" else "RHS"
    head = (f'<div class="half-head"><span class="half-side">{label}</span>'
            f'<span class="half-layer">{esc(layer_short)}</span></div>')
    cluster = f'<div class="cluster {side}">{g_main}{g_inner}{g_thumb}</div>'
    # the stage reserves the (optionally scaled) footprint so the card hugs it
    stage = f'<div class="stage">{cluster}</div>'
    return f'<div class="half {side}">{head}{stage}</div>'


def render_board(binds, layer_short):
    left = render_half(binds, "left", layer_short)
    right = render_half(binds, "right", layer_short)
    return (f'<div class="board-scroll"><div class="board">'
            f'{left}{right}</div></div>')


def render_notes(full):
    """Format the layer's keymap comment as legible HTML: each source line is a
    block padded to its own indent (so wrapped text hangs under the first char),
    section labels ending in ':' are emphasised, and &behaviour tokens tinted."""
    lines = full.splitlines()
    out = []
    started = False
    gap = '<div class="nl gap"></div>'
    for ln in lines:
        if not ln.strip():
            if out and out[-1] != gap:
                out.append(gap)
            continue
        m = re.match(r"^( *)(.*)$", ln.rstrip())
        indent, text = len(m.group(1)), esc(m.group(2))
        # template rule: an extra line break between top-level comments (a line
        # at indent 0 starts a new comment; its indented children stay grouped).
        if started and indent == 0 and (not out or out[-1] != gap):
            out.append(gap)
        text = re.sub(r"(&amp;[a-z][a-z0-9_]*)", r'<span class="tok">\1</span>', text)
        cls = "nl nh" if m.group(2).rstrip().endswith(":") else "nl"
        out.append(f'<div class="{cls}" style="--i:{indent}">{text}</div>')
        started = True
    return "".join(out)


def render_layer(layer):
    idx = layer["idx"]
    full = layer["desc"]
    first = full.splitlines()[0] if full else ""
    summary = first.split("—", 1)[1].strip() if "—" in first else first
    summary = summary.rstrip(".")
    return f'''
  <section class="layer" id="layer-{idx}">
    <div class="layer-head">
      <span class="eyebrow">layer {idx} · 0x0{idx}</span>
      <h2>{LAYER_SHORT[idx]}</h2>
      <span class="summary">{esc(summary)}</span>
    </div>
    {render_board(layer["binds"], LAYER_SHORT[idx])}
    <details class="notes"><summary>Layer notes · straight from the keymap comments</summary>
      <div class="desc">{render_notes(full)}</div>
    </details>
  </section>'''


def render_combos(groups):
    out = ['<section class="combos" id="combos"><div class="sec-head">'
           '<span class="eyebrow">chords</span><h2>Combos</h2></div>'
           '<p class="lead">Press these keys together to fire a single action. '
           'Same-hand chords use a 50&#8202;ms window; cross-hand chords 65&#8202;ms.</p>']
    for g in groups:
        out.append(f'<h3 class="combo-group">{esc(g["title"])}</h3>')
        out.append('<div class="chip-row">')
        for c in g["combos"]:
            tag = (f'<span class="chip-tag t-{c["tag"].lower()}">{c["tag"]}</span>'
                   if c["tag"] else "")
            keys, _, effect = c["text"].partition("➔")
            keycaps = '<span class="plus">+</span>'.join(
                kc(k) for k in keys.strip().split("+"))
            effect = effect.strip()
            fx = kc(effect) if effect and " " not in effect else \
                f'<span class="chip-fx">{esc(effect)}</span>'
            out.append(
                f'<div class="chip">{tag}<span class="chip-keys">{keycaps}</span>'
                f'<span class="chip-arrow">➔</span>{fx}'
                f'<span class="chip-ms">{c["timeout"]}ms</span></div>')
        out.append('</div>')
    out.append('</section>')
    return "".join(out)


LEGEND = [
    ("cat-alpha", "Letters / symbols"),
    ("cat-mod", "Modifiers"),
    ("cat-layer", "Layer switch"),
    ("cat-shortcut", "Shortcut / arrows"),
    ("cat-media", "Media"),
    ("cat-mouse", "Mouse"),
    ("cat-system", "System"),
    ("cat-macro", "Macro"),
    ("ghost", "Transparent"),
]


def render_legend():
    swatches = "".join(
        f'<div class="leg"><span class="key {c} sw"></span>{esc(t)}</div>'
        for c, t in LEGEND)
    glossary = [
        ("hold / tap", "a two-tier key: the small label is what a hold does, "
                       "the big label is what a tap does"),
        ("sticky", "one-shot — applies to just the next key you press"),
        ("→layer", "one-shot layer: the next key comes from that layer"),
        ("▽", "transparent — falls through to the layer below"),
    ]
    gl = "".join(f'<div class="gl"><code>{esc(k)}</code><span>{esc(v)}</span></div>'
                 for k, v in glossary)
    return (f'<section class="legend" id="legend"><div class="sec-head">'
            f'<span class="eyebrow">key</span><h2>Legend</h2></div>'
            f'<div class="legend-grid">{swatches}</div>'
            f'<div class="glossary">{gl}</div></section>')


def build(keymap_text, meta):
    layers = parse_layers(keymap_text)
    combos = parse_combos(keymap_text)
    nav = "".join(
        f'<a href="#layer-{l["idx"]}" data-target="layer-{l["idx"]}">'
        f'{LAYER_SHORT[l["idx"]]}<span>{l["idx"]}</span></a>' for l in layers)
    layers_html = "".join(render_layer(l) for l in layers)
    ncombos = sum(len(g["combos"]) for g in combos)
    src = esc(meta["source"])
    commit = esc(meta["commit"])
    repo = esc(meta["repo_url"])
    commit_link = (f'<a href="{repo}/commit/{commit}">{commit[:7]}</a>'
                   if repo and commit and commit != "working copy" else commit)
    panel = meta.get("panel", True)
    fields = dict(
        css=CSS, js=JS + (JS_KNOBS if panel else ""), nav=nav, layers=layers_html,
        combos=render_combos(combos), legend=render_legend(),
        knobs=KNOBS if panel else "",
        nlayers=len(layers), ncombos=ncombos, src=src,
        commit=commit_link, date=esc(meta["date"]))
    # fragment mode: no doctype/html/head/body — for hosts that supply their own
    # document skeleton (e.g. the Artifact wrapper). Full mode is standalone.
    tmpl = BODY if meta.get("fragment") else HTML
    return tmpl.format(**fields)


CSS = r"""
:root{
  /* live-adjustable geometry — the knob panel writes these */
  --board-gap:319px; --thumb-inset:374px; --thumb-top:204px; --thumb-rot:18deg;
  /* Kanso Zen (dark) */
  --bg:#14171d; --panel:#1c1e25; --board:#090e13; --board-edge:#393b44;
  --cap:#22262d; --cap-hi:#31374504; --cap-line:#393b44; --ink:#c5c9c7;
  --ink-dim:#a4a7a4; --ink-faint:#717c7c; --hair:#262a31;
  --brass:#dca561; --teal:#7aa89f; --blue:#7fb4ca; --violet:#938aa9;
  --rose:#c4746e; --green:#98bb6c; --accent:#e6c384;
  --shadow:0 1px 0 #00000055,0 6px 16px -8px #000a;
  --font-sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --font-mono:ui-monospace,"SF Mono","JetBrains Mono","Cascadia Code",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:light){
  :root{
    /* Kanso Pearl (light) */
    --bg:#e6e4e0; --panel:#f2f1ef; --board:#cfceca; --board-edge:#b6b5b0;
    --cap:#fbfbf9; --cap-hi:#00000000; --cap-line:#d4d3cf; --ink:#22262d;
    --ink-dim:#545464; --ink-faint:#8b8b85; --hair:#d7d6d1;
    --brass:#836f4a; --teal:#5e857a; --blue:#4d699b; --violet:#766b90;
    --rose:#c84053; --green:#6f894e; --accent:#9a6a1f;
    --shadow:0 1px 0 #ffffff,0 6px 16px -10px #0003;
  }
}
:root[data-theme="dark"]{
  --bg:#14171d; --panel:#1c1e25; --board:#090e13; --board-edge:#393b44;
  --cap:#22262d; --cap-line:#393b44; --ink:#c5c9c7; --ink-dim:#a4a7a4;
  --ink-faint:#717c7c; --hair:#262a31; --brass:#dca561; --teal:#7aa89f;
  --blue:#7fb4ca; --violet:#938aa9; --rose:#c4746e; --green:#98bb6c;
  --accent:#e6c384; --shadow:0 1px 0 #00000055,0 6px 16px -8px #000a;
}
:root[data-theme="light"]{
  --bg:#e6e4e0; --panel:#f2f1ef; --board:#cfceca; --board-edge:#b6b5b0;
  --cap:#fbfbf9; --cap-line:#d4d3cf; --ink:#22262d; --ink-dim:#545464;
  --ink-faint:#8b8b85; --hair:#d7d6d1; --brass:#836f4a; --teal:#5e857a;
  --blue:#4d699b; --violet:#766b90; --rose:#c84053; --green:#6f894e;
  --accent:#9a6a1f; --shadow:0 1px 0 #ffffff,0 6px 16px -10px #0003;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font-sans);
  line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.eyebrow{font-family:var(--font-mono);font-size:11px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--ink-faint)}

/* header */
header.hero{border-bottom:1px solid var(--hair);padding:46px 0 30px;
  background:radial-gradient(120% 140% at 82% -10%,#ffffff08,transparent 60%)}
.hero h1{font-family:var(--font-mono);font-weight:650;font-size:clamp(26px,4.4vw,40px);
  margin:.35em 0 .15em;letter-spacing:-.01em;text-wrap:balance}
.hero h1 .brass{color:var(--brass)}
.hero p.tag{color:var(--ink-dim);max-width:60ch;margin:.2em 0 0;font-size:16px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.meta .m{font-family:var(--font-mono);font-size:12px;color:var(--ink-dim);
  background:var(--panel);border:1px solid var(--hair);border-radius:999px;
  padding:4px 11px}
.meta .m b{color:var(--ink);font-weight:600}

/* sticky nav */
nav.layers{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--hair)}
nav.layers .wrap{display:flex;gap:6px;padding-top:9px;padding-bottom:9px;flex-wrap:wrap}
nav.layers a{font-family:var(--font-mono);font-size:13px;color:var(--ink-dim);
  padding:6px 12px;border-radius:8px;display:flex;align-items:baseline;gap:7px;
  border:1px solid transparent}
nav.layers a span{font-size:10px;color:var(--ink-faint)}
nav.layers a:hover{background:var(--panel);text-decoration:none;color:var(--ink)}
nav.layers a.active{background:var(--panel);border-color:var(--hair);color:var(--ink)}
nav.layers a.active{box-shadow:inset 0 -2px 0 var(--accent)}

main{padding:8px 0 40px}
section{padding:34px 0;border-bottom:1px solid var(--hair)}
.layer-head,.sec-head{display:flex;align-items:baseline;gap:14px;margin-bottom:14px}
h2{font-family:var(--font-mono);font-weight:640;font-size:22px;margin:2px 0;
  letter-spacing:.02em}
.summary{color:var(--ink-dim);font-size:15px;font-style:italic}
.desc{font-family:var(--font-mono);font-size:12.5px;line-height:1.6;color:var(--ink-dim);
  margin:0;padding:14px 18px 16px;overflow-x:auto}
/* one block per source line; padding-left = its indent, so wrapped text hangs
   under the first character instead of falling back to the margin. */
.nl{white-space:pre-wrap;padding-left:calc(var(--i,0) * 1ch)}
.nl.nh{color:var(--ink);font-weight:650}
.nl.gap{height:.9em}
.desc .tok{color:var(--brass);font-weight:600}
.notes{margin-top:18px;border:1px solid var(--hair);border-radius:8px;
  background:var(--panel);overflow:hidden}
.notes>summary{cursor:pointer;font-family:var(--font-mono);font-size:11.5px;
  letter-spacing:.04em;color:var(--ink-dim);padding:10px 14px;list-style:none;
  user-select:none}
.notes>summary::-webkit-details-marker{display:none}
.notes>summary::before{content:"▸  ";color:var(--ink-faint)}
.notes[open]>summary::before{content:"▾  "}
.notes[open]>summary{border-bottom:1px solid var(--hair)}
.notes .desc{border-left:3px solid var(--accent)}

/* board */
/* let the board use the full viewport width (it's the centrepiece), not just
   the text column, so it never gets clipped by the page's max-width */
.board-scroll{overflow-x:auto;padding:12px 20px 6px;width:100vw;
  margin-inline:calc(50% - 50vw)}
/* the board is two half-clusters with a centre gap between them */
/* size to content (so the frame hugs the board) and centre with auto margins,
   which collapse to 0 when it overflows so BOTH sides stay scrollable */
.board{display:flex;align-items:flex-start;gap:var(--board-gap);
  width:fit-content;margin-inline:auto;
  background:var(--board);border:1px solid var(--board-edge);
  border-radius:16px;padding:24px 30px 30px;box-shadow:var(--shadow)}
:root{--u:52px}

/* each half wraps a heading landmark + the key cluster. The heading only shows
   once the halves stack (narrow screens); side-by-side it's hidden. */
.half{position:relative;flex:none;width:429px}
.half-head{display:none}
.stage{position:relative}
.cluster{position:relative;width:429px;height:496px;flex:none}

/* ---- stacked / card mode: below this width the two halves stack vertically,
   each in its own framed card with an LHS/RHS + layer-name landmark. The thumbs
   keep their natural inboard spread (as if the centre gap were still there), so
   the cluster is widened to CW to contain them and the whole thing is scaled to
   fit the viewport — no key overlaps, no clipping. ---- */
@media (max-width:960px){
  /* CW/CH = full content box of one half incl. the inboard thumb spread.
     --scale (set by JS to fit the viewport) shrinks the cluster on narrow
     screens — CSS calc can't derive a unitless ratio from vw, so JS owns it. */
  .board{--cw:562px; --ch:430px;
    flex-direction:column;align-items:center;gap:22px;
    background:transparent;border:none;box-shadow:none;padding:4px 0}
  .board-scroll{padding:12px 8px 6px;overflow-x:auto}
  .half{width:fit-content;max-width:100%;
    background:var(--board);border:1px solid var(--board-edge);
    border-radius:16px;box-shadow:var(--shadow);padding:14px 20px 20px}
  .half-head{display:flex;align-items:baseline;gap:10px;margin-bottom:10px;
    padding:0 2px}
  .half-side{font-family:var(--font-mono);font-weight:700;font-size:12px;
    letter-spacing:.14em;color:var(--accent)}
  .half-layer{font-family:var(--font-mono);font-size:12px;color:var(--ink-faint);
    letter-spacing:.08em;text-transform:uppercase}
  .stage{width:calc(var(--cw) * var(--scale,1));
    height:calc(var(--ch) * var(--scale,1));margin-inline:auto}
  .cluster{position:absolute;top:0;left:0;width:var(--cw);height:var(--ch);
    transform:scale(var(--scale,1));transform-origin:top left}
  /* the right half's thumb points into the (now absent) centre gap — shift the
     whole right cluster inboard so that spread lands inside the card instead. */
  .cluster.right{--rhs-shift:130px}
}
.g-main{position:absolute;top:0;display:grid;grid-auto-rows:var(--u);gap:6px}
.cluster.left  .g-main{left:0;grid-template-columns:81px repeat(5,var(--u))}
.cluster.right .g-main{left:calc(58px + var(--rhs-shift,0px));
  grid-template-columns:repeat(5,var(--u)) 81px}
.g-inner{position:absolute;top:0;width:var(--u)}
.cluster.left  .g-inner{left:377px}
.cluster.right .g-inner{left:var(--rhs-shift,0px)}
.g-inner .key{position:absolute;left:0;width:var(--u)}
.g-thumb{position:absolute;display:grid;grid-template-columns:repeat(3,var(--u));
  grid-auto-rows:var(--u);gap:6px}
.cluster.left  .g-thumb{left:var(--thumb-inset);top:var(--thumb-top);
  transform:rotate(var(--thumb-rot));transform-origin:50% 35%}
.cluster.right .g-thumb{left:calc(261px - var(--thumb-inset) + var(--rhs-shift,0px));
  top:var(--thumb-top);
  transform:rotate(calc(-1 * var(--thumb-rot)));transform-origin:50% 35%}
/* a 1.5u-tall key = 1.5 pitches minus one gap (matches the 2u thumb keys) */
.key.tall{height:calc(var(--u)*1.5 + 3px)}
.cell{display:flex}
.key{--c:var(--ink-dim);width:100%;height:100%;min-width:0;border-radius:8px;
  background:linear-gradient(var(--cap),color-mix(in srgb,var(--cap) 92%,#000));
  border:1px solid var(--cap-line);box-shadow:var(--shadow);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:1px;padding:3px;position:relative;overflow:hidden;cursor:default}
.key.big .k-main{font-size:15px}
.key::before{content:"";position:absolute;inset:0 0 auto 0;height:42%;
  background:linear-gradient(#ffffff10,transparent);pointer-events:none}
.k-main{font-family:var(--font-mono);font-size:14px;font-weight:600;color:var(--ink);
  line-height:1;text-align:center;z-index:1}
.k-hold{font-family:var(--font-mono);font-size:9px;color:var(--c);line-height:1;
  align-self:flex-start;z-index:1;font-weight:600}
.k-sub{font-family:var(--font-mono);font-size:8px;letter-spacing:.03em;
  color:var(--ink-faint);line-height:1;z-index:1;text-transform:uppercase}
/* category accents: a top stripe + tinted legend */
.key:not(.ghost){border-top:2px solid var(--c)}
.cat-alpha,.cat-sym,.cat-num{--c:var(--cap-line)}
.cat-num .k-main{color:var(--ink)}
.cat-mod{--c:var(--brass)} .cat-mod .k-main{color:var(--brass)}
.cat-layer{--c:var(--teal)} .cat-layer .k-main{color:var(--teal)}
.cat-shortcut{--c:var(--blue)} .cat-shortcut .k-main{color:var(--blue)}
.cat-media{--c:var(--violet)} .cat-media .k-main{color:var(--violet)}
.cat-mouse{--c:var(--violet)} .cat-mouse .k-main{color:var(--violet)}
.cat-system{--c:var(--rose)} .cat-system .k-main{color:var(--rose)}
.cat-macro{--c:var(--green)} .cat-macro .k-main{color:var(--green)}
.key.ghost{background:transparent;border-style:dashed;border-color:var(--hair);
  box-shadow:none}
.key.ghost::before{display:none}
.key.ghost .k-main{color:var(--ink-faint);font-size:12px;font-weight:400}

/* combos */
.lead{color:var(--ink-dim);max-width:64ch;margin:0 0 20px}
.combo-group{font-family:var(--font-mono);font-size:12px;letter-spacing:.05em;
  color:var(--ink-faint);text-transform:uppercase;margin:20px 0 10px;font-weight:600}
.chip-row{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:flex;align-items:center;gap:9px;background:var(--panel);
  border:1px solid var(--hair);border-radius:10px;padding:8px 11px;font-size:13px}
.chip-tag{font-family:var(--font-mono);font-size:9px;font-weight:700;padding:2px 5px;
  border-radius:5px;letter-spacing:.05em}
.t-lhs{background:color-mix(in srgb,var(--teal) 20%,transparent);color:var(--teal)}
.t-rhs{background:color-mix(in srgb,var(--blue) 20%,transparent);color:var(--blue)}
.chip-keys{display:inline-flex;align-items:center;gap:3px}
.kc{font-family:var(--font-mono);font-size:12px;font-weight:600;color:var(--ink);
  background:linear-gradient(var(--cap),color-mix(in srgb,var(--cap) 90%,#000));
  border:1px solid var(--cap-line);border-top-width:2px;border-radius:6px;
  min-width:23px;height:25px;display:inline-flex;align-items:center;
  justify-content:center;padding:0 6px;box-shadow:var(--shadow)}
.kc.wide{padding:0 9px}
.plus{color:var(--ink-faint);font-weight:600;font-family:var(--font-mono);margin:0 1px}
.chip-arrow{color:var(--accent);font-weight:700}
.chip-fx{color:var(--ink-dim)}
.chip-ms{font-family:var(--font-mono);font-size:10px;color:var(--ink-faint);
  margin-left:2px;border-left:1px solid var(--hair);padding-left:8px}

/* legend */
.legend-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
  gap:10px;margin-bottom:22px}
.leg{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--ink-dim)}
.key.sw{width:34px;height:26px;flex:none}
.key.sw::before{height:50%}
.glossary{display:grid;gap:10px}
.gl{display:flex;gap:12px;align-items:baseline;font-size:13.5px;color:var(--ink-dim);
  max-width:70ch}
.gl code{font-family:var(--font-mono);font-size:12px;color:var(--ink);background:var(--panel);
  border:1px solid var(--hair);border-radius:5px;padding:2px 7px;white-space:nowrap;flex:none;
  min-width:74px;text-align:center}

footer{padding:26px 0 60px;color:var(--ink-faint);font-size:12.5px;font-family:var(--font-mono)}
footer a{color:var(--ink-dim)}

/* live geometry knob panel */
.knobs{position:fixed;right:16px;bottom:16px;z-index:60;width:236px;
  background:color-mix(in srgb,var(--panel) 94%,transparent);backdrop-filter:blur(8px);
  border:1px solid var(--hair);border-radius:12px;box-shadow:0 10px 34px -10px #0008;
  font-family:var(--font-mono);font-size:12px;color:var(--ink);overflow:hidden}
.knobs-head{display:flex;justify-content:space-between;align-items:center;
  padding:9px 12px;border-bottom:1px solid var(--hair);letter-spacing:.08em;
  text-transform:uppercase;font-size:10px;color:var(--ink-faint)}
.knobs-head button{background:none;border:none;color:var(--ink-dim);cursor:pointer;
  font-size:15px;line-height:1;padding:0 3px}
.knobs-body{padding:11px 12px;display:grid;gap:13px}
.knobs.collapsed .knobs-body{display:none}
.knobs label{display:grid;gap:5px;color:var(--ink-dim)}
.knobs label output{color:var(--accent);font-weight:600}
.knobs input[type=range]{width:100%;accent-color:var(--accent);margin:0;cursor:pointer}
.knobs-out{border-top:1px solid var(--hair);padding-top:9px;color:var(--ink-faint);
  font-size:11px;line-height:1.5}
.knobs-copy{background:var(--bg);color:var(--ink-dim);border:1px solid var(--hair);
  border-radius:7px;padding:6px 10px;font-family:var(--font-mono);font-size:11px;
  cursor:pointer}
.knobs-copy:hover{border-color:var(--accent);color:var(--accent)}
@media (max-width:640px){.knobs{display:none}}
"""

JS = r"""
const links=[...document.querySelectorAll('nav.layers a')];
const secs=links.map(a=>document.getElementById(a.dataset.target)).filter(Boolean);
const io=new IntersectionObserver((es)=>{
  es.forEach(e=>{if(e.isIntersecting){
    const id=e.target.id;
    links.forEach(a=>a.classList.toggle('active',a.dataset.target===id));
  }});
},{rootMargin:'-45% 0px -50% 0px'});
secs.forEach(s=>io.observe(s));

// Fit each stacked half-card to the viewport. CSS calc can't turn vw into a
// unitless scale factor, so compute it here. Keep CW/MARGIN in sync with the
// stacked-mode CSS (--cw and the card/scroll padding around the stage).
(function(){
  const CW=562, MARGIN=64, MIN=0.4;
  const mq=window.matchMedia('(max-width:960px)');
  const boards=[...document.querySelectorAll('.board')];
  function fit(){
    const avail=document.documentElement.clientWidth-MARGIN;
    const s=mq.matches?Math.max(MIN,Math.min(1,avail/CW)):1;
    boards.forEach(b=>b.style.setProperty('--scale',String(s)));
  }
  fit();
  window.addEventListener('resize',fit,{passive:true});
  if(mq.addEventListener)mq.addEventListener('change',fit);
})();
"""

JS_KNOBS = r"""
// live geometry knobs -> CSS variables
(function(){
  const R=document.documentElement, out=document.getElementById('k-out');
  const map=[['k-gap','--board-gap','px'],['k-inset','--thumb-inset','px'],
             ['k-top','--thumb-top','px'],['k-rot','--thumb-rot','deg']];
  function refresh(){
    const g=id=>document.getElementById(id).value;
    out.textContent='gap '+g('k-gap')+' · inset '+g('k-inset')
      +' · top '+g('k-top')+' · angle '+g('k-rot');
  }
  map.forEach(([id,v,u])=>{
    const el=document.getElementById(id), o=document.getElementById(id+'-o');
    const upd=()=>{R.style.setProperty(v,el.value+u);o.textContent=el.value;refresh();};
    el.addEventListener('input',upd); upd();
  });
  document.getElementById('k-toggle').addEventListener('click',function(){
    const k=document.getElementById('knobs');k.classList.toggle('collapsed');
    this.textContent=k.classList.contains('collapsed')?'+':'–';
  });
  document.getElementById('k-copy').addEventListener('click',function(){
    if(navigator.clipboard)navigator.clipboard.writeText(out.textContent);
    this.textContent='copied';setTimeout(()=>this.textContent='copy values',1100);
  });
})();
"""

BODY = """<style>{css}</style>
<header class="hero"><div class="wrap">
  <span class="eyebrow">SliceMK ErgoDox Wireless · ZMK</span>
  <h1>Keymap <span class="brass">Layout Tour</span></h1>
  <p class="tag">A visual walk through every layer of the keymap — generated
     straight from the firmware config, so it can never drift out of date.</p>
  <div class="meta">
    <span class="m"><b>{nlayers}</b> layers</span>
    <span class="m"><b>{ncombos}</b> combos</span>
    <span class="m">source&nbsp;<b>{src}</b></span>
    <span class="m">rev&nbsp;<b>{commit}</b></span>
  </div>
</div></header>
<nav class="layers"><div class="wrap">{nav}
  <a href="#combos" data-target="combos">Combos<span>◇</span></a>
  <a href="#legend" data-target="legend">Legend<span>▤</span></a>
</div></nav>
<main class="wrap">
{layers}
{combos}
{legend}
</main>
<footer class="wrap">Auto-generated from <b>{src}</b> · rev {commit} · {date}.
  Edit the keymap, push, and this page rebuilds itself.</footer>
{knobs}
<script>{js}</script>
"""

HTML = ('<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>ErgoDox Keymap — Visual Tour</title></head><body>'
        + BODY + '</body></html>')

KNOBS = """<div class="knobs" id="knobs">
  <div class="knobs-head"><span>◐ geometry</span>
    <button id="k-toggle" title="collapse" aria-label="collapse">–</button></div>
  <div class="knobs-body">
    <label>center gap · <output id="k-gap-o">319</output>px
      <input type="range" id="k-gap" min="0" max="480" value="319"></label>
    <label>thumb inset · <output id="k-inset-o">374</output>px
      <input type="range" id="k-inset" min="240" max="430" value="374"></label>
    <label>thumb top · <output id="k-top-o">204</output>px
      <input type="range" id="k-top" min="120" max="300" value="204"></label>
    <label>thumb angle · <output id="k-rot-o">18</output>&deg;
      <input type="range" id="k-rot" min="0" max="34" value="18"></label>
    <div class="knobs-out" id="k-out"></div>
    <button class="knobs-copy" id="k-copy">copy values</button>
  </div>
</div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keymap")
    ap.add_argument("--out", default="-")
    ap.add_argument("--commit", default="working copy")
    ap.add_argument("--date", default="")
    ap.add_argument("--repo-url", default="")
    ap.add_argument("--source", default="config/slicemk_ergodox.keymap")
    ap.add_argument("--no-panel", dest="panel", action="store_false",
                    help="omit the live geometry knob panel (for publishing)")
    ap.add_argument("--fragment", action="store_true",
                    help="emit body content only (no <html>/<head>/<body>)")
    a = ap.parse_args()
    text = open(a.keymap, encoding="utf-8").read()
    out = build(text, {"commit": a.commit, "date": a.date,
                       "repo_url": a.repo_url, "source": a.source,
                       "panel": a.panel, "fragment": a.fragment})
    if a.out == "-":
        sys.stdout.write(out)
    else:
        open(a.out, "w", encoding="utf-8").write(out)
        print(f"wrote {a.out} ({len(out)} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
