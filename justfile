# Copyright 2024-2025 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

uv := require("uv")

export PY_COLORS := "1"
export PYTHONBREAKPOINT := "pdb.set_trace"

uv_run := "uv run --frozen --extra dev"

[private]
default:
    @just help

# Regenerate uv.lock
lock:
    uv lock

# Create a development environment
env: lock
    uv sync --extra dev

# Upgrade uv.lock with the latest dependencies
upgrade:
    uv lock --upgrade

# Run action on monorepo. For a full list of actions, run `just repo`
repo *args: lock
    {{uv_run}} repository.py {{args}}

# Run the lustre-server BDD integration tests (requires a Juju controller and LXD)
lustre-integration *args: lock
    #!/usr/bin/env bash
    set -euo pipefail

    # Drop the optional `--` separator that `just` forwards from the CLI.
    PASSTHROUGH=()
    for arg in {{args}}; do
        [[ "$arg" == "--" ]] || PASSTHROUGH+=("$arg")
    done

    # Build the charm and export its path. The BDD `pack` step skips
    # `charmcraft pack` when `LUSTRE_SERVER_CHARM_PATH` is set, and the
    # `deploy_local` step deploys from it.
    {{uv_run}} repository.py build lustre-server
    ln -sfn "$(pwd)/_build/lustre-server.charm" lustre-server.charm
    export LUSTRE_SERVER_CHARM_PATH=1

    {{uv_run}} pytest -v --exitfirst -s --tb native --log-cli-level=INFO \
        --juju-bdd-wait-timeout 1800 \
        ./charms/lustre-server/tests/integration "${PASSTHROUGH[@]}"

# Show available recipes
help:
    @just --list --unsorted
