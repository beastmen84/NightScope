#!/usr/bin/env bash

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="$root/.venv/bin/python"
spec="$root/packaging/NightScope.spec"
dist_dir="$root/dist/NightScope"
license_check="$root/tools/generate_third_party_licenses.py"
qt_bundle_audit="$root/tools/audit_qt_bundle.py"
legal_files=("LICENSE" "THIRD_PARTY_NOTICES.md")

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This build script requires Linux." >&2
    exit 1
fi

if [[ ! -x "$python" ]]; then
    echo "Python venv not found at $python" >&2
    exit 1
fi

cd "$root"
"$python" "$license_check" --check
"$python" -m PyInstaller --clean --noconfirm "$spec"

for filename in "${legal_files[@]}"; do
    install -m 0644 "$root/$filename" "$dist_dir/$filename"
done

"$python" "$license_check" \
    --output "$dist_dir/THIRD_PARTY_LICENSES.txt" \
    --platform-label Linux
"$python" "$qt_bundle_audit" "$dist_dir" --platform linux
