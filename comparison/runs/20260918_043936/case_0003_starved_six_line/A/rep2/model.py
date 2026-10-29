import simpy
import factorysimpy
from factorysimpy.nodes.node import Node
from factorysimpy.nodes.machine import Machine
from factorysimpy.edges.buffer import Buffer
from factorysimpy.nodes.source import Source
from factorysimpy.nodes.sink import Sink

class SerialProductionLine(Node):
    def __init__(self, env, id):
        super().__init__(env, id)
        
        self.source = Source(env, id="src", inter_arrival_time=300)
        self.add_child_node(self.source)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        machine_data = [
            {"name": "M1", "delay": 199.86, "avail": 98.77, "mttr": 1062.58},
            {"name": "M2", "delay": 220.09, "avail": 98.63, "mttr": 1184.73},
            {"name": "M3", "delay": 240.01, "avail": 99.78, "mttr": 314.75},
            {"name": "M4", "delay": 259.99, "avail": 98.85, "mttr": 1246.71},
            {"name": "M5", "delay": 230.13, "avail": 99.51, "mttr": 2129.84},
            {"name": "M6", "delay": 209.83, "avail": 98.98, "mttr": 2200.89},
        ]
        
        self.M = []
        for data in machine_data:
            avail = data["avail"] / 100.0
            mtbf = (avail * data["mttr"]) / (1.0 - avail)
            machine = Machine(env, id=data["name"], processing_delay=data["delay"], mtbf=mtbf, mttr=data["mttr"])
            self.M.append(machine)
        self.add_child_node(self.M)
        
        self.buffers = [Buffer(env, id=f"B{i}", capacity=10) for i in range(7)]
        self.add_child_edge(self.buffers)
        
        self.buffers[0].connect(self.source, self.M[0])
        for i in range(5):
            self.buffers[i+1].connect(self.M[i], self.M[i+1])
        self.buffers[6].connect(self.M[5], self.sink)

env = simpy.Environment()
TOP = SerialProductionLine(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)