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
# Mock Method-A model for case_0001_serial_line (no failures, deterministic).
# Mirrors what a faithful FactoryFlow model looks like: FactorySimPy Machines
# cannot express random breakdowns, so behaviour follows pure deterministic
# processing-time flow. Executed by the harness wrapper (probe appended).
import simpy
import factorysimpy
from factorysimpy.nodes.node import Node
from factorysimpy.nodes.machine import Machine
from factorysimpy.edges.buffer import Buffer
from factorysimpy.nodes.source import Source
from factorysimpy.nodes.sink import Sink


class SerialLine(Node):
    def __init__(self, env, pts, caps, inter_arrival):
        super().__init__(env, "TOP")
        n = len(pts)
        self.source = Source(env, "SRC", inter_arrival_time=inter_arrival)
        self.machines = [
            Machine(env, f"M{i + 1}", processing_delay=pts[i]) for i in range(n)
        ]
        self.sink = Sink(env, "SINK")
        self.add_child_node([self.source] + self.machines + [self.sink])
        buffers = []
        b0 = Buffer(env, "B0", capacity=caps[0])
        b0.connect(self.source, self.machines[0])
        buffers.append(b0)
        for i in range(n - 1):
            b = Buffer(env, f"B{i + 1}", capacity=caps[i + 1])
            b.connect(self.machines[i], self.machines[i + 1])
            buffers.append(b)
        bout = Buffer(env, f"B{n}", capacity=caps[0] if len(caps) > n else 8)
        bout.connect(self.machines[n - 1], self.sink)
        buffers.append(bout)
        self.add_child_edge(buffers)
        self.entry = self.source
        self.exit = self.sink


env = simpy.Environment()
TOP = SerialLine(env, pts=[150.0, 120.0, 180.0, 120.0, 150.0],
                 caps=[20, 8, 8, 8, 8], inter_arrival=130.0)
TOP.fill_hierarchical_id()
TOP.validate()
TOP.run_simulation(450000.0)

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
