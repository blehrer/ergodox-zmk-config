#!/usr/bin/env python3
"""Render a ZMK ErgoDox keymap into a self-contained visual layout tour (HTML).

Reads config/slicemk_ergodox.keymap and emits a single index.html with all CSS
and JS inlined (works as a GitHub Pages site and as a standalone file).

Usage: render_keymap.py <keymap-file> [--out index.html] [--commit SHA]
                        [--date ISO] [--repo-url URL]
"""
import argparse
import html
import os
import re
import sys

# Static assets (CSS / JS / HTML templates) live as real files alongside this
# script and are inlined at build time, so the generated page stays a single
# self-contained file while the sources remain editable and reviewable.
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tour")


def asset(name):
    with open(os.path.join(ASSET_DIR, name), encoding="utf-8") as f:
        return f.read()

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
# ZMK mouse-button codes -> label (a constant code map, not a hardcoded value)
MOUSE_BTN = {"LCLK": "L‑clk", "RCLK": "R‑clk", "MCLK": "M‑clk",
             "MB4": "Btn 4", "MB5": "Btn 5"}

# macro name -> the literal text it types, derived from the keymap's own macro
# definitions (populated by parse_macros / build; never hardcoded here).
MACROS = {}


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


def mouse_label(code):
    return MOUSE_BTN.get(code, code)


def key_from_binding(token):
    """token like 'kp ESC' / 'mt LGUI BSPC'. Returns dict for rendering."""
    parts = token.split()
    prefix = parts[0]
    args = parts[1:]
    d = {"main": "", "hold": "", "sub": "", "cat": "sym", "raw": "&" + token}

    if prefix == "kp":
        lbl, cat = resolve_code(" ".join(args))
        d.update(main=lbl, cat=cat)
    elif prefix == "sk":
        lbl, _ = resolve_code(" ".join(args))
        d.update(main=lbl, sub="sticky", cat="mod")
    elif prefix == "sl":
        d.update(main=layer_label(args[0]), sub="→layer", cat="layer")
    elif prefix == "mo":
        d.update(main=layer_label(args[0]), sub="hold", cat="layer")
    elif prefix == "to":
        d.update(main=layer_label(args[0]), sub="switch", cat="layer")
    elif prefix in ("mt", "tmt"):   # mod-tap (tmt = tap-preferred thumb variant)
        holdlbl, _ = resolve_code(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=holdlbl, main=taplbl, cat="mod")
    elif prefix == "lm":
        lay = layer_label(args[0])
        modlbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=modlbl, main=lay, sub="hold", cat="layer")
    elif prefix == "df0":          # hold modifier / tap key
        holdlbl, _ = resolve_code(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=holdlbl, main=taplbl, cat="mod")
    elif prefix == "df1":          # hold layer / tap key
        lay = layer_label(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=lay, main=taplbl, cat="layer")
    elif prefix == "dfk":          # hold key / tap key
        holdlbl, _ = resolve_code(args[0])
        taplbl, _ = resolve_code(" ".join(args[1:]))
        d.update(hold=holdlbl, main=taplbl, cat="sym")
    elif prefix == "df11":         # hold mouse btn / tap mouse btn — derive both
        d.update(hold=mouse_label(args[0]), main=mouse_label(args[1]), cat="mouse")
    elif prefix == "mmv":
        arrow = {"MOVE_LEFT": "←", "MOVE_RIGHT": "→", "MOVE_UP": "↑", "MOVE_DOWN": "↓"}.get(args[0], args[0] if args else "")
        d.update(main=arrow, sub="mouse", cat="mouse")
    elif prefix in ("td_left", "td_right", "td_up", "td_down"):
        arrow = {"td_left": "←", "td_right": "→", "td_up": "↑", "td_down": "↓"}[prefix]
        d.update(main=arrow, sub="mouse", cat="mouse")
    elif prefix in MACROS:         # a macro: show the text it actually types
        d.update(main=MACROS[prefix], sub="macro", cat="macro")
    elif prefix == "trans":
        d.update(main="▽", cat="trans")
    elif prefix == "none":
        d.update(main="", cat="none")
    elif prefix == "bootloader":
        d.update(main="BOOT", cat="system")
    elif prefix in ("caps_word", "extended_caps_word"):
        d.update(main="Caps", sub="word", cat="system")
    else:
        d.update(main=prefix, cat="sym")
    return d


