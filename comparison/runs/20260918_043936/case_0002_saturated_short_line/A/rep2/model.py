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
        
        m_data = [
            {"id": "M1", "delay": 89.98, "mtbf": None, "mttr": None},
            {"id": "M2", "delay": 69.98, "mtbf": 86829.72222222222, "mttr": 392.5},
            {"id": "M3", "delay": 110.28, "mtbf": None, "mttr": None}
        ]
        
        self.M = []
        for d in m_data:
            if d["mtbf"] is not None:
                m = Machine(env, id=d["id"], processing_delay=d["delay"], mtbf=d["mtbf"], mttr=d["mttr"])
            else:
                m = Machine(env, id=d["id"], processing_delay=d["delay"])
            self.M.append(m)
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        b_data = [
            {"id": "B0", "cap": 15},
            {"id": "B1", "cap": 5},
            {"id": "B2", "cap": 5},
            {"id": "edge[3]", "cap": None}
        ]
        
        self.edges = []
        for d in b_data:
            if d["cap"] is not None:
                b = Buffer(env, id=d["id"], capacity=d["cap"])
            else:
                b = Buffer(env, id=d["id"])
            self.edges.append(b)
        self.add_child_edge(self.edges)
        
        nodes_seq = [self.source] + self.M + [self.sink]
        for i in range(len(self.edges)):
            self.edges[i].connect(nodes_seq[i], nodes_seq[i+1])

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)