#!/usr/bin/env python

LEAVES = (
    (0x00, 0x00),           # highest basic function parameter
    (0x01, 0x00),           # processor information & features
    (0x02, 0x00),           # cache & TLB descriptor information
    #(0x03, 0x00),          # processor serial number; unused since Pentium 3
    (0x04, 0x00),           # cache hierarchy & topology (Intel)
    (0x05, 0x00),           # MONITOR & MWAIT features
    (0x06, 0x00),           # thermal & power management
    (0x07, 0x00),           # extended features
    (0x07, 0x01),           # extended features
    (0x07, 0x02),           # extended features
    (0x0d, 0x00),           # XSAVE features
    (0x12, 0x00),           # Intel SGX features
    (0x14, 0x00),           # Intel processor trace features
    (0x15, 0x00),           # TSC & core crystal frequencies
    (0x16, 0x00),           # CPU & bus frequencies
    (0x1d, 0x00),           # AMX tile information
    (0x1e, 0x00),           # AMX TMUL (tile multiply) information
    (0x1e, 0x01),           # AMX TMUL (tile multiply) information
    (0x21, 0x00),           # Intel TDX enumeration
    (0x24, 0x00),           # AVX10 ISA information
    (0x24, 0x01),           # AVX10 features
    #(0x20000000, 0x00),    # highest Xeon Phi function parameter
    #(0x20000001, 0x00),    # Xeon Phi features
    (0x40000000, 0x00),     # hypervisor identification information
    (0x40000001, 0x00),     # hypervisor interface information
    (0x80000000, 0x00),     # highest extended function parameter
    (0x80000001, 0x00),     # extended processor information & features
    (0x80000002, 0x00),     # processor brand string
    (0x80000003, 0x00),     # processor brand string
    (0x80000004, 0x00),     # processor brand string
    (0x80000005, 0x00),     # L1 cache & TLB information
    (0x80000006, 0x00),     # extended L2 cache features
    (0x80000007, 0x00),     # power management & RAS capabilities
    (0x80000008, 0x00),     # virtual & physical address sizes
    (0x8000000a, 0x00),     # AMD SVM features
    (0x8000001d, 0x00),     # cache hierarchy & topology (AMD)
    (0x8000001f, 0x00),     # encrypted memory capabilities
    (0x80000021, 0x00),     # extended feature identification
)

if __name__ == "__main__":
    from archspec.cpu.detect import CpuidInfoCollector
    cpu = CpuidInfoCollector()
    for leaf, subleaf in LEAVES:
        registers = cpu.cpuid.registers_for(leaf, subleaf)
        print(f"{leaf:08x}.{subleaf:08x}", "=>",
              f"{registers.eax:08x}",
              f"{registers.ebx:08x}",
              f"{registers.ecx:08x}",
              f"{registers.edx:08x}",
              )
