# Mock Method-A model for case_0001_serial_line (no failures, deterministic).
# Mirrors what a faithful FactoryFlow model looks like: FactorySimPy Machines
# cannot express random breakdowns, so behaviour follows pure deterministic
# processing-time flow. Executed by the harness wrapper (probe appended).
import simpy
import factorysimpy
from factorysimpy.nodes.node import Node
from factorysimpy.nodes.machine import Machine
from factorysimpy.edges.buffer import Buffer
from factorysimpy.nodes.source import Source
from factorysimpy.nodes.sink import Sink


class SerialLine(Node):
    def __init__(self, env, pts, caps, inter_arrival):
        super().__init__(env, "TOP")
        n = len(pts)
        self.source = Source(env, "SRC", inter_arrival_time=inter_arrival)
        self.machines = [
            Machine(env, f"M{i + 1}", processing_delay=pts[i]) for i in range(n)
        ]
        self.sink = Sink(env, "SINK")
        self.add_child_node([self.source] + self.machines + [self.sink])
        buffers = []
        b0 = Buffer(env, "B0", capacity=caps[0])
        b0.connect(self.source, self.machines[0])
        buffers.append(b0)
        for i in range(n - 1):
            b = Buffer(env, f"B{i + 1}", capacity=caps[i + 1])
            b.connect(self.machines[i], self.machines[i + 1])
            buffers.append(b)
        bout = Buffer(env, f"B{n}", capacity=caps[0] if len(caps) > n else 8)
        bout.connect(self.machines[n - 1], self.sink)
        buffers.append(bout)
        self.add_child_edge(buffers)
        self.entry = self.source
        self.exit = self.sink


env = simpy.Environment()
TOP = SerialLine(env, pts=[150.0, 120.0, 180.0, 120.0, 150.0],
                 caps=[20, 8, 8, 8, 8], inter_arrival=130.0)
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(450000.0)