---
name: keybinding-workflow
description: Analyzes and implements keybindings copied from the ErgoDox keymap tour. Use automatically when a prompt contains "Key sequence:", "Layers:", and "Resolved tour result:", or when discussing conflicts between the ZMK keymap and application shortcuts.
---

# Keybinding workflow

Use this skill when a pasted tour prompt includes **Key sequence:**, **Layers:**, and **Resolved tour result:**, or when the user asks about a tour-derived keybinding conflict with app shortcuts.

## Entry points

- Live tour: [https://blehrer.github.io/ergodox-zmk-config/](https://blehrer.github.io/ergodox-zmk-config/)
- Regenerate locally:

```sh
python3 tools/render_keymap.py config/slicemk_ergodox.keymap --out tour.html
```

## Parse the prompt

1. If **Layers:** is missing, stop and ask the user to paste a fresh tour prompt (all three blocks: Key sequence, Layers, Resolved tour result).
2. Read **Key sequence:** and **Resolved tour result:** for the ZMK binding and layer path.
3. Open `config/slicemk_ergodox.keymap`. For each layer in **Layers:**, read the named layer comment block (`/* BASE (0) — … */`, etc.).
4. From each layer comment, collect **App bindings:** lines to learn which apps are in scope. If scope is unclear or spans apps ambiguously, ask before changing anything.

## Locate managed app config

For each scoped app, resolve chezmoi-managed sources:

```sh
chezmoi source-path <active-config>
```

Inspect explicit keybindings there and the app’s installed defaults (docs, `defaults read`, or app settings UI). For every app in scope, report what the pasted **Key sequence:** does today (ZMK output plus in-app effect). Ask what behavior the user wants. Flag conflicts (same chord, different meaning; or ZMK chord shadowing an app shortcut).

## Implement

- **Conflict-free and unambiguous:** implement immediately in the keymap and/or dotfiles.
- **Choice required:** describe options and wait for the user’s decision.

### ZMK keymap

Edit bindings in `config/slicemk_ergodox.keymap` when the fix belongs on the keyboard.

### Dotfiles marker

In the chezmoi dotfiles repo, add or reuse **one** adjacent, unique lowercase marker on the binding you touch:

```text
keymap-ref: <lowercase-slug>
```

Search existing markers before inventing a new slug.

### Layer notes

In the same layer comment block, add or update **App bindings:** with the resolved chord, app, behavior, and an HTTPS code-search link:

```text
https://github.com/blehrer/dotfiles/search?q=<urlencoded-marker>&type=code
```

URL-encode the marker (e.g. `keymap-ref%3A+<slug>`). Use only `https://` links in notes and reports—never `http://` or repo-local file paths as workflow steps.

## Verify

1. Apply managed configs (`chezmoi apply` or the app’s documented reload) for every app you changed.
2. Run each affected app’s native validator if one exists (e.g. config lint, `defaults read` sanity check).
3. In this repository:

```sh
python3 -m unittest tests/test_render_keymap.py
```

4. Build a temporary tour without the panel:

```sh
python3 tools/render_keymap.py config/slicemk_ergodox.keymap --out /tmp/tour.html --no-panel
```

Confirm the binding and **App bindings:** notes render as expected.

## Constraints

- Do not add cross-repository workflow dependencies in this repo (no “clone dotfiles here” automation); chezmoi and dotfiles edits stay in their own trees.
- Never `git push` or open PRs unless the user explicitly asks in that turn.
