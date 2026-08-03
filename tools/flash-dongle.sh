#!/usr/bin/env bash
# Wait for the SliceMK dongle UF2 bootloader volume, then copy firmware onto it.
#
# macOS note: UF2 volumes reject extended attributes; we use cp -X when available.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${ROOT}/.firmware-cache"
DEFAULT_VOL="MDBT50QBOOT"
DEFAULT_UF2="slicemk_ergodox_dongle-raytac_mdbt50q_cx_blue-zmk.uf2"
TIMEOUT=300
POLL=2
UF2=""
VOLUME="$DEFAULT_VOL"
DOWNLOAD=0
WAIT=1

usage() {
    cat <<EOF
Usage: $(basename "$0") [options] [firmware.uf2]

Wait for the dongle bootloader volume and copy a .uf2 onto it. The dongle
reboots when the copy finishes.

Options:
  --latest          Download the rolling "latest" release from this repo's
                    GitHub origin (matches build.yaml for the CX Blue dongle).
  --uf2 PATH        Firmware file to flash (default: --latest, or ${DEFAULT_UF2}
                    in .firmware-cache/ if already downloaded).
  --volume NAME     Bootloader volume name (default: ${DEFAULT_VOL}).
  --timeout SEC     Stop waiting after SEC seconds (default: ${TIMEOUT}).
  --no-wait         Fail unless the volume is already mounted.
  -h, --help        Show this help.

Examples:
  $(basename "$0") --latest
  $(basename "$0") --latest --volume MDBT50QBOOT
  $(basename "$0") ~/Downloads/slicemk_ergodox_dongle-raytac_mdbt50q_cx_blue-zmk.uf2
EOF
}

repo_slug() {
    local url
    url="$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)"
    [[ -n "$url" ]] || return 1
    sed -E 's#.*github.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#' <<<"$url"
}

download_latest() {
    local slug dest
    slug="$(repo_slug)" || {
        echo "error: could not infer GitHub repo from git remote; pass --uf2 PATH" >&2
        exit 1
    }
    mkdir -p "$CACHE"
    dest="${CACHE}/${DEFAULT_UF2}"
    echo "Downloading latest from github.com/${slug} ..."
    curl -fsSL -o "$dest" \
        "https://github.com/${slug}/releases/download/latest/${DEFAULT_UF2}"
    UF2="$dest"
}

copy_uf2() {
    local vol="/Volumes/${VOLUME}"
    # ponytail: cp -X is macOS-only; plain cp elsewhere (Linux UF2 mounts vary).
    if cp -X "$UF2" "$vol/" 2>/dev/null; then
        :
    elif cp "$UF2" "$vol/"; then
        :
    else
        echo "error: copy to ${vol}/ failed" >&2
        exit 1
    fi
    sync 2>/dev/null || true
    echo "Flashed $(basename "$UF2") to ${vol}/ — dongle should reboot."
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --latest)   DOWNLOAD=1; shift ;;
        --uf2)      UF2="$2"; shift 2 ;;
        --volume)   VOLUME="$2"; shift 2 ;;
        --timeout)  TIMEOUT="$2"; shift 2 ;;
        --no-wait)  WAIT=0; shift ;;
        -h|--help)  usage; exit 0 ;;
        -*)         echo "error: unknown option $1" >&2; usage >&2; exit 1 ;;
        *)          UF2="$1"; shift ;;
    esac
done

if [[ "$DOWNLOAD" -eq 1 ]]; then
    download_latest
elif [[ -z "$UF2" ]]; then
    if [[ -f "${CACHE}/${DEFAULT_UF2}" ]]; then
        UF2="${CACHE}/${DEFAULT_UF2}"
    else
        echo "No firmware given; use --latest or --uf2 PATH" >&2
        usage >&2
        exit 1
    fi
fi

[[ -f "$UF2" ]] || { echo "error: not a file: $UF2" >&2; exit 1; }

vol="/Volumes/${VOLUME}"
if [[ -d "$vol" ]]; then
    copy_uf2
    exit 0
fi

if [[ "$WAIT" -eq 0 ]]; then
    echo "error: ${vol} is not mounted" >&2
    exit 1
fi

echo "Waiting for ${vol} (timeout ${TIMEOUT}s) — put the dongle in bootloader mode."
deadline=$((SECONDS + TIMEOUT))
while (( SECONDS < deadline )); do
    if [[ -d "$vol" ]]; then
        copy_uf2
        exit 0
    fi
    sleep "$POLL"
done

echo "error: ${vol} never appeared" >&2
exit 1
