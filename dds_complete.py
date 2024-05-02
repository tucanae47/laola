import numpy as np
import amaranth as nm
from amaranth.hdl.rec import Record

from amaranth.hdl.ast import *
from amaranth.back import verilog
from amaranth.sim import Simulator
# from amaranth.lib.coding import PriorityEncoder

from amaranth.sim import *

from amaranth import *
import numpy as np

# this is leider needed because the simulator cant recurse so deep and its a known issue with pysim afaik
import sys
sys.setrecursionlimit(900000000)
class SUM(Elaboratable):

    def __init__(self):
        # Inputs
        self.in_1 = Signal(14)
        self.in_2 = Signal(14)
        self.out_1 = Signal(14)

    def elaborate(self, platform):
        m = Module()
        m.d.sync += self.out_1.eq(self.in_1[1:] + self.in_2[1:])
        return m

# taken from amaranth.lib.coding but with MSB instead
class PriorityEncoder(Elaboratable):
    def __init__(self, width):
        self.width = width

        self.i = Signal(width)
        self.o = Signal(range(width))
        self.n = Signal()

    def elaborate(self, platform):
        m = Module()
        for j in range(self.width):
            with m.If(self.i[j]):
                m.d.comb += self.o.eq(j)
        m.d.comb += self.n.eq(self.i == 0)
        return m

phase_bits = 27
lut_bits = 14
class DDS(Elaboratable):

    def create_sine_lut(self, lut_bits, lut_size):
        # Generate a sine wave LUT
        # lut_size_quarter = lut_size // 4
        # lut_gen = [int((np.sin(2 * np.pi * i / lut_size) + 1) * (2**(lut_bits - 1) - 1)) for i in range(lut_size)]
        # lut_gen = [int((np.sin(2 * np.pi * i / lut_size) + 1) * (2**(lut_bits - 1) - 1)) for i in range(lut_size)]
        lut_gen = [int((np.sin(2 * np.pi * i / lut_size) + 1) * (2**(8 - 1) - 1)) for i in range(lut_size)]

        # lut_gen =[int((np.sin(np.pi / 2 * i / lut_size) + 1) * (2**(lut_bits - 1) - 1)) for i in range(lut_size)]
        return Memory(width=lut_bits, depth=lut_size, init=lut_gen)

    def __init__(self, phase_bits=32, lut_bits=10, freq_bits=32):
        # Phase accumulator
        self.phase_accumulator = nm.Signal(phase_bits)
        
        # Frequency control (phase increment)
        self.freq = Signal(freq_bits)

        self.freq_last = Signal.like(self.freq)
        # Output of the DDS
        self.dds_output = Signal(lut_bits)
        self.dds_output = Signal(lut_bits)
        self.phase_offset = Signal(lut_bits)
        self.offset_last = Signal.like(self.phase_offset)
        self.amplitude = Signal(12)
        self.quadrant = Signal(2)
        # self.debug = Signal(phase_bits)
        self.lut_bits = lut_bits
        self.phase_bits = phase_bits
        self.index_size = (1<< (lut_bits)) 
        self.PI = 1 << (lut_bits)
        self.FULL = 1 << (lut_bits)
        self.index = Signal(lut_bits)
        self.lut_size = 2**lut_bits
        self.mask  = (1 << self.lut_bits) - 1  # Creates a mask with lower lut_bits bits set to 1

        # Internal LUT for the sine wave
        self.lut = self.create_sine_lut(lut_bits, self.lut_size)

    def elaborate(self, platform):
        m = nm.Module()
        theta = Signal.like(self.phase_accumulator)
        data = Signal(self.lut_bits)
        read_port = self.lut.read_port()
        m.submodules += read_port
        mulbuff = Signal.like(data + 12)
        # enc = m.submodules.enc =  PriorityEncoder(width = self.phase_bits)
        m.d.sync += self.freq_last.eq(self.freq)
        m.d.sync += self.offset_last.eq(self.phase_offset)
        initial_phase_set = Signal(reset=0)  # Flag to apply phase offset once or conditionally
        
        # Conditional application of phase offset
        with m.If(self.phase_offset != self.offset_last): 
            m.d.sync += self.phase_accumulator.eq(self.phase_accumulator + self.phase_offset)


        with m.If(self.freq != self.freq_last): 
            m.d.sync += self.phase_accumulator.eq(self.freq)
        with m.Else():
               m.d.sync += self.phase_accumulator.eq(self.phase_accumulator + self.freq)
        
        m.d.sync += theta.eq(self.phase_accumulator[-len(read_port.addr):])
        m.d.sync += self.index.eq(theta)
        m.d.comb += read_port.addr.eq(self.index)
        m.d.comb += mulbuff.eq(read_port.data * self.amplitude)
        m.d.comb += self.dds_output.eq(mulbuff[:self.lut_bits])
        # m.d.comb += [
        #     read_port.addr.eq(self.theta),
        #     self.dds_output.eq(read_port.data)
        # ]
        return m

        
def test():
    f1 = DDS(phase_bits=phase_bits, lut_bits=lut_bits, freq_bits=phase_bits)
    f2 = DDS(phase_bits=phase_bits, lut_bits=lut_bits, freq_bits=phase_bits)
    dut = SUM()
    m = Module()
    m.domains += ClockDomain("sync")
    m.submodules.dut = dut
    m.submodules.f1 = f1
    m.submodules.f2 = f2
    m.d.comb += dut.in_1.eq(f1.dds_output)
    m.d.comb += dut.in_2.eq(f2.dds_output)
    m.d.comb +=f1.freq.eq(4000)
    m.d.comb +=f2.freq.eq(80000)
    m.d.comb +=f1.amplitude.eq(1)
    m.d.comb +=f2.amplitude.eq(1)
    def bench():
        for i in range(2,8):
            # yield f1.freq.eq(i* 10)
            # yield f2.freq.eq(i * 1000)
            yield f1.phase_offset.eq(i*2)
            yield f2.phase_offset.eq(i*4)
            # yield f1.amplitude.eq(2*i)
            # yield f2.amplitude.eq(4*i)
            # upper_range = 16384/ 2
            upper_range = int((16384 / 2))
            # upper_range = int((16384 / i) * 4 )
            for ph in range(upper_range):
                yield dut.out_1
                yield
            yield
            # for i in reversed(range(4,10)):
            #     yield dut.freq.eq(i*1)
            #     for ph in range(16384):
            #         yield dut.dds_output
            #         yield
            #     yield

    sim = Simulator(m)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)

    # with sim.write_vcd("dds4.vcd", gtkw_file= open("dds4.gtkw", "w"), traces=[dut.freq_last, dut.phase_accumulator, dut.freq, dut.dds_output, dut.quadrant, dut.index]):
        # sim.run()
    with sim.write_vcd("sum.vcd", "sum.gtkw", traces=[f1.phase_accumulator, f2.phase_accumulator, f1.amplitude, f1.phase_offset, f2.amplitude, f2.phase_offset, dut.in_1, dut.in_2, dut.out_1]):
        sim.run()

# if __name__ == "__main__":
#     f1 = DDS(phase_bits=phase_bits, lut_bits=lut_bits, freq_bits=phase_bits)
#     f2 = DDS(phase_bits=phase_bits, lut_bits=lut_bits, freq_bits=phase_bits)
#     dut = SUM()
#     m = Module()
#     m.domains += ClockDomain("sync")
#     m.submodules.dut = dut
#     m.submodules.f1 = f1
#     m.submodules.f2 = f2
#     m.d.comb += dut.in_1.eq(f1.dds_output)
#     m.d.comb += dut.in_2.eq(f2.dds_output)
#     # m.d.comb +=f1.freq.eq(4000)
#     # m.d.comb +=f2.freq.eq(40000)
#     # dut = DDS(16,16)
#     v = verilog.convert(
#         m, name="dds", ports=[m.dut.in_1, m.dut.in_2, m.dut.out_1],
#         emit_src=False, strip_internal_attrs=True)
#     print(v)


if __name__ == "__main__":
    dut = DDS(phase_bits=phase_bits, lut_bits=lut_bits, freq_bits=phase_bits)
    # dut = DDS(16,16)
    v = verilog.convert(
        dut, name="dds", ports=[dut.amplitude, dut.phase_offset, dut.freq, dut.dds_output],
        emit_src=False, strip_internal_attrs=True)
    print(v)
