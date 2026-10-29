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
        
        machine_params = [
            (149.90, 0.9945, 793.67),
            (120.50, 0.9686, 1053.95),
            (180.59, 0.9903, 4200.65),
            (120.83, 0.9739, 1894.81),
            (149.89, 0.9956, 641.17)
        ]
        
        self.M = []
        for i, (delay, avail, mttr) in enumerate(machine_params):
            mtbf = (avail * mttr) / (1 - avail)
            self.M.append(Machine(env, id=f"M{i+1}", processing_delay=delay, mtbf=mtbf, mttr=mttr))
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        buffer_capacities = [20, 8, 8, 8, 8]
        self.e = []
        for i, cap in enumerate(buffer_capacities):
            self.e.append(Buffer(env, id=f"B{i}", capacity=cap))
        
        self.e.append(Buffer(env, id="B5"))
        self.add_child_edge(self.e)
        
        self.e[0].connect(self.source, self.M[0])
        for i in range(4):
            self.e[i+1].connect(self.M[i], self.M[i+1])
        self.e[5].connect(self.M[4], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)