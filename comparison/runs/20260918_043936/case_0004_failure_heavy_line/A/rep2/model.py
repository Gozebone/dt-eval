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

        self.source = Source(env, id="src", inter_arrival_time=150)
        self.add_child_node(self.source)

        delays = [99.96, 130.16, 90.14, 140.19, 109.82]
        self.M = [Machine(env, id=f"M{i+1}", processing_delay=delays[i]) for i in range(5)]
        self.add_child_node(self.M)

        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)

        capacities = [6, 3, 3, 3, 3]
        self.edges = []
        
        for i in range(5):
            buf = Buffer(env, id=f"edge[{i}]", capacity=capacities[i])
            self.edges.append(buf)
            
        buf_sink = Buffer(env, id="edge[5]")
        self.edges.append(buf_sink)
        
        self.add_child_edge(self.edges)

        self.edges[0].connect(self.source, self.M[0])
        for i in range(4):
            self.edges[i+1].connect(self.M[i], self.M[i+1])
        self.edges[5].connect(self.M[4], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)