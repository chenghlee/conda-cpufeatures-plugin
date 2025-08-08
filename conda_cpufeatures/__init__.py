"""conda plugin for detecting CPU features like ISA vector extensions and
listing them as virtual packages.

Copyright (C) 2024 Anaconda, Inc.
"""

import platform

from conda.base.context import context
from conda.plugins import CondaVirtualPackage, hookimpl


@hookimpl
def conda_virtual_packages():
    if platform.machine() == "x86_64":
        from archspec.cpu.detect import CpuidInfoCollector
        cpu = CpuidInfoCollector()
    else:
        import archspec.cpu
        cpu = archspec.cpu.host()

    for feature in cpu.features:
        yield CondaVirtualPackage(f"cpu_{feature}", "1", "0")
