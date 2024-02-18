import numpy as np
import amaranth as nm
from amaranth.hdl.rec import Record

from amaranth.hdl.ast import *
from amaranth.back import verilog
from amaranth.sim import Simulator

from amaranth.sim import *

from amaranth import *
import numpy as np

# this is leider needed because the simulator cant recurse so deep and its a known issue with pysim afaik
import sys
sys.setrecursionlimit(100000)

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

        # Output of the DDS
        self.dds_output = Signal(lut_bits)
        self.quadrant = Signal(2)
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
        acum = Signal.like(self.phase_accumulator)
        data = Signal(self.lut_bits)
        read_port = self.lut.read_port()
        m.submodules += read_port
        m.d.sync += self.phase_accumulator.eq(self.phase_accumulator + self.freq)
        # Add delayed signal for the phase accum
        m.d.sync += acum.eq(self.phase_accumulator)
        # Quadrant is always the 2 MSB bits of the phase acummulator
        m.d.sync += self.quadrant.eq(self.phase_accumulator[self.phase_bits-2:]) 

        with m.Switch(self.quadrant):
            with m.Case(0):
                m.d.sync += theta.eq(acum[:len(read_port.addr)])
                m.d.sync += self.index.eq(theta)
                m.d.sync += read_port.addr.eq(self.index)
                m.d.sync += data.eq(read_port.data)
            with m.Case(1):
                m.d.sync += theta.eq(self.PI - (acum[:len(read_port.addr)]))
                # normalize theta
                m.d.sync += self.index.eq(theta & self.mask)
                # same as int((theta / (np.pi / 2)) * len(lut))
                # m.d.sync += self.index.eq((theta << self.lut_bits - 1) >> (self.lut_bits - 1))
                with m.If(self.index >= (self.index_size- self.freq)):
                    m.d.sync += self.index.eq(self.index - self.freq)
                m.d.sync += read_port.addr.eq(self.index)
                m.d.sync += data.eq(read_port.data)
            with m.Case(2):
                m.d.sync += theta.eq(acum[:len(read_port.addr)] -self.PI)
                # normalize theta
                m.d.sync += self.index.eq(theta & self.mask)
                # m.d.sync += self.index.eq((theta << self.lut_bits - 1) >> (self.lut_bits - 1))
                with m.If(self.index >= (self.index_size- self.freq)):
                    m.d.sync += self.index.eq(self.index - self.freq)
                m.d.sync += read_port.addr.eq((self.index))
                m.d.sync += data.eq(-read_port.data + (1 << self.lut_bits))
            with m.Case(3):
                m.d.sync += theta.eq(self.PI + self.PI - acum[:len(read_port.addr)])
                # normalize theta
                m.d.sync += self.index.eq(theta & self.mask)
                # m.d.sync += self.index.eq((theta << self.lut_bits - 1) >> (self.lut_bits - 1))
                with m.If(self.index >= (self.index_size - self.freq )):
                    m.d.sync += self.index.eq(self.index - self.freq)
                m.d.sync += read_port.addr.eq(self.index)
                m.d.sync += data.eq(-read_port.data + (1 << self.lut_bits))

        m.d.sync += self.dds_output.eq(data)
        return m

        
def test():
    phase_bits = 14
    dut = DDS(phase_bits=phase_bits, lut_bits=phase_bits - 2, freq_bits=14)
    def bench():
        # yield dut.freq.eq(10)
        for i in range(1,6):
            yield dut.freq.eq(1*i)
            for ph in range(16384):
                yield dut.dds_output
                yield
            # yield dut.freq.eq(2)
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)

    # with sim.write_vcd("dds4.vcd", traces=[dut.phase_accumulator, dut.freq, dut.dds_output, dut.quadrant, dut.index]):
    with sim.write_vcd("dds4.vcd", gtkw_file= open("dds4.gtkw", "w"), traces=[dut.phase_accumulator, dut.freq, dut.dds_output, dut.quadrant, dut.index]):
        sim.run()

if __name__ == "__main__":
    dut = DDS(phase_bits=14, lut_bits=14, freq_bits=14)
    # dut = DDS(16,16)
    v = verilog.convert(
        dut, name="dds", ports=[dut.phase_accumulator, dut.freq, dut.dds_output],
        emit_src=False, strip_internal_attrs=True)
    print(v)