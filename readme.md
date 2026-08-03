This repository contains the default ZMK user configuration for the
[ErgoDox Wireless](https://www.slicemk.com/pages/ergodox-wireless) keyboard.
While the
[SliceMK Keymap Configurator](https://config.slicemk.com/zmk/) is recommended
for the majority of users, the GitHub Actions workflow provides some additional
options for customization.

If you have questions, feel free to join the
[SliceMK Discord](https://discord.gg/FQvyd7BAaA).

# Keymap Layout Tour

A visual, always-up-to-date walkthrough of every layer and combo is published to
GitHub Pages at
**https://blehrer.github.io/ergodox-zmk-config/**. It is generated directly from
`config/slicemk_ergodox.keymap` by `tools/render_keymap.py`, and the
[Keymap Layout Tour workflow](.github/workflows/keymap-tour.yml) rebuilds and
redeploys it automatically on every push that touches the keymap, so it can
never drift out of date with the firmware.

To preview it locally:

```sh
python3 tools/render_keymap.py config/slicemk_ergodox.keymap --out tour.html
```

(The generator uses only the Python standard library. Add `--no-panel` to omit
the live geometry-adjustment panel, as the published build does.)

# Getting Started

- Fork this repository on GitHub.
- Modify the `board` and `shield` values in `build.yaml` to match the ZMK build
  target based on your hardware (see [Board/Shield](#boardshield)).

# Flashing the dongle

After a push to `main`, GitHub Actions builds central firmware and publishes it
to the rolling [**latest** release](https://github.com/blehrer/ergodox-zmk-config/releases/tag/latest).

`tools/flash-dongle.sh` waits for the dongle bootloader volume and copies the
`.uf2` onto it:

```sh
# Download the latest build, wait for MDBT50QBOOT, flash
./tools/flash-dongle.sh --latest

# Or flash a file you already have
./tools/flash-dongle.sh path/to/firmware.uf2
```

Put the **USB dongle** in bootloader mode first (double-tap its reset button
while plugged in). On macOS the volume mounts as **`MDBT50QBOOT`**. The script
uses `cp -X` so macOS extended-attribute errors do not block the copy.

Options: `--volume NAME`, `--timeout SEC`, `--no-wait` (fail if not mounted).
Downloaded firmware is cached under `.firmware-cache/` (gitignored).

**Optional:** install a `pre-push` hook that runs `./tools/flash-dongle.sh --latest`
after every push to `main` on a `github.com` remote (background — put the dongle
in bootloader mode when it prompts you). CI must finish before `--latest` picks
up the new build; re-run the script if you were too early.

```sh
./tools/install-githooks.sh
```

# Customization

- To modify your keymap, edit `config/slicemk_ergodox.keymap`.
- If you are using a dongle, add custom ZMK configuration options to
  `config/slicemk_ergodox_dongle.conf`. If you are not using a dongle, custom
  options should instead go in `config/slicemk_ergodox_leftcentral.conf`.
- To use with a custom ZMK fork, edit `config/west.yml`.

# Board/Shield

If you are not sure which dongle or PCB version you have, please put your
dongle/PCB into bootloader mode and check the "Model" value within the
`INFO_UF2.TXT` file.

GitHub Actions will only build the firmware for your central. Please download
the firmware for your peripheral(s)
[here](https://docs.slicemk.com/keyboard/ergodox/peripheral/).

Here are some of the common dongle options:

- **Raytac MDBT50Q-CX Blue**
	- Board `raytac_mdbt50q_cx_blue`
	- Shield `slicemk_ergodox_dongle`
- **Raytac MDBT50Q-RX Green**
	- Board `raytac_mdbt50q_rx_green`
	- Shield `slicemk_ergodox_dongle`
- **Raytac MDBT50Q-RX** (if model name does not include "Green")
	- Board `raytac_mdbt50q_rx`
	- Shield `slicemk_ergodox_dongle`
- **Nordic nRF52840 Dongle**
	- Board `nordic_nrf52840_dongle_slicemk`
	- Shield `slicemk_ergodox_dongle`
- **SliceMK USB C Dongle MDBT50Q Blue**
	- Board `slicemk_usbc_mdbt50q_blue`
	- Shield `slicemk_ergodox_dongle`

Here are some of the common dongleless options:

- **SliceMK ErgoDox Wireless 202104**
	- Board `slicemk_ergodox_202104`
	- Shield `slicemk_ergodox_leftcentral`
- **SliceMK ErgoDox Wireless 202108 Blue**
	- Board `slicemk_ergodox_202108_blue_left`
	- Shield `slicemk_ergodox_leftcentral`
- **SliceMK ErgoDox Wireless 202108 Green**
	- Board `slicemk_ergodox_202108_green_left`
	- Shield `slicemk_ergodox_leftcentral`
	- Shield `slicemk_ergodox_leftcentral`
- **SliceMK ErgoDox Wireless 202205 Green**
	- Board `slicemk_ergodox_202205_green_left`
	- Shield `slicemk_ergodox_leftcentral`
- **SliceMK ErgoDox Wireless 202207 Green**
	- Board `slicemk_ergodox_202207_green_left`
	- Shield `slicemk_ergodox_leftcentral`
