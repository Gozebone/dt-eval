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
        
        self.source = Source(env, id="src", inter_arrival_time=45)
        self.add_child_node(self.source)
        
        machine_params = [
            {"id": "M1", "processing_delay": 59.99, "mtbf": 461353.86, "mttr": 46.14},
            {"id": "M2", "processing_delay": 80.28},
            {"id": "M3", "processing_delay": 70.16, "mtbf": 226452.93, "mttr": 272.07},
            {"id": "M4", "processing_delay": 75.03}
        ]
        self.M = [Machine(env, **p) for p in machine_params]
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        buffer_params = [
            {"id": "B0", "capacity": 25},
            {"id": "B1", "capacity": 10},
            {"id": "B2", "capacity": 10},
            {"id": "B3", "capacity": 10},
            {"id": "edge[4]"}
        ]
        self.edges = [Buffer(env, **p) for p in buffer_params]
        self.add_child_edge(self.edges)
        
        self.edges[0].connect(self.source, self.M[0])
        for i in range(3):
            self.edges[i+1].connect(self.M[i], self.M[i+1])
        self.edges[4].connect(self.M[3], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)