# ---------------------------------------------------------------------------
# Parse keymap
# ---------------------------------------------------------------------------
def parse_macros(text):
    """Derive each macro's typed text from the keymap's `macros` node, by
    decoding its &kp sequence (e.g. <&kp MINUS &kp GT &kp SPACE> -> '->␣')."""
    node = re.search(r"macros\s*\{(.*?)\n    \};", text, re.S)
    if not node:
        return {}
    macros = {}
    for m in re.finditer(r"(\w+)\s*:\s*\w+\s*\{.*?bindings\s*=\s*<([^>]*)>",
                         node.group(1), re.S):
        chars = [resolve_code(kp)[0]
                 for kp in re.findall(r"&kp\s+(\S+)", m.group(2))]
        macros[m.group(1)] = "".join(chars)
    return macros


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


def _centrality(pos):
    """How close a key position sits to the board's centre. Higher = more inner
    (index-finger side); lower = more outer (pinky side). Symmetric across hands
    so LHS and RHS combos can be ordered on the same inner→outer axis."""
    p = int(pos)
    if p in OUTER_L:
        return OUTER_L[p][0]          # left: col 6 is the innermost column
    if p in OUTER_R:
        return 7 - OUTER_R[p][0]      # right: col 1 is the innermost column
    return 0


def _inner_first(combo):
    """Sort key that orders a combo by its innermost finger first."""
    return sorted((_centrality(p) for p in combo["positions"]), reverse=True)


def _sort_inner_out(combos):
    return sorted(combos, key=_inner_first, reverse=True)


def parse_combos(text):
    """Return the combos sorted into four semantic buckets:

        {"lhs": [...], "rhs": [...],          # unpaired single-hand chords
         "isos": [(lhs, rhs), ...],           # mirror-image LHS/RHS pairs
         "twohand": [...]}                    # cross-hand chords

    Each combo is {"text", "positions", "timeout"}. Single-hand entries are
    ordered inner→outer; the isomorphic pairs are ordered by their left side.
    """
    m = re.search(r"combos\s*\{(.*?)\n    \};", text, re.S)
    block = m.group(1) if m else ""
    section = None                    # 'lhs' | 'rhs' | 'iso' (from --- headers)
    pending_desc = None
    lhs, rhs, iso_flat, twohand = [], [], [], []
    for raw in block.splitlines():
        line = raw.strip()
        hdr = re.match(r"/\*\s*(?:---\s*)?(.*?)\s*(?:---\s*)?\*/$", line)
        # section headers (single-line comments that are not the ➔ desc)
        if hdr and "➔" not in line and "key-positions" not in raw:
            title = hdr.group(1).lower()
            if "isomorphic" in title:
                section = "iso"
            elif "left" in title and "unpaired" in title:
                section = "lhs"
            elif "right" in title and "unpaired" in title:
                section = "rhs"
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
            combo = {"tag": tag, "text": body.strip(),
                     "positions": cm.group(2).split(), "timeout": cm.group(4)}
            # cross-hand chords carry no LHS/RHS tag even though they trail the
            # isomorphic section in the source, so route them by tag, not section.
            if section == "iso" and tag:
                iso_flat.append(combo)
            elif section == "lhs" or tag == "LHS":
                lhs.append(combo)
            elif section == "rhs" or tag == "RHS":
                rhs.append(combo)
            else:
                twohand.append(combo)
            pending_desc = None

    # fold the flat LHS,RHS,LHS,RHS,... stream into (lhs, rhs) pairs
    isos, pend = [], None
    for c in iso_flat:
        if c["tag"] == "LHS":
            pend = c
        elif c["tag"] == "RHS" and pend is not None:
            isos.append((pend, c))
            pend = None
    isos.sort(key=lambda pr: _inner_first(pr[0]), reverse=True)

    return {"lhs": _sort_inner_out(lhs), "rhs": _sort_inner_out(rhs),
            "isos": isos, "twohand": twohand}


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


