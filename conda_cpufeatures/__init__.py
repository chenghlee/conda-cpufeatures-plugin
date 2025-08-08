"""conda plugin for detecting CPU features like ISA vector extensions and
listing them as virtual packages.

Copyright (C) 2024 Anaconda, Inc.
"""

from conda.base.context import context
from conda.plugins import CondaVirtualPackage, hookimpl


@hookimpl
def conda_virtual_packages():
    import archspec.cpu
    for feature in archspec.cpu.host().features:
        yield CondaVirtualPackage(f"cpu_{feature}", "1", "0")
