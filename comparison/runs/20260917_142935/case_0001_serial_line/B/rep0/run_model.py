# Mock Method-B model for case_0001_serial_line.
# In mock mode the adapter substitutes {"throughput": 19.868056, "wip": 40.386633, "energy": 0.989219} with the case's
# ground-truth KPIs so the stdout contract is satisfied and the parsing path is
# exercised end-to-end. Not an LLM-generated model — plumbing only.
import json

_TRUTH = json.loads("""{"throughput": 19.868056, "wip": 40.386633, "energy": 0.989219}""")

print(f"Throughput = {_TRUTH['throughput']:.3f} parts/hour")
print(f"WIP = {_TRUTH['wip']:.3f} parts")
print(f"Mean Energy Consumption per Part = {_TRUTH['energy']:.6f} kWh/part")
print("=== Bottleneck Frequency over runs ===")
print("M3 100%")