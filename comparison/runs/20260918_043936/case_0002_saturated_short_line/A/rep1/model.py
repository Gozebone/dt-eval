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

        machine_data = [
            {"id": "M1", "processing_delay": 89.98, "Availability_%": 100.00, "MTTR_s": 1.0, "EnergyIdling": 0.30, "EnergyWorking": 3.00},
            {"id": "M2", "processing_delay": 69.98, "Availability_%": 99.55, "MTTR_s": 392.5, "EnergyIdling": 0.44, "EnergyWorking": 4.50},
            {"id": "M3", "processing_delay": 110.28, "Availability_%": 100.00, "MTTR_s": 1.0, "EnergyIdling": 0.60, "EnergyWorking": 5.98}
        ]
        self.M = [Machine(env, **data) for data in machine_data]
        self.add_child_node(self.M)

        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)

        buffer_data = [
            {"id": "B0", "capacity": 15},
            {"id": "B1", "capacity": 5},
            {"id": "B2", "capacity": 5}
        ]
        self.e = [Buffer(env, **data) for data in buffer_data]
        self.e.append(Buffer(env, id="edge[3]"))
        self.add_child_edge(self.e)

        self.e[0].connect(self.source, self.M[0])
        for i in range(2):
            self.e[i+1].connect(self.M[i], self.M[i+1])
        self.e[3].connect(self.M[2], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)