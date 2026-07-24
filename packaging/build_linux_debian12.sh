#!/usr/bin/env bash

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dockerfile="$root/packaging/Dockerfile.debian12"
image_tag="${NIGHTSCOPE_DEBIAN12_IMAGE:-nightscope-debian12-builder:local}"
container_runtime="${NIGHTSCOPE_CONTAINER_RUNTIME:-}"

if [[ -z "$container_runtime" ]]; then
    if command -v podman >/dev/null 2>&1; then
        container_runtime="$(command -v podman)"
    elif command -v docker >/dev/null 2>&1; then
        container_runtime="$(command -v docker)"
    else
        echo "Docker or Podman is required for the Debian 12 release build." >&2
        exit 1
    fi
fi

if [[ ! -x "$container_runtime" ]]; then
    echo "Container runtime not found or not executable: $container_runtime" >&2
    exit 1
fi

"$container_runtime" build \
    --file "$dockerfile" \
    --tag "$image_tag" \
    "$root"

run_options=(
    run
    --rm
    --user "$(id -u):$(id -g)"
    --env HOME=/tmp/nightscope-builder
    --env NIGHTSCOPE_BUILD_PYTHON=/usr/local/bin/python
    --volume "$root:/workspace"
    --workdir /workspace
)

if [[ "$(basename "$container_runtime")" == "podman" ]]; then
    run_options+=(--userns=keep-id)
fi

"$container_runtime" "${run_options[@]}" "$image_tag" \
    bash -lc \
    'mkdir -p "$HOME" && ./packaging/build_linux.sh && ./packaging/archive_linux.sh'
