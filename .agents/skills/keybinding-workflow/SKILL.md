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

1. Read **Key sequence:**, **Layers:**, and **Resolved tour result:** for the ZMK binding and layer path.
2. Open `config/slicemk_ergodox.keymap`. For each layer in **Layers:**, read the named layer comment block (`/* BASE (0) — … */`, etc.).
3. From each layer comment, collect **App bindings:** lines to learn which apps are in scope.

## Stop and ask

Do not edit files until the user answers when any of these apply:

- **Layers:** is missing or `(none)` — the prompt does not identify a layer.
- App scope cannot be inferred from **App bindings:** and the sequence (unclear or ambiguous across apps).
- A default binding cannot be determined for an app that still relies on defaults.
- A marker ID already identifies unrelated logic in dotfiles.
- Conflict resolution requires choosing which existing behavior to replace.

Report validation failures and leave unrelated files unchanged.

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

In the same layer comment block, add or update **App bindings:** with the resolved chord, app, behavior, and an HTTPS code-search link. Quote the entire search phrase so GitHub does not treat `keymap-ref:` as a search qualifier:

```text
https://github.com/blehrer/dotfiles/search?q=%22keymap-ref%3A+<slug>%22&type=code
```

Example:

```text
https://github.com/blehrer/dotfiles/search?q=%22keymap-ref%3A+zellij-mode-cycle%22&type=code
```

Use only `https://` links in notes and reports—never `http://` or repo-local file paths as workflow steps.

## Verify

1. Apply only the managed paths you changed: `chezmoi apply <target>` (for example the Zellij or Ghostty config path).
2. Run each affected app’s native validator if one exists (e.g. `zellij setup --check`, Ghostty `+validate-config`).
3. In this repository:

```sh
python3 -m unittest discover -s tests
```

4. Build a temporary tour without the panel:

```sh
python3 tools/render_keymap.py config/slicemk_ergodox.keymap --out /tmp/tour.html --no-panel
```

Confirm the binding and **App bindings:** notes render as expected.

## Constraints

- Do not add cross-repository workflow dependencies in this repo (no “clone dotfiles here” automation); chezmoi and dotfiles edits stay in their own trees.
- Never `git push` or open PRs unless the user explicitly asks in that turn.
