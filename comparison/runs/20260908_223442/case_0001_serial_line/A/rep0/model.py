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
        
        self.source = Source(env, id="src", inter_arrival_time=130)
        self.add_child_node(self.source)
        
        delays = [149.90, 120.50, 180.59, 120.83, 149.89]
        self.M = [Machine(env, id=f"M{i+1}", processing_delay=delays[i]) for i in range(5)]
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        capacities = [20, 8, 8, 8, 8]
        self.B = [Buffer(env, id=f"B{i}", capacity=capacities[i]) for i in range(5)]
        self.B.append(Buffer(env, id="B5"))
        self.add_child_edge(self.B)
        
        self.B[0].connect(self.source, self.M[0])
        for i in range(4):
            self.B[i+1].connect(self.M[i], self.M[i+1])
        self.B[5].connect(self.M[4], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)