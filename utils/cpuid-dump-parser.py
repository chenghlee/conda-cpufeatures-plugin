#!/usr/bin/env python

import json
import struct
import sys

from collections import defaultdict
from enum import Enum
from functools import cache, cached_property
from itertools import chain


class Registers(Enum):
    EAX = 0
    EBX = 1
    ECX = 2
    EDX = 3


def node_name(eax, ecx=0):
    return f"{eax:08x}.{ecx:08x}"


class CPUID:
    def __init__(self):
        self._raw_data = {}

    def load(self, file_, register_masks=None):
        self._raw_data = {}
        register_masks = register_masks or {}
        self._raw_data = dict()
        with open(file_, "r") if isinstance(file_, str) else file_ as infile:
            for line in infile:
                node, registers = line.strip().split(" => ")
                self._raw_data[node] = {
                    r: int(v, 16)
                    for r, v in zip(Registers, registers.split())
                }

        for node, mask_set in register_masks.items():
            for register, mask in mask_set.items():
                self._raw_data[node][register] &= mask


    @cached_property
    def vendor(self) -> str:
        node = node_name(0x00)
        vendor_name = struct.pack("III",
                                  self._raw_data[node][Registers.EBX],
                                  self._raw_data[node][Registers.EDX],
                                  self._raw_data[node][Registers.ECX],
                                  ).decode('utf-8')
        return vendor_name

    @cached_property
    def model_name(self) -> str:
        if self._raw_data[node_name(0x80000000)][Registers.EAX] < 0x80000004:
            return ""

        def _name_part(leaf):
            node = node_name(leaf)
            return struct.pack("IIII",
                               self._raw_data[node][Registers.EAX],
                               self._raw_data[node][Registers.EBX],
                               self._raw_data[node][Registers.ECX],
                               self._raw_data[node][Registers.EDX],
                               ).decode('utf-8')

        model_name = "".join((_name_part(leaf)
                              for leaf in range(0x80000002, 0x80000005)))
        model_name = model_name.split('\x00', 1)[0].strip()
        return model_name

    @cached_property
    def family_id(self) -> int:
        register_value = self._raw_data[node_name(0x01)][Registers.EAX]
        family_id = (register_value >> 8) & 0xf
        if family_id == 15:
            family_id += (register_value >> 20) & 0xff
        return family_id

    @cached_property
    def model_id(self) -> int:
        register_value = self._raw_data[node_name(0x01)][Registers.EAX]
        model_id = (register_value >> 4) & 0xf
        family_id = (register_value >> 8) & 0xf
        if family_id == 6 or family_id == 15:
            extended_model_id = (register_value >> 16) & 0xf
            model_id |= (extended_model_id << 4)
        return model_id

    @cached_property
    def stepping_id(self) -> int:
        return self._raw_data[node_name(0x01)][Registers.EAX] & 0xf

    @cached_property
    def highest_base_function(self) -> int:
        return self._raw_data[node_name(0x00)][Registers.EAX]

    @cached_property
    def highest_extended_function(self) -> int:
        return self._raw_data[node_name(0x80000000)][Registers.EAX]

    @cached_property
    def hypervisor_name(self) -> str:
        register = self._raw_data[node_name(1)][Registers.ECX]
        if (register >> 31) & 1:
            leaf = self._raw_data[node_name(0x40000000)]
            name = struct.pack("III",
                               leaf[Registers.EBX],
                               leaf[Registers.ECX],
                               leaf[Registers.EDX],
                               ).decode('utf-8')
            name = name.split('\x00', 1)[0]
        else:
            name = "NONE"
        return name

    def register_value(self, leaf, register):
        return self._raw_data[node_name(leaf, subleaf)][register]

    def __getitem__(self, node):
        return self._raw_data[node]


