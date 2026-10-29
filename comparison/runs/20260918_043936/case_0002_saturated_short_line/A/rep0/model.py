import simpy
import factorysimpy
from factorysimpy.nodes.node import Node
from factorysimpy.nodes.machine import Machine
from factorysimpy.edges.buffer import Buffer
from factorysimpy.nodes.source import Source
from factorysimpy.nodes.sink import Sink

class SystemModel(Node):
    def __init__(self, env, id):
        super().__init__(env, id)
        
        self.source = Source(env, id="src", inter_arrival_time=60)
        self.add_child_node(self.source)
        
        m_delays = [89.98, 69.98, 110.28]
        self.M = [Machine(env, id=f"M{i+1}", processing_delay=m_delays[i]) for i in range(3)]
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        b_caps = [15, 5, 5]
        self.B = [Buffer(env, id=f"B{i}", capacity=b_caps[i]) for i in range(3)]
        self.B.append(Buffer(env, id="B3"))
        self.add_child_edge(self.B)
        
        self.B[0].connect(self.source, self.M[0])
        for i in range(2):
            self.B[i+1].connect(self.M[i], self.M[i+1])
        self.B[3].connect(self.M[2], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)