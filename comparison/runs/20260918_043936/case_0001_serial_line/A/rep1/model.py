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
        
        self.source = Source(env, id="src", inter_arrival_time=130.0)
        self.add_child_node(self.source)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        machine_data = [
            {"id": "M1", "delay": 149.90, "avail": 99.45, "mttr": 793.67},
            {"id": "M2", "delay": 120.50, "avail": 96.86, "mttr": 1053.95},
            {"id": "M3", "delay": 180.59, "avail": 99.03, "mttr": 4200.65},
            {"id": "M4", "delay": 120.83, "avail": 97.39, "mttr": 1894.81},
            {"id": "M5", "delay": 149.89, "avail": 99.56, "mttr": 641.17},
        ]
        
        self.M = []
        for d in machine_data:
            mtbf = (d['avail'] * d['mttr']) / (100.0 - d['avail'])
            m = Machine(env, id=d['id'], processing_delay=d['delay'], mtbf=mtbf, mttr=d['mttr'])
            self.M.append(m)
        self.add_child_node(self.M)
        
        buffer_caps = [20, 8, 8, 8, 8]
        self.buffers = []
        for i in range(5):
            b = Buffer(env, id=f"B{i}", capacity=buffer_caps[i])
            self.buffers.append(b)
        
        b5 = Buffer(env, id="B5")
        self.buffers.append(b5)
        self.add_child_edge(self.buffers)
        
        self.buffers[0].connect(self.source, self.M[0])
        for i in range(4):
            self.buffers[i+1].connect(self.M[i], self.M[i+1])
        self.buffers[5].connect(self.M[4], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)