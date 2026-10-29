import sys as _sys, os as _os
_sys.path.insert(0, '/ssd/projects/dt-eval/FactoryFlow/FactoryFlow_v2/app/src')
_os.environ.setdefault('MPLBACKEND', 'Agg')
class _StStreamlit:
    graphviz_chart = staticmethod(lambda *a, **k: None)
    @staticmethod
    def set_page_config(*a, **k):
        return None
_sys.modules.setdefault('streamlit', _StStreamlit())
class _F:
    def __init__(self):
        self._buf = ''
    def write(self, s):
        self._buf += s
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            if '__FF_KPI_JSON__' in line:
                _sys.__stdout__.write(line + '\n')
                _sys.__stdout__.flush()
    def flush(self):
        pass
_sys.stdout = _F()
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
        
        self.source = Source(env, id="src", inter_arrival_time=300)
        self.add_child_node(self.source)
        
        machine_data = [
            {"id": "M1", "delay": 199.86, "avail": 98.77, "mttr": 1062.58},
            {"id": "M2", "delay": 220.09, "avail": 98.63, "mttr": 1184.73},
            {"id": "M3", "delay": 240.01, "avail": 99.78, "mttr": 314.75},
            {"id": "M4", "delay": 259.99, "avail": 98.85, "mttr": 1246.71},
            {"id": "M5", "delay": 230.13, "avail": 99.51, "mttr": 2129.84},
            {"id": "M6", "delay": 209.83, "avail": 98.98, "mttr": 2200.89}
        ]
        
        self.M = []
        for data in machine_data:
            avail = data["avail"] / 100.0
            mttr = data["mttr"]
            mtbf = (avail * mttr) / (1.0 - avail)
            m = Machine(env, id=data["id"], processing_delay=data["delay"], mtbf=mtbf, mttr=mttr)
            self.M.append(m)
        self.add_child_node(self.M)
        
        self.sink = Sink(env, id="sink")
        self.add_child_node(self.sink)
        
        self.buffers = [Buffer(env, id=f"B{i}", capacity=10) for i in range(7)]
        self.add_child_edge(self.buffers)
        
        self.buffers[0].connect(self.source, self.M[0])
        for i in range(5):
            self.buffers[i+1].connect(self.M[i], self.M[i+1])
        self.buffers[6].connect(self.M[5], self.sink)

env = simpy.Environment()
TOP = SystemModel(env, "TOP")
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(432000)

# ===== harness probe (appended) =====
import json as _json
from factorysimpy.nodes.node import Node as _Node
from factorysimpy.nodes.machine import Machine as _Machine
_PROBE = {}
def _harness_machines():
    found = []
    for _v in list(globals().values()):
        if isinstance(_v, _Node):
            for _t in _v.all_tops:
                nodes, _edges = _t.get_all_nodes_edges()
                for _n in nodes.values():
                    if isinstance(_n, _Machine):
                        found.append(_n)
    return found
_ms = _harness_machines()
if _ms:
    _per = {}
    for _m in _ms:
        _s = _m.stats
        _tts = _s.get('total_time_spent_in_states', {})
        _horizon = float(getattr(_m.env, 'now', 0.0))
        _proc = max([_tts.get(_k, 0.0) for _k in (
            'PROCESSING_STATE', 'ATLEAST_ONE_PROCESSING_STATE',
            'ALL_ACTIVE_PROCESSING_STATE')] or [0.0])
        _n = _s.get('num_item_processed', 0)
        if isinstance(_n, (list, tuple, dict)):
            _n = len(_n)
        _per[_m.id] = {
            'processed': _n,
            'horizon': _horizon,
            'utilization': (_proc / _horizon) if _horizon else None,
            'throughput_per_unit': (_n / _horizon) if _horizon else None,
        }
    _PROBE['machines'] = _per
    _PROBE['time_unit_s'] = 1.0
print('__FF_KPI_JSON__:' + _json.dumps(_PROBE, default=str))
