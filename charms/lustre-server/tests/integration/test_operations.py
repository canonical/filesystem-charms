#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
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

"""Custom Gherkin step definitions for lustre-server integration tests."""

import json
import logging
import subprocess

from pytest_bdd import given, parsers, scenarios, then
from pytest_jubilant_bdd import Context, flexible
from pytest_jubilant_bdd.errors import (
    AppNotFoundError,
    TooManyDeployedAppsError,
    UnitNotFoundError,
)

logger = logging.getLogger(__name__)

scenarios("features/lustre_server_operations.feature")


@given(parsers.parse("I disable secureboot on the LXD profile for model '{model}'"))
def disable_secureboot(context: Context, model: str) -> None:
    """Disable secure boot on the LXD profile Juju created for the given model.

    Args:
        context: Shared test context owning model lifecycle.
        model: Name of the model whose LXD profile will be patched.
    """
    # Lustre DKMS modules are unsigned and cannot be loaded while secure boot
    # is enabled, so patch the profile before any machines are deployed.
    juju = context.get_juju(model)
    model_name = juju.model.split(":")[-1]
    lxd_profile = f"juju-{model_name}"

    result = subprocess.run(
        ["lxc", "profile", "list", "--all-projects", "--format", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"lxc profile list failed (rc={result.returncode}): {result.stderr}")

    profiles = json.loads(result.stdout)
    target = next(
        (
            (profile.get("project"), profile.get("name"))
            for profile in profiles
            if profile.get("name", "").startswith(lxd_profile)
        ),
        None,
    )
    if target is None:
        profile_names = ", ".join(f"{p.get('name')} ({p.get('project')})" for p in profiles)
        raise RuntimeError(
            f"No LXD profile matching prefix '{lxd_profile}' found. "
            f"Available profiles: {profile_names}"
        )

    cmd = ["lxc", "profile", "--project", target[0], "set", target[1]]
    try:
        subprocess.run(
            cmd + ["boot.mode=uefi-nosecureboot"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        logger.warning(
            "Failed to set boot.mode=uefi-nosecureboot for LXD profile '%s'. "
            "Falling back to security.secureboot=false",
            target[1],
        )
        subprocess.run(
            cmd + ["security.secureboot=false"],
            check=True,
            capture_output=True,
            text=True,
        )


@given(parsers.parse("I wait for unit '{unit}' to exist"))
def wait_for_unit(context: Context, unit: str) -> None:
    """Wait for a unit to appear in the model.

    Args:
        context: Shared test context owning model lifecycle.
        unit: Name of the unit to wait for (e.g. "filesystem-client/0").
    """
    context.wait(
        ready=lambda ctx: _unit_exists(ctx, unit),
    )


def _unit_exists(ctx: Context, unit: str) -> bool:
    """Check whether a unit is present in the current testing context.

    Args:
        ctx: Shared test context to query for the unit.
        unit: Name of the unit to check for.

    Returns:
        True if the unit exists, False if it is absent or its app is not found.
    """
    try:
        ctx.get_unit(unit)
    except UnitNotFoundError, AppNotFoundError, TooManyDeployedAppsError:
        return False
    return True


@then(flexible("the ssh output contains '{text}' [and '{other}']"))
def assert_ssh_output_contains(context: Context, text: str, other: str | None) -> None:
    """Assert the next `juju ssh` output contains the text(s) (LIFO order).

    Args:
        context: Shared test context owning the ssh result stack.
        text: Text expected in the ssh output.
        other: Optional second text expected in the same output.
    """
    output = context.ssh_results.pop()
    assert text in output, f"'{text}' not found in ssh output:\n{output}"
    if other is not None:
        assert other in output, f"'{other}' not found in ssh output:\n{output}"


@then(parsers.parse("the ssh output is '{text}'"))
def assert_ssh_output_is(context: Context, text: str) -> None:
    """Assert the next `juju ssh` output is exactly the text (LIFO order).

    Args:
        context: Shared test context owning the ssh result stack.
        text: Exact text expected from the ssh output.
    """
    output = context.ssh_results.pop()
    # Strip whitespace to handle commands such as `lfs getstripe --stripe-count`
    # giving output with trailing newlines
    assert output.strip() == text, f"ssh output is not exactly '{text}':\n{output}"


@then(parsers.parse("the ssh output capacity is between '{minimum}' KB and '{maximum}' KB"))
def assert_ssh_output_capacity_between(context: Context, minimum: str, maximum: str) -> None:
    """Assert the next `juju ssh` output is `df` with total KB in the given range.

    Args:
        context: Shared test context owning the ssh result stack.
        minimum: Lower bound of the mount capacity, in KB.
        maximum: Upper bound of the mount capacity, in KB.
    """
    output = context.ssh_results.pop()
    lines = output.strip().splitlines()
    if len(lines) < 2:
        raise AssertionError(f"unexpected df output:\n{output}")
    total_kb = int(lines[1].split()[1])
    assert int(minimum) <= total_kb <= int(maximum), (
        f"mount capacity is {total_kb} KB, expected between "
        f"{minimum} KB and {maximum} KB:\n{output}"
    )