def render_half(binds, side, layer_short, highlight=None):
    outer = OUTER_L if side == "left" else OUTER_R
    off = OFF_L6 if side == "left" else OFF_R6
    inner = INNER_L if side == "left" else INNER_R
    thumb = THUMB_L if side == "left" else THUMB_R
    hl = highlight or set()

    def extra(p, base=""):
        # tag positions that differ between the two revisions (diff mode)
        return (base + (" chg" if p in hl else "")).strip()

    # grid 1: outer 6 columns (with per-column stagger)
    cells = [f'<div class="cell" style="grid-column:{c};grid-row:{r}">'
             + render_key(binds.get(p), f"transform:translateY({off[c]}px)", extra(p))
             + "</div>" for p, (c, r) in outer.items()]
    g_main = f'<div class="g-main">{"".join(cells)}</div>'

    # grid 2: inner column (absolute keys, edges aligned to the alpha column)
    ikeys = [render_key(binds.get(p), f"top:{top}px;height:{h}px",
                        extra(p, "tall" if h > U else "")) for p, top, h in inner]
    g_inner = f'<div class="g-inner">{"".join(ikeys)}</div>'

    # grid 3: thumb cluster (its own grid, positioned + rotated via CSS)
    tcells = [f'<div class="cell" style="grid-column:{c} / span {cs};'
              f'grid-row:{r} / span {rs}">'
              + render_key(binds.get(p), "", extra(p, "big" if rs > 1 else "")) + "</div>"
              for p, (c, r, cs, rs) in thumb.items()]
    g_thumb = f'<div class="g-thumb">{"".join(tcells)}</div>'

    label = "LHS" if side == "left" else "RHS"
    head = (f'<div class="half-head"><span class="half-side">{label}</span>'
            f'<span class="half-layer">{esc(layer_short)}</span></div>')
    cluster = f'<div class="cluster {side}">{g_main}{g_inner}{g_thumb}</div>'
    # the stage reserves the (optionally scaled) footprint so the card hugs it
    stage = f'<div class="stage">{cluster}</div>'
    return f'<div class="half {side}">{head}{stage}</div>'


def render_board(binds, layer_short, highlight=None):
    left = render_half(binds, "left", layer_short, highlight)
    right = render_half(binds, "right", layer_short, highlight)
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


def _keys_html(c):
    """The keycaps of a chord, joined with + separators."""
    keys = c["text"].partition("➔")[0]
    return '<span class="plus">+</span>'.join(
        kc(k) for k in keys.strip().split("+"))


def _combo_line(c):
    """One chord on its own line: keys ➔ effect, timeout right-aligned."""
    effect = c["text"].partition("➔")[2].strip()
    # the effect fills the flexible column; a keycap stays natural-width at the
    # left of it, while plain text wraps within it (never stretching or clipping)
    inner = kc(effect) if effect and " " not in effect else esc(effect)
    tcls = "" if effect and " " not in effect else " is-text"
    fx = f'<span class="combo-fx{tcls}">{inner}</span>'
    return (f'<div class="combo"><span class="chip-keys">{_keys_html(c)}</span>'
            f'<span class="chip-arrow">➔</span>{fx}'
            f'<span class="chip-ms">{c["timeout"]}ms</span></div>')


def _combo_card(head, combos, head_cls=""):
    """A framed card: an optional LHS/RHS landmark over one or more chord lines."""
    h = (f'<div class="combo-card-head {head_cls}">{esc(head)}</div>'
         if head else "")
    lines = "".join(_combo_line(c) for c in combos)
    return f'<div class="combo-card">{h}<div class="combo-lines">{lines}</div></div>'


