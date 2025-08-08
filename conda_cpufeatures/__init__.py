"""conda plugin for detecting CPU features like ISA vector extensions and
listing them as virtual packages.

Copyright (C) 2024 Anaconda, Inc.
"""

import platform
import struct

from conda.base.context import context
from conda.plugins import CondaVirtualPackage, hookimpl


@hookimpl
def conda_virtual_packages():
    if platform.machine() == "x86_64":
        from archspec.cpu.detect import CpuidInfoCollector
        cpu = CpuidInfoCollector()

        registers = cpu.cpuid.registers_for(0x80000000)
        if registers.eax >= 0x80000004:
            cpu_model_name = "".join((struct.pack("IIII", *cpu.cpuid(i)).decode("utf-8")
                                      for i in range(0x80000002, 0x80000005)))
            if (cpu.vendor == "GenuineIntel" and cpu_model_name.startswith("VirtualApple")):
                # Version 2 since Rosetta 1 was the PPC -> x86 transition
                yield CondaVirtualPackage(f"rosetta", "2", "0")
    else:
        import archspec.cpu
        cpu = archspec.cpu.host()

    for feature in cpu.features:
        yield CondaVirtualPackage(f"cpu_{feature}", "1", "0")
