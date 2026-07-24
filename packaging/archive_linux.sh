#!/usr/bin/env bash

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="${NIGHTSCOPE_BUILD_PYTHON:-$root/.venv/bin/python}"
bundle_dir="$root/dist/NightScope"
version_file="$root/VERSION"
bundle_audit="$root/tools/audit_qt_bundle.py"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This archive script requires Linux." >&2
    exit 1
fi

if [[ ! -x "$python" ]]; then
    echo "Build Python not found or not executable at $python" >&2
    exit 1
fi

if [[ ! -x "$bundle_dir/NightScope" ]]; then
    echo "Linux bundle not found at $bundle_dir; run packaging/build_linux.sh first." >&2
    exit 1
fi

version="$(<"$version_file")"
distribution_id="$(
    . /etc/os-release
    printf '%s' "${ID:-linux}"
)"
distribution_version="$(
    . /etc/os-release
    printf '%s' "${VERSION_ID:-unknown}"
)"
machine_architecture="$(uname -m)"
case "$machine_architecture" in
    x86_64)
        asset_architecture="x64"
        ;;
    aarch64)
        asset_architecture="arm64"
        ;;
    *)
        asset_architecture="$machine_architecture"
        ;;
esac

artifact_name="NightScope-v${version}-${distribution_id}-${distribution_version}-${asset_architecture}"
archive_name="${artifact_name}.tar.gz"
checksum_name="${archive_name}.sha256"
archive_path="$root/dist/$archive_name"
checksum_path="$root/dist/$checksum_name"
archive_temp="$(mktemp -p "$root/dist" ".${archive_name}.XXXXXX")"
trap 'rm -f -- "$archive_temp"' EXIT

"$python" "$bundle_audit" "$bundle_dir" --platform linux
tar \
    --sort=name \
    --mtime="@0" \
    --owner=0 \
    --group=0 \
    --numeric-owner \
    -cf - \
    -C "$root/dist" \
    NightScope \
    | gzip -n -9 > "$archive_temp"
mv -f -- "$archive_temp" "$archive_path"
trap - EXIT
chmod 0644 "$archive_path"

archive_digest="$(sha256sum "$archive_path")"
printf '%s  %s\n' "${archive_digest%% *}" "$archive_name" > "$checksum_path"
chmod 0644 "$checksum_path"

echo "Wrote $archive_path"
echo "Wrote $checksum_path"