def render_combos(data):
    out = ['<section class="combos" id="combos"><div class="sec-head">'
           '<span class="eyebrow">chords</span><h2>Combos</h2></div>'
           '<p class="lead">Press these keys together to fire a single action. '
           'Same-hand chords use a 50&#8202;ms window; cross-hand chords 65&#8202;ms.</p>']

    # Single-hand, unpaired — LHS and RHS are an ordered pair of cards that sit
    # side by side when there's room; each lists its chords inner→outer.
    if data["lhs"] or data["rhs"]:
        out.append('<div class="combo-block">'
                   '<h3 class="combo-group">Single-hand · unpaired</h3>'
                   '<div class="pair-grid">')
        out.append(_combo_card("LHS", data["lhs"], "h-lhs"))
        out.append(_combo_card("RHS", data["rhs"], "h-rhs"))
        out.append('</div></div>')

    # Isomorphisms — mirror-image pairs. Each pair is a two-card grid (its own
    # LHS + RHS side); the collection of pairs is itself a 1–2-wide grid.
    if data["isos"]:
        out.append('<div class="combo-block">'
                   '<h3 class="combo-group">Isomorphisms · mirrored pairs</h3>'
                   '<div class="iso-grid">')
        for left, right in data["isos"]:
            out.append('<div class="iso-pair"><div class="iso-sides">')
            out.append(_combo_card("LHS", [left], "h-lhs"))
            out.append(_combo_card("RHS", [right], "h-rhs"))
            out.append('</div></div>')
        out.append('</div></div>')

    # Two-handed — each cross-hand chord is its own unit in a 1–2-wide grid.
    if data["twohand"]:
        out.append('<div class="combo-block">'
                   '<h3 class="combo-group">Two-handed</h3>'
                   '<div class="unit-grid">')
        for c in data["twohand"]:
            out.append(_combo_card("", [c]))
        out.append('</div></div>')

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
    MACROS.clear()
    MACROS.update(parse_macros(keymap_text))
    layers = parse_layers(keymap_text)
    combos = parse_combos(keymap_text)
    nav = "".join(
        f'<a href="#layer-{l["idx"]}" data-target="layer-{l["idx"]}">'
        f'{LAYER_SHORT[l["idx"]]}<span>{l["idx"]}</span></a>' for l in layers)
    layers_html = "".join(render_layer(l) for l in layers)
    ncombos = (len(combos["lhs"]) + len(combos["rhs"])
               + 2 * len(combos["isos"]) + len(combos["twohand"]))
    src = esc(meta["source"])
    commit = esc(meta["commit"])
    repo = esc(meta["repo_url"])
    commit_link = (f'<a href="{repo}/commit/{commit}">{commit[:7]}</a>'
                   if repo and commit and commit != "working copy" else commit)
    repo_link = (f'<a class="m repo" href="{repo}" target="_blank" '
                 f'rel="noopener">GitHub&nbsp;↗</a>' if repo else "")
    panel = meta.get("panel", True)
    css = asset("tour.css") + (asset("knobs.css") if panel else "")
    js = asset("tour.js") + (asset("knobs.js") if panel else "")
    page = asset("page.html").format(
        css=css, js=js, knobs=asset("knobs.html") if panel else "",
        nav=nav, layers=layers_html, combos=render_combos(combos),
        legend=render_legend(), nlayers=len(layers), ncombos=ncombos,
        src=src, commit=commit_link, date=esc(meta["date"]), repo_link=repo_link)
    # fragment mode: body content only, for a host that supplies its own document
    # skeleton (e.g. the Artifact wrapper). Full mode is a standalone document.
    if meta.get("fragment"):
        return page
    return PAGE_HEAD + page + PAGE_TAIL


PAGE_HEAD = ('<!doctype html><html lang="en"><head>'
             '<meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             '<title>ErgoDox Keymap — Visual Tour</title></head><body>')
PAGE_TAIL = "</body></html>"

DIFF_HEAD = ('<!doctype html><html lang="en" data-theme="light"><head>'
             '<meta charset="utf-8"><title>Keymap diff</title>'
             '<style>{css}</style></head><body>')


def build_diff(before_text, after_text):
    """Compare two keymap revisions and return {SHORT: standalone HTML} for each
    layer whose bindings changed. Each page shows the before board (changed keys
    ringed red) above the after board (ringed green)."""
    MACROS.clear()
    MACROS.update(parse_macros(after_text))
    before = {l["short"]: l for l in parse_layers(before_text)}
    after = {l["short"]: l for l in parse_layers(after_text)}
    css = asset("tour.css") + asset("diff.css")
    pages = {}
    for short, la in after.items():
        lb = before.get(short)
        if lb is None:
            continue
        changed = {p for p in la["binds"] if lb["binds"].get(p) != la["binds"].get(p)}
        if not changed:
            continue
        poslist = ", ".join(str(p) for p in sorted(changed))
        body = (
            f'<section class="before"><div class="diff-title">● Before</div>'
            f'<div class="diff-sub">{esc(short)} layer</div>'
            f'{render_board(lb["binds"], short, changed)}</section>'
            f'<section class="after"><div class="diff-title">● After</div>'
            f'<div class="diff-sub">{esc(short)} layer · positions {poslist}</div>'
            f'{render_board(la["binds"], short, changed)}</section>')
        pages[short] = DIFF_HEAD.format(css=css) + body + PAGE_TAIL
    return pages



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
    ap.add_argument("--diff-base", metavar="KEYMAP",
                    help="render a before/after diff against this earlier keymap")
    ap.add_argument("--diff-dir", default=".",
                    help="output dir for --diff-base pages (default: cwd)")
    a = ap.parse_args()
    text = open(a.keymap, encoding="utf-8").read()

    if a.diff_base:
        before = open(a.diff_base, encoding="utf-8").read()
        pages = build_diff(before, text)
        for short, page in pages.items():
            path = os.path.join(a.diff_dir, f"diff-{short}.html")
            open(path, "w", encoding="utf-8").write(page)
            print(f"wrote {path} ({len(page)} bytes)", file=sys.stderr)
        # stdout lists the changed layers, one per line, for the caller
        sys.stdout.write("".join(f"{s}\n" for s in pages))
        return

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
