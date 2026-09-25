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

"""Integration test fixtures for the lustre-server charm.

The ``pytest-jubilant-bdd`` plugin provides the session-scoped ``context``
fixture, which owns model lifecycle. Do not define a ``juju`` fixture here.
"""


def pytest_addoption(parser) -> None:
    """Add lustre-server-specific CLI options."""
    parser.addoption(
        "--charm-base",
        action="store",
        default="ubuntu@26.04",
        help="Charm base version to use for integration tests",
    )
