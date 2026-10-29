```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import datetime
import json
import time
import numpy as np
from collections import defaultdict
import sqlite3

# Initialize PyChrono system
chrono.SetChronoDataPath('path_to_chrono_data')  # Set to actual path
system = chrono.ChSystemNSC()
system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))  # No gravity for this simulation

# Create a database connection
conn = sqlite3.connect('production_line.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS machines (
        id TEXT PRIMARY KEY,
        processing_time_s DOUBLE PRECISION,
        availability DOUBLE PRECISION,
        mttr_s DOUBLE PRECISION,
        power_working_kw DOUBLE PRECISION,
        power_idle_kw DOUBLE PRECISION
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS buffers (
        id TEXT PRIMARY KEY,
        capacity INTEGER
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS samples (
        ts TIMESTAMPTZ,
        machine_id TEXT,
        tag TEXT,
        value DOUBLE PRECISION
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        ts TIMESTAMPTZ,
        machine_id TEXT,
        reason_code TEXT,
        duration_s DOUBLE PRECISION,
        energy_kwh DOUBLE PRECISION
    )
''')

# Insert machines and buffers data
machines_data = [
    ('M1', 100, 0.9, 2400, 4.0, 0.4),
    ('M2', 130, 0.92, 3000, 5.0, 0.5),
    ('M3', 90, 0.88, 3600, 4.5, 0.45),
    ('M4', 140, 0.91, 4800, 7.0, 0.7),
    ('M5', 110, 0.93, 2400, 5.5, 0.55)
]

buffers_data = [
    ('B0', 6),
    ('B1', 3),
    ('B2', 3),
    ('B3', 3),
    ('B4', 3)
]

cursor.executemany('INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?, ?, ?)', machines_data)
cursor.executemany('INSERT OR REPLACE INTO buffers VALUES (?, ?)', buffers_data)
conn.commit()

# Define machine parameters
machines = {
    'M1': {'processing_time_s': 100, 'availability': 0.9, 'mttr_s': 2400, 'power_working_kw': 4.0, 'power_idle_kw': 0.4},
    'M2': {'processing_time_s': 130, 'availability': 0.92, 'mttr_s': 3000, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M3': {'processing_time_s': 90, 'availability': 0.88, 'mttr_s': 3600, 'power_working_kw': 4.5, 'power_idle_kw': 0.45},
    'M4': {'processing_time_s': 140, 'availability': 0.91, 'mttr_s': 4800, 'power_working_kw': 7.0, 'power_idle_kw': 0.7},
    'M5': {'processing_time_s': 110, 'availability': 0.93, 'mttr_s': 2400, 'power_working_kw': 5.5, 'power_idle_kw': 0.55}
}

# Define buffers with capacity
buffers = {
    'B0': 6, 'B1': 3, 'B2': 3, 'B3': 3, 'B4': 3
}

# Create parts (representing products being processed)
class Part:
    def __init__(self, id):
        self.id = id
        self.current_station = None
        self.start_time = None
        self.processing_start_time = None
        self.processing_end_time = None

# Create machines as bodies
class Machine:
    def __init__(self, id, processing_time_s, availability, mttr_s, power_working_kw, power_idle_kw):
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.is_operational = True
        self.failure_time = 0
        self.last_failure_start = 0
        self.total_operational_time = 0
        self.total_downtime = 0
        self.parts_processed = 0
        self.parts_in_queue = 0
        self.power_consumption = 0
        self.power_accumulated_kwh = 0
        self.next_part_ready_time = 0
        self.active_part = None

    def simulate_failure(self, current_time):
        if not self.is_operational and current_time - self.failure_time >= self.mttr_s:
            self.is_operational = True
            self.total_downtime += current_time - self.last_failure_start
            self.failure_time = 0
            self.last_failure_start = 0
            return False  # Machine is repaired
        elif not self.is_operational:
            return True  # Still broken
        elif not self.is_operational and current_time - self.failure_time < self.mttr_s:
            return True  # Still broken

        # Randomly decide if machine fails based on availability
        if np.random.random() > self.availability:
            self.is_operational = False
            self.failure_time = current_time
            self.last_failure_start = current_time
            return True  # Machine failed
        return False  # Machine operational

    def get_power_kW(self):
        if self.is_operational and self.active_part:
            return self.power_working_kw
        else:
            return self.power_idle_kw

# Create machines
machines_objects = {}
for machine_id, params in machines.items():
    machines_objects[machine_id] = Machine(machine_id, **params)

# Create buffers (storage areas)
class Buffer:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity
        self.parts = []
        self.current_count = 0

    def add_part(self, part):
        if self.current_count < self.capacity:
            self.parts.append(part)
            self.current_count += 1
            return True
        return False

    def remove_part(self):
        if self.current_count > 0:
            part = self.parts.pop(0)
            self.current_count -= 1
            return part
        return None

# Create buffers
buffers_objects = {}
for buffer_id, capacity in buffers.items():
    buffers_objects[buffer_id] = Buffer(buffer_id, capacity)

# Create a source part generator
class SourceGenerator:
    def __init__(self, inter_arrival_time_s):
        self.inter_arrival_time_s = inter_arrival_time_s
        self.next_arrival = inter_arrival_time_s
        self.part_count = 0

    def generate_part(self, current_time):
        if current_time >= self.next_arrival:
            self.part_count += 1
            part = Part(f"P{self.part_count}")
            part.start_time = current_time
            self.next_arrival += self.inter_arrival_time_s
            return part
        return None

# Create source
source = SourceGenerator(150)  # Inter-arrival time of 150 seconds

# Simulation parameters
sim_duration_s = 432000  # 5 days in seconds
time_step = 1  # Simulation time step in seconds
current_time = 0
part_count = 0
last_log_time = 0

# Track events and samples
events = []
samples = []

# Initialize simulation
print("Starting simulation...")
start_time = time.time()

# Main simulation loop
while current_time < sim_duration_s:

    # Generate new parts
    new_part = source.generate_part(current_time)
    if new_part:
        part_count += 1
        new_part.current_station = 'M1'
        buffers_objects['B0'].add_part(new_part)
        print(f"Generated part {new_part.id} at time {current_time}s")

    # Process machines
    for machine_id, machine in machines_objects.items():
        if machine.is_operational and machine.active_part is None:
            # Check if there's a part in the buffer waiting
            buffer_id = f"B{int(machine_id[1:]) - 1}" if machine_id != 'M1' else 'B0'
            if buffers_objects[buffer_id].current_count > 0:
                part = buffers_objects[buffer_id].remove_part()
                if part:
                    machine.active_part = part
                    part.processing_start_time = current_time
                    machine.next_part_ready_time = current_time + machine.processing_time_s
                    print(f"Part {part.id} started processing on {machine_id} at {current_time}s")

        # Check if machine has finished processing
        if machine.active_part and current_time >= machine.next_part_ready_time:
            machine.active_part.processing_end_time = current_time
            machine.active_part.current_station = machine_id
            machine.parts_processed += 1
            part = machine.active_part
            machine.active_part = None

            # Check if this is the last machine (M5)
            if machine_id == 'M5':
                print(f"Part {part.id} completed at time {current_time}s")
                # Log part completion
                part.end_time = current_time
                part.processing_duration = part.processing_end_time - part.processing_start_time
            else:
                # Move to next buffer
                next_buffer_id = f"B{int(machine_id[1:])}"
                if not buffers_objects[next_buffer_id].add_part(part):
                    print(f"Buffer {next_buffer_id} full, part {part.id} delayed")

        # Simulate machine failure
        machine.simulate_failure(current_time)

        # Calculate power consumption
        power_kW = machine.get_power_kW()
        machine.power_consumption = power_kW
        machine.power_accumulated_kwh += power_kW * time_step / 3600  # Convert to kWh

        # Log machine samples
        timestamp = datetime.datetime.fromtimestamp(current_time).isoformat()
        samples.append((timestamp, machine_id, 'power_kw', power_kW))
        samples.append((timestamp, machine_id, 'availability', machine.availability))
        samples.append((timestamp, machine_id, 'mttr_s', machine.mttr_s))
        samples.append((timestamp, machine_id, 'parts_processed', machine.parts_processed))
        samples.append((timestamp, machine_id, 'parts_in_queue', buffers_objects[f"B{int(machine_id[1:]) - 1 if machine_id != 'M1' else 0}"].current_count))

    # Check for failures and log events
    for machine_id, machine in machines_objects.items():
        if not machine.is_operational:
            if machine.failure_time > 0:
                # Log failure event
                timestamp = datetime.datetime.fromtimestamp(current_time).isoformat()
                duration = current_time - machine.failure_time
                events.append((timestamp, machine_id, 'FAILURE', duration, 0))

    # Log samples every second
    if current_time - last_log_time >= 1:
        for machine_id, machine in machines_objects.items():
            timestamp = datetime.datetime.fromtimestamp(current_time).isoformat()
            samples.append((timestamp, machine_id, 'power_kwh_accumulated', machine.power_accumulated_kwh))
            samples.append((timestamp, machine_id, 'operational', int(machine.is_operational)))
            samples.append((timestamp, machine_id, 'mttr_s_remaining', machine.mttr_s - (current_time - machine.failure_time) if not machine.is_operational else 0))
        last_log_time = current_time

    # Advance simulation time
    current_time += time_step

# Log events and samples to database
for event in events:
    cursor.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?)', event)

for sample in samples:
    cursor.execute('INSERT INTO samples VALUES (?, ?, ?, ?)', sample)

conn.commit()

# Print summary statistics
print("\nSimulation Summary:")
print(f"Total parts processed: {part_count}")
for machine_id, machine in machines_objects.items():
    print(f"Machine {machine_id}:")
    print(f"  Parts processed: {machine.parts_processed}")
    print(f"  Total power consumed (kWh): {machine.power_accumulated_kwh:.2f}")
    print(f"  Operational time: {machine.total_operational_time:.2f}s")
    print(f"  Downtime: {machine.total_downtime:.2f}s")
    print(f"  Availability: {(machine.total_operational_time / (machine.total_operational_time + machine.total_downtime)) * 100:.2f}%")

# Close database connection
conn.close()

end_time = time.time()
print(f"Simulation completed in {end_time - start_time:.2f} seconds")
```