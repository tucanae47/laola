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

# taken from amaranth.lib.coding but modified to change to MSB
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
        lut_gen =[int((np.sin(np.pi / 2 * i / lut_size) + 1) * (2**(lut_bits - 1) - 1)) for i in range(lut_size)]
        return Memory(width=lut_bits, depth=lut_size, init=lut_gen)

    def __init__(self, phase_bits=32, lut_bits=10, freq_bits=32):
        # Phase accumulator
        self.phase_accumulator = nm.Signal(phase_bits)
        
        # Frequency control (phase increment)
        self.freq = Signal(freq_bits)

        self.freq_last = Signal.like(self.freq)
        # Output of the DDS
        self.dds_output = Signal(lut_bits)
        self.quadrant = Signal(lut_bits)
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
        # enc = m.submodules.enc =  PriorityEncoder(width = self.phase_bits)
        m.d.sync += self.freq_last.eq(self.freq)
        
        with m.If(self.freq != self.freq_last): 
            m.d.sync += self.phase_accumulator.eq(self.freq)
        with m.Else():
            m.d.sync += self.phase_accumulator.eq(self.phase_accumulator + self.freq)

        # Add delayed signal for the phase accum
        # m.d.comb += factor.eq((Const(self.lut_size) // self.freq) * 4)
        # m.d.comb += enc.i.eq(factor)
        m.d.comb += self.quadrant.eq(self.phase_accumulator[self.lut_bits:self.lut_bits+2]) 

        with m.Switch(self.quadrant):
            with m.Case(0):
                m.d.sync += theta.eq(self.phase_accumulator[:len(read_port.addr)])
                m.d.sync += self.index.eq(theta)
                m.d.comb += read_port.addr.eq(self.index)
                m.d.comb += data.eq(read_port.data)
            with m.Case(1):
                m.d.sync += theta.eq(self.PI - (self.phase_accumulator[:len(read_port.addr)]))
                # normalize theta
                m.d.sync += self.index.eq(theta & self.mask)
                # same as int((theta / (np.pi / 2)) * len(lut))
                # m.d.sync += self.index.eq((theta << self.lut_bits - 1) >> (self.lut_bits - 1))
                with m.If(self.index >= (self.index_size- self.freq)):
                    m.d.sync += self.index.eq(self.index - self.freq)
                m.d.comb += read_port.addr.eq(self.index)
                m.d.comb += data.eq(read_port.data)
            with m.Case(2):
                m.d.sync += theta.eq(self.phase_accumulator[:len(read_port.addr)] -self.PI)
                # normalize theta
                m.d.sync += self.index.eq(theta & self.mask)
                # m.d.sync += self.index.eq((theta << self.lut_bits - 1) >> (self.lut_bits - 1))
                with m.If(self.index >= (self.index_size- self.freq)):
                    m.d.sync += self.index.eq(self.index - self.freq)
                m.d.comb += read_port.addr.eq((self.index))
                m.d.comb += data.eq(-read_port.data + (1 << self.lut_bits))
            with m.Case(3):
                m.d.sync += theta.eq(self.PI + self.PI - self.phase_accumulator[:len(read_port.addr)])
                # normalize theta
                m.d.sync += self.index.eq(theta & self.mask)
                # m.d.sync += self.index.eq((theta << self.lut_bits - 1) >> (self.lut_bits - 1))
                with m.If(self.index >= (self.index_size - self.freq )):
                    m.d.sync += self.index.eq(self.index - self.freq)
                m.d.comb += read_port.addr.eq(self.index)
                m.d.comb += data.eq(-read_port.data + (1 << self.lut_bits))

        m.d.comb += self.dds_output.eq(data)
        return m

        
def test():
    dut = DDS(phase_bits=phase_bits, lut_bits=lut_bits, freq_bits=phase_bits)
    def bench():
        for i in range(2,10):
            yield dut.freq.eq(i * 1)
            upper_range = int((16384 / i) * 4 )
            for ph in range(upper_range*2):
                yield dut.dds_output
                yield
            yield
        for i in reversed(range(4,10)):
            yield dut.freq.eq(i*1)
            for ph in range(16384):
                yield dut.dds_output
                yield
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)

    with sim.write_vcd("dds4.vcd", gtkw_file= open("dds4.gtkw", "w"), traces=[dut.freq_last, dut.phase_accumulator, dut.freq, dut.dds_output, dut.quadrant, dut.index]):
        sim.run()

if __name__ == "__main__":
    dut = DDS(phase_bits=phase_bits, lut_bits=lut_bits, freq_bits=phase_bits)
    # dut = DDS(16,16)
    v = verilog.convert(
        dut, name="dds", ports=[dut.freq, dut.dds_output],
        emit_src=False, strip_internal_attrs=True)
    print(v)