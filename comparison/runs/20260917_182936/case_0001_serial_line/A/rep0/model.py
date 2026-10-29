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
        
        machine_data = [
            {"name": "M1", "delay": 149.90, "avail": 99.45, "mttr": 793.67},
            {"name": "M2", "delay": 120.50, "avail": 96.86, "mttr": 1053.95},
            {"name": "M3", "delay": 180.59, "avail": 99.03, "mttr": 4200.65},
            {"name": "M4", "delay": 120.83, "avail": 97.39, "mttr": 1894.81},
            {"name": "M5", "delay": 149.89, "avail": 99.56, "mttr": 641.17}
        ]
        
        self.M = []
        for data in machine_data:
            avail = data["avail"] / 100.0
            mtbf = (avail * data["mttr"]) / (1.0 - avail)
            m = Machine(env, id=data["name"], processing_delay=data["delay"], mtbf=mtbf, mttr=data["mttr"])
            self.M.append(m)
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        buffer_caps = [20, 8, 8, 8, 8]
        self.e = []
        for i in range(6):
            if i < 5:
                b = Buffer(env, id=f"B{i}", capacity=buffer_caps[i])
            else:
                b = Buffer(env, id=f"edge[{i}]")
            self.e.append(b)
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