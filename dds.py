import numpy as np
import amaranth as nm
from amaranth.hdl.rec import Record

from amaranth.hdl.ast import *
from amaranth.back import verilog
from amaranth.sim import Simulator

from amaranth.sim import *

import numpy as np

# this is leider needed because the simulator cant recurse so deep and its a known issue with pysim afaik
import sys
sys.setrecursionlimit(100000)

class DDS(nm.Elaboratable):

    def create_sine_lut(self, lut_bits, lut_size):
        # Generate a sine wave LUT
        lut_gen = [int((np.sin(2 * np.pi * i / lut_size) + 1) * (2**(lut_bits - 1) - 1)) for i in range(lut_size)]
        return nm.Memory(width=lut_bits, depth=lut_size, init=lut_gen)

    def __init__(self, phase_bits=32, lut_bits=10, freq_bits=32):
        # Phase accumulator
        self.phase_accumulator = nm.Signal(phase_bits)
        
        # Frequency control (phase increment)
        self.freq_control = nm.Signal(freq_bits)

        # Output of the DDS
        self.dds_output = nm.Signal(lut_bits)

        # Internal LUT for the sine wave
        self.lut = self.create_sine_lut(lut_bits, 2**lut_bits)

    def elaborate(self, platform):
        m = nm.Module()

        read_port = self.lut.read_port()
        m.submodules += read_port

        # Increment the phase accumulator
        m.d.sync += self.phase_accumulator.eq(self.phase_accumulator + self.freq_control)

        # Map the most significant bits of the phase accumulator to the LUT address
        m.d.comb += [
            read_port.addr.eq(self.phase_accumulator[-len(read_port.addr):]),
            self.dds_output.eq(read_port.data)
        ]

        return m
 

# pytest dds.py
def test():
    dut = DDS(phase_bits=27, lut_bits=14, freq_bits=27)
    def bench():
        # yield dut.freq_control.eq(10)
        for i in range(1,10):
            yield dut.freq_control.eq(i*1)
            for ph in range(16384):
            # for ph in range(1024):
                yield dut.dds_output
                yield
            # yield dut.freq_control.eq(10*i)
            # yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("dds.vcd", "dds.gtkw", traces=[dut.phase_accumulator, dut.freq_control, dut.dds_output]):
        sim.run()

if __name__ == "__main__":
    dut = DDS(phase_bits=14, lut_bits=14, freq_bits=14)
    # dut = DDS(16,16)
    v = verilog.convert(
        dut, name="dds", ports=[dut.phase_accumulator, dut.freq_control, dut.dds_output],
        emit_src=False, strip_internal_attrs=True)
    print(v)