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
            {"id": "M1", "delay": 149.90, "avail": 0.9945, "mttr": 793.67},
            {"id": "M2", "delay": 120.50, "avail": 0.9686, "mttr": 1053.95},
            {"id": "M3", "delay": 180.59, "avail": 0.9903, "mttr": 4200.65},
            {"id": "M4", "delay": 120.83, "avail": 0.9739, "mttr": 1894.81},
            {"id": "M5", "delay": 149.89, "avail": 0.9956, "mttr": 641.17}
        ]
        
        self.M = []
        for p in machine_params:
            mtbf = (p["avail"] * p["mttr"]) / (1.0 - p["avail"])
            self.M.append(Machine(env, id=p["id"], processing_delay=p["delay"], mtbf=mtbf, mttr=p["mttr"]))
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        buffer_caps = [20, 8, 8, 8, 8]
        self.e = []
        for i in range(6):
            if i < 5:
                self.e.append(Buffer(env, id=f"B{i}", capacity=buffer_caps[i]))
            else:
                self.e.append(Buffer(env, id=f"B{i}"))
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