#!/usr/bin/env bash

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="${NIGHTSCOPE_BUILD_PYTHON:-$root/.venv/bin/python}"
spec="$root/packaging/NightScope.spec"
dist_dir="$root/dist/NightScope"
license_check="$root/tools/generate_third_party_licenses.py"
native_notice_generator="$root/tools/generate_linux_native_notices.py"
qt_bundle_audit="$root/tools/audit_qt_bundle.py"
collect_toc="$root/build/NightScope/COLLECT-00.toc"
legal_files=("LICENSE" "SOURCE_CODE.md" "THIRD_PARTY_NOTICES.md")
license_archive=""

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This build script requires Linux." >&2
    exit 1
fi

if [[ ! -x "$python" ]]; then
    echo "Build Python not found or not executable at $python" >&2
    exit 1
fi

mkdir -p "$root/build"
license_archive="$(mktemp -p "$root/build" ".linux-licenses.XXXXXX")"
trap 'rm -f -- "$license_archive"' EXIT

cd "$root"
"$python" "$license_check" \
    --output "$license_archive" \
    --platform-label Linux
"$python" -m PyInstaller --clean --noconfirm "$spec"

for filename in "${legal_files[@]}"; do
    install -m 0644 "$root/$filename" "$dist_dir/$filename"
done

install -m 0644 "$license_archive" "$dist_dir/THIRD_PARTY_LICENSES.txt"
"$python" "$native_notice_generator" \
    "$dist_dir" \
    --collect-toc "$collect_toc"
"$python" "$qt_bundle_audit" "$dist_dir" --platform linux