def load_cpuid_flags():
    cpuid_flags = defaultdict(lambda: {r: {} for r in Registers})

    try:
        from archspec.cpu.schema import CPUID_JSON
    except ImportError:
        # TODO: consider adding an argument to load CPU flag information from
        # another source (e.g., a user-supplied file path)
        raise ValueError("could not load CPU flag information")

    data = CPUID_JSON.data
    for flag_set in chain(data.get("flags", []),
                          data.get("extension-flags",[]),
                          ):
        leaf, subleaf = flag_set["input"]["eax"], flag_set["input"]["ecx"]
        for bit in flag_set["bits"]:
            register = Registers[bit["register"].upper()]
            cpuid_flags[node_name(leaf, subleaf)][register][bit["bit"]] = bit["name"].upper()
    return cpuid_flags



if __name__ == "__main__":
    import re
    import sys
    from pprint import pprint

    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("dump_file", nargs="?", default=sys.stdin)
    args = parser.parse_args()

    register_masks = {
        node_name(0x01, 0x00): {
            # Mask out local APIC ID of the logical processor that ran the
            # CPUID instruction, as this tends to vary from run to run.
            Registers.EBX: 0x00111111,
        },
    }

    cpuid = CPUID()
    cpuid.load(args.dump_file, register_masks)

    cpuid_flags = load_cpuid_flags()


    OUTPUT_FMT = "{:40s}: {}"

    VALUE_FIELDS = (
        ("CPU vendor name", cpuid.vendor),
        ("CPU model name", cpuid.model_name),
        (
            "CPU family, model, stepping id",
            ", ".join((
                f"0x{v:02x}" for v in
                (cpuid.family_id, cpuid.model_id, cpuid.stepping_id)
            ))
        ),
        (
            "Highest base function",
            f"0x{cpuid.highest_base_function:08x}"
        ),
        (
            "Highest extended function",
            f"0x{cpuid.highest_extended_function:08x}"
        ),
        ("Hypervisor name", cpuid.hypervisor_name),
    )

    FEATURE_FLAG_REGISTERS = (
        (0x01, 0x00, Registers.EDX),
        (0x01, 0x00, Registers.ECX),
        (0x05, 0x00, Registers.ECX, (0, 1, 3,)),
        (0x07, 0x00, Registers.EBX),
        (0x07, 0x00, Registers.ECX),
        (0x07, 0x00, Registers.EDX),
        (0x80000001, 0x00, Registers.ECX),
        (0x80000001, 0x00, Registers.EDX),
    )

    CPUID_FLAGS_SUPPLEMENT = (
        (0x01, 0x00, Registers.ECX, 11, "SDBG"),

        (0x05, 0x00, Registers.ECX,  0, "EMX"),
        (0x05, 0x00, Registers.ECX,  1, "IBE"),
        (0x05, 0x00, Registers.ECX,  3, "MONITORLESS_MWAIT"),

        (0x07, 0x00, Registers.EBX,  1, "IA32_TSC_ADJUST"),
        (0x07, 0x00, Registers.EBX, 13, "DEPRECATE_FPU_CS_DS"),

        (0x07, 0x00, Registers.ECX, 15, "Intel TDX FZM"),
        (0x07, 0x00, Registers.ECX, 16, "LA57"),
        (0x07, 0x00, Registers.ECX, 23, "KL"),
        (0x07, 0x00, Registers.ECX, 24, "BUS_LOCK_DETECT"),
        (0x07, 0x00, Registers.ECX, 26, "Intel TDX MPRR"),

        (0x07, 0x00, Registers.EDX,  0, "Intel TDX SGX_TEM"),
        (0x07, 0x00, Registers.EDX,  1, "SGX_KEYS"),
        (0x07, 0x00, Registers.EDX,  2, "AVX512_4VNNIW"),
        (0x07, 0x00, Registers.EDX,  3, "AVX512_4FMAPS"),
        (0x07, 0x00, Registers.EDX,  5, "UINTR"),
        (0x07, 0x00, Registers.EDX,  9, "SRBDS_CTRL"),
        (0x07, 0x00, Registers.EDX, 11, "RTM_ALWAYS_ABORT"),
        (0x07, 0x00, Registers.EDX, 13, "RTM_FORCE_ABORT"),
        (0x07, 0x00, Registers.EDX, 15, "HYBRID"),
        (0x07, 0x00, Registers.EDX, 18, "PCONFIG"),
        (0x07, 0x00, Registers.EDX, 19, "LBR"),
        (0x07, 0x00, Registers.EDX, 20, "CET_IBT"),
        (0x07, 0x00, Registers.EDX, 26, "IBRS_IBPB"),
        (0x07, 0x00, Registers.EDX, 27, "STIBP"),
        (0x07, 0x00, Registers.EDX, 28, "FLUSH_L1D"),
        (0x07, 0x00, Registers.EDX, 29, "IA32_ARCH_CAPABILITIES"),
        (0x07, 0x00, Registers.EDX, 30, "IA32_CORE_CAPABILITIES"),

        (0x80000001, 0x00, Registers.ECX, 30, "ADDR_MASK_EXT"),
    )

    for leaf, subleaf, register, bit, name in CPUID_FLAGS_SUPPLEMENT:
        node = node_name(leaf, subleaf)
        if bit not in cpuid_flags[node][register]:
            cpuid_flags[node][register][bit] = re.sub(' ', '_', name.upper())

    FEATURE_FLAG_IGNORE_BITS = [
        (0x01, 0x00, Registers.ECX, 16),        # reserved (unknown/unused function)
        (0x01, 0x00, Registers.EDX, 10),        # reserved (unknown/unused function)
        (0x01, 0x00, Registers.EDX, 20),        # reserved (unknown/unused function)
        (0x01, 0x00, Registers.EDX, 30),        # Itanium (IA64) identification

        (0x07, 0x00, Registers.ECX, 15),        # Intel TDX FZM
        (0x07, 0x00, Registers.ECX, 26),        # Intel TDX MPRR

        (0x07, 0x00, Registers.EDX,  0),        # Intel TDX SGX-TEM
        (0x07, 0x00, Registers.EDX,  6),        # reserved (unknown/unused function)
        (0x07, 0x00, Registers.EDX,  7),        # reserved (unknown/unused function)
        (0x07, 0x00, Registers.EDX, 12),        # reserved (unknown/unused function)
        (0x07, 0x00, Registers.EDX, 17),        # reserved (unknown/unused function)
        (0x07, 0x00, Registers.EDX, 21),        # reserved (unknown/unused function)

        (0x80000001, 0x00, Registers.ECX, 14),  # reserved (unknown/unused function)
        (0x80000001, 0x00, Registers.ECX, 18),  # reserved (unknown/unused function)
        (0x80000001, 0x00, Registers.ECX, 20),  # reserved (unknown/unused function)
        (0x80000001, 0x00, Registers.ECX, 25),  # formerly, AMD StreamPerfMon
        (0x80000001, 0x00, Registers.ECX, 31),  # reserved (unknown/unused function)

        (0x80000001, 0x00, Registers.EDX, 18),  # reserved (unknown/unused function)
        (0x80000001, 0x00, Registers.EDX, 21),  # reserved (unknown/unused function)
        (0x80000001, 0x00, Registers.EDX, 28),  # reserved (unknown/unused function)
    ]

    FEATURE_FLAG_IGNORE_BITS += ((0x07, 0x00, Registers.ECX, bit_num)
                                 for bit_num in range(17, 22))


    for name, value in VALUE_FIELDS:
        print(OUTPUT_FMT.format(name, value))

    for leaf, subleaf, register, *bits in FEATURE_FLAG_REGISTERS:
        node = node_name(leaf, subleaf)
        bits = bits[0] if bits else range(0, 32)
        for bit_num in bits:
            if (leaf, subleaf, register, bit_num) in FEATURE_FLAG_IGNORE_BITS:
                continue
            flag_value = (cpuid[node][register] >> bit_num) & 1
            flag_name = (cpuid_flags[node].get(register, {}).get(bit_num, "")
                         or f"{node}.{register.name}.{bit_num}")
            print(OUTPUT_FMT.format(flag_name, "yes" if flag_value else "no"))
