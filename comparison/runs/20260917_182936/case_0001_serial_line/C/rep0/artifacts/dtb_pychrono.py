```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import math
import time
from datetime import datetime
import threading
import queue

# Initialize PyChrono system
chrono.SetChronoDataPath('path_to_chrono_data')  # Replace with actual path
system = chrono.ChSystemNSC()
system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))  # No gravity for this application

# Simulation parameters
TIME_STEP = 0.01
SIMULATION_DURATION = 3600 * 24  # 24 hours simulation
PART_ARRIVAL_INTERVAL = 130.0  # seconds
LOGGING_INTERVAL = 1.0  # seconds

# Data structures for logging
class MachineState:
    def __init__(self, machine_id):
        self.machine_id = machine_id
        self.status = "IDLE"  # IDLE, PROCESSING, MAINTENANCE
        self.processing_time = 0.0
        self.mttr = 0.0
        self.power_consumption = 0.0
        self.last_state_change = 0.0
        self.total_processing_time = 0.0
        self.total_maintenance_time = 0.0
        self.total_energy_consumption = 0.0
        self.processed_parts = 0
        self.availability = 0.0
        self.avg_processing_time = 0.0

class BufferState:
    def __init__(self, buffer_id, capacity):
        self.buffer_id = buffer_id
        self.capacity = capacity
        self.current_parts = 0
        self.parts_in_buffer = []
        self.total_parts = 0

# Global state tracking
machines = {}
buffers = {}
part_counter = 0
last_arrival_time = 0.0
simulation_start_time = time.time()
energy_consumption_log = []
wip_log = []
throughput_log = []
machine_availability_log = []

# Create machines with their specifications
def create_machine(machine_id, process_time, availability, mttr, work_power, idle_power):
    machine = MachineState(machine_id)
    machine.process_time = process_time
    machine.availability = availability
    machine.mttr = mttr
    machine.work_power = work_power
    machine.idle_power = idle_power
    machines[machine_id] = machine
    return machine

# Create buffers
def create_buffer(buffer_id, capacity):
    buffer = BufferState(buffer_id, capacity)
    buffers[buffer_id] = buffer
    return buffer

# Initialize machines
for i, process in enumerate([
    {"machine": "M1", "process_time_s": 150, "availability": 0.98, "mttr_s": 600, "work_power_kw": 4.0, "idle_power_kw": 0.4},
    {"machine": "M2", "process_time_s": 120, "availability": 0.97, "mttr_s": 900, "work_power_kw": 5.0, "idle_power_kw": 0.5},
    {"machine": "M3", "process_time_s": 180, "availability": 0.95, "mttr_s": 1200, "work_power_kw": 6.0, "idle_power_kw": 0.6},
    {"machine": "M4", "process_time_s": 120, "availability": 0.97, "mttr_s": 900, "work_power_kw": 5.0, "idle_power_kw": 0.5},
    {"machine": "M5", "process_time_s": 150, "availability": 0.98, "mttr_s": 600, "work_power_kw": 4.0, "idle_power_kw": 0.4}
]):
    create_machine(process["machine"], process["process_time_s"], process["availability"],
                   process["mttr_s"], process["work_power_kw"], process["idle_power_kw"])

# Create buffers
create_buffer("B0", 20)
create_buffer("B1", 8)
create_buffer("B2", 8)
create_buffer("B3", 8)
create_buffer("B4", 8)

# Part class representing workpieces
class Workpiece:
    def __init__(self, part_id):
        self.id = part_id
        self.created_at = time.time()
        self.processing_start_time = None
        self.processing_end_time = None
        self.current_machine = None
        self.path = []  # Track the processing path through machines

# Part generation function
def generate_part():
    global part_counter, last_arrival_time
    current_time = time.time() - simulation_start_time
    
    if current_time - last_arrival_time >= PART_ARRIVAL_INTERVAL:
        part_counter += 1
        part = Workpiece(part_counter)
        buffers["B0"].current_parts += 1
        buffers["B0"].parts_in_buffer.append(part)
        buffers["B0"].total_parts += 1
        last_arrival_time = current_time
        print(f"Part {part_counter} generated at {current_time:.2f}s")
        return part
    return None

# Simulate machine processing
def simulate_machine_processing(machine_id, part):
    machine = machines[machine_id]
    
    # Check if machine is available
    if machine.status != "IDLE":
        return False
    
    # Simulate machine availability
    if np.random.rand() > machine.availability:
        # Machine fails - go into maintenance
        machine.status = "MAINTENANCE"
        machine.mttr = machine.mttr
        machine.last_state_change = time.time() - simulation_start_time
        return False
    
    # Start processing
    machine.status = "PROCESSING"
    machine.processing_start_time = time.time() - simulation_start_time
    machine.processed_parts += 1
    part.current_machine = machine_id
    part.processing_start_time = time.time() - simulation_start_time
    part.path.append(machine_id)
    
    # Simulate processing duration
    processing_duration = machine.process_time
    
    # Simulate energy consumption during processing
    machine.power_consumption = machine.work_power
    machine.total_energy_consumption += machine.work_power * (processing_duration / 3600)  # kWh
    
    return True

# Update machine status based on processing completion
def update_machine_status():
    current_time = time.time() - simulation_start_time
    
    for machine_id, machine in machines.items():
        if machine.status == "PROCESSING":
            if current_time - machine.processing_start_time >= machine.process_time:
                # Processing completed
                machine.status = "IDLE"
                machine.total_processing_time += machine.process_time
                machine.avg_processing_time = machine.total_processing_time / machine.processed_parts
                
                # Calculate availability
                total_time = current_time - machine.last_state_change
                machine.availability = machine.total_processing_time / total_time if total_time > 0 else 0.0
                
                # Reset power consumption
                machine.power_consumption = machine.idle_power
                machine.total_energy_consumption += machine.idle_power * (0.1 / 3600)  # Assume small idle consumption
                
                # Move part to next buffer
                if machine_id == "M1":
                    if buffers["B1"].current_parts < buffers["B1"].capacity:
                        buffers["B1"].current_parts += 1
                        print(f"Part moved from M1 to B1")
                    else:
                        print("Buffer B1 full, part remains in M1")
                elif machine_id == "M2":
                    if buffers["B2"].current_parts < buffers["B2"].capacity:
                        buffers["B2"].current_parts += 1
                        print(f"Part moved from M2 to B2")
                    else:
                        print("Buffer B2 full, part remains in M2")
                elif machine_id == "M3":
                    if buffers["B3"].current_parts < buffers["B3"].capacity:
                        buffers["B3"].current_parts += 1
                        print(f"Part moved from M3 to B3")
                    else:
                        print("Buffer B3 full, part remains in M3")
                elif machine_id == "M4":
                    if buffers["B4"].current_parts < buffers["B4"].capacity:
                        buffers["B4"].current_parts += 1
                        print(f"Part moved from M4 to B4")
                    else:
                        print("Buffer B4 full, part remains in M4")
                elif machine_id == "M5":
                    # Final stage - part finished
                    part = buffers["B4"].parts_in_buffer.pop(0) if buffers["B4"].parts_in_buffer else None
                    if part:
                        part.processing_end_time = time.time() - simulation_start_time
                        print(f"Part {part.id} completed at {part.processing_end_time:.2f}s")
                        
                        # Log throughput
                        throughput_log.append({
                            'timestamp': part.processing_end_time,
                            'processed_parts': part_counter,
                            'throughput_per_hour': part_counter / (part.processing_end_time / 3600)
                        })

# Log simulation data
def log_simulation_data(current_time):
    # Log WIP (Work In Progress)
    wip_total = sum(buf.current_parts for buf in buffers.values())
    wip_log.append({
        'timestamp': current_time,
        'wip_total': wip_total,
        'b0_count': buffers['B0'].current_parts,
        'b1_count': buffers['B1'].current_parts,
        'b2_count': buffers['B2'].current_parts,
        'b3_count': buffers['B3'].current_parts,
        'b4_count': buffers['B4'].current_parts
    })
    
    # Log machine availability
    for machine_id, machine in machines.items():
        machine_availability_log.append({
            'timestamp': current_time,
            'machine_id': machine_id,
            'availability': machine.availability,
            'status': machine.status
        })
    
    # Log energy consumption
    total_energy = sum(machine.total_energy_consumption for machine in machines.values())
    energy_consumption_log.append({
        'timestamp': current_time,
        'total_energy_kwh': total_energy,
        'energy_per_part': total_energy / part_counter if part_counter > 0 else 0.0
    })

# Main simulation loop
def run_simulation():
    print("Starting simulation...")
    start_time = time.time()
    
    # Initial part generation
    generate_part()
    
    step = 0
    while True:
        current_time = time.time() - start_time
        
        # Generate new parts periodically
        generate_part()
        
        # Update machine statuses
        update_machine_status()
        
        # Process parts through machines
        for machine_id, machine in machines.items():
            if machine.status == "IDLE":
                # Try to move part from buffer to machine
                if machine_id == "M1" and buffers["B1"].current_parts > 0:
                    # Try to move part from B1 to M1
                    if buffers["B1"].current_parts > 0:
                        part = buffers["B1"].parts_in_buffer.pop(0)
                        buffers["B1"].current_parts -= 1
                        simulate_machine_processing(machine_id, part)
                elif machine_id == "M2" and buffers["B2"].current_parts > 0:
                    # Try to move part from B2 to M2
                    if buffers["B2"].current_parts > 0:
                        part = buffers["B2"].parts_in_buffer.pop(0)
                        buffers["B2"].current_parts -= 1
                        simulate_machine_processing(machine_id, part)
                elif machine_id == "M3" and buffers["B3"].current_parts > 0:
                    # Try to move part from B3 to M3
                    if buffers["B3"].current_parts > 0:
                        part = buffers["B3"].parts_in_buffer.pop(0)
                        buffers["B3"].current_parts -= 1
                        simulate_machine_processing(machine_id, part)
                elif machine_id == "M4" and buffers["B4"].current_parts > 0:
                    # Try to move part from B4 to M4
                    if buffers["B4"].current_parts > 0:
                        part = buffers["B4"].parts_in_buffer.pop(0)
                        buffers["B4"].current_parts -= 1
                        simulate_machine_processing(machine_id, part)
                elif machine_id == "M5":
                    # Check if we can start processing from B4
                    if buffers["B4"].current_parts > 0:
                        part = buffers["B4"].parts_in_buffer.pop(0)
                        buffers["B4"].current_parts -= 1
                        simulate_machine_processing(machine_id, part)
        
        # Log data periodically
        if int(current_time) % int(LOGGING_INTERVAL) == 0:
            log_simulation_data(current_time)
            
        # Break condition
        if current_time >= SIMULATION_DURATION:
            break
            
        step += 1
        time.sleep(TIME_STEP)
    
    # Final logging
    final_time = time.time() - start_time
    log_simulation_data(final_time)
    
    # Print summary statistics
    print("\n--- Simulation Summary ---")
    print(f"Total parts processed: {part_counter}")
    print(f"Simulation time: {final_time:.2f} seconds")
    print(f"Final WIP: {sum(buf.current_parts for buf in buffers.values())}")
    print(f"Total energy consumed: {sum(log['total_energy_kwh'] for log in energy_consumption_log):.2f} kWh")
    
    # Save logs to files
    with open('wip_log.csv', 'w') as f:
        f.write('timestamp,wip_total,b0_count,b1_count,b2_count,b3_count