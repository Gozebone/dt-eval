```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import pychrono.fea as fea
import math
import numpy as np
import time
import sqlite3
from datetime import datetime

# Initialize PyChrono system
chrono.SetChronoDataPath('path/to/chronodata')  # Adjust path if needed
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Simulation parameters
time_step = 0.01
simulation_time = 3600  # 1 hour of simulation
update_interval = 150  # seconds

# Database initialization
def init_database():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    
    # Create tables according to schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS production_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            machine_name TEXT,
            detail_id INTEGER,
            process_time REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machine_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            machine_name TEXT,
            state TEXT,
            uptime REAL,
            downtime REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS energy_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            machine_name TEXT,
            power_kw REAL,
            energy_kwh REAL
        )
    ''')
    
    conn.commit()
    return conn

# Delayed event class for machine processing
class MachineEvent:
    def __init__(self, machine_name, process_time, availability, mttr, work_power, idle_power):
        self.machine_name = machine_name
        self.process_time = process_time
        self.availability = availability
        self.mttr = mttr
        self.work_power = work_power
        self.idle_power = idle_power
        self.current_state = "IDLE"
        self.state_start_time = 0
        self.total_uptime = 0
        self.total_downtime = 0
        self.energy_consumed = 0
        self.processing_start = None
        self.processing_end = None
        self.detail_count = 0
        self.detail_id = 0

    def update_state(self, current_time, new_state):
        if self.current_state != new_state:
            if self.current_state == "WORKING":
                self.total_uptime += current_time - self.state_start_time
            elif self.current_state == "DOWN":
                self.total_downtime += current_time - self.state_start_time
            self.state_start_time = current_time
            self.current_state = new_state

    def get_energy_consumption(self, current_time):
        if self.current_state == "WORKING":
            return self.work_power * (current_time - self.state_start_time) / 3600
        elif self.current_state == "IDLE":
            return self.idle_power * (current_time - self.state_start_time) / 3600
        return 0

    def process_detail(self, current_time):
        self.detail_id += 1
        self.processing_start = current_time
        self.update_state(current_time, "WORKING")
        return self.process_time

    def complete_processing(self, current_time):
        self.processing_end = current_time
        self.detail_count += 1
        self.update_state(current_time, "IDLE")

    def get_availability(self):
        total_time = self.total_uptime + self.total_downtime
        if total_time == 0:
            return 1.0
        return self.total_uptime / total_time

# Create machines
machines = {}
machine_configs = [
    {"name": "M1", "process_time": 100, "availability": 0.9, "mttr": 2400, "work_power": 4.0, "idle_power": 0.4},
    {"name": "M2", "process_time": 130, "availability": 0.92, "mttr": 3000, "work_power": 5.0, "idle_power": 0.5},
    {"name": "M3", "process_time": 90, "availability": 0.88, "mttr": 3600, "work_power": 4.5, "idle_power": 0.45},
    {"name": "M4", "process_time": 140, "availability": 0.91, "mttr": 4800, "work_power": 7.0, "idle_power": 0.7},
    {"name": "M5", "process_time": 110, "availability": 0.93, "mttr": 2400, "work_power": 5.5, "idle_power": 0.55}
]

for config in machine_configs:
    machines[config["name"]] = MachineEvent(
        config["name"],
        config["process_time"],
        config["availability"],
        config["mttr"],
        config["work_power"],
        config["idle_power"]
    )

# Buffer setup (simple representation)
buffers = {}
for i in range(5):  # B0 to B4
    buffers[f"B{i}"] = {"capacity": 10, "current": 0, "max_capacity": 10}

# Create a simple detail that moves through machines
class Detail:
    def __init__(self, detail_id):
        self.detail_id = detail_id
        self.position = chrono.ChVectorD(0, 0, 0)
        self.velocity = chrono.ChVectorD(0, 0, 0)
        self.machine_queue = ["M1", "M2", "M3", "M4", "M5"]
        self.current_machine = 0
        self.processing_start = None
        self.processing_end = None
        self.buffer_position = None

# Initialize database
conn = init_database()
cursor = conn.cursor()

# Simulation parameters
current_time = 0
detail_counter = 0
next_detail_arrival = 0

# Simulation loop
try:
    while current_time < simulation_time:
        # Handle detail arrivals
        if current_time >= next_detail_arrival:
            detail_counter += 1
            print(f"Detail {detail_counter} arrived at time {current_time}")
            next_detail_arrival += 150  # Next arrival in 150 seconds

        # Update each machine's state
        for machine_name, machine in machines.items():
            machine.update_state(current_time, machine.current_state)
            energy = machine.get_energy_consumption(current_time)
            machine.energy_consumed += energy

            # Log machine state
            cursor.execute(
                "INSERT INTO machine_states (timestamp, machine_name, state, uptime, downtime) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), machine_name, machine.current_state, 
                 machine.total_uptime, machine.total_downtime)
            )
            
            # Log energy consumption
            cursor.execute(
                "INSERT INTO energy_consumption (timestamp, machine_name, power_kw, energy_kwh) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), machine_name, 
                 machine.work_power if machine.current_state == 'WORKING' else machine.idle_power,
                 energy)
            )

        # Log production events (simplified)
        if current_time % update_interval == 0 and current_time > 0:
            for machine_name, machine in machines.items():
                if machine.current_state == "WORKING" and machine.processing_start:
                    cursor.execute(
                        "INSERT INTO production_events (timestamp, event_type, machine_name, detail_id, process_time) VALUES (?, ?, ?, ?, ?)",
                        (datetime.now().isoformat(), "PROCESSING_COMPLETE", machine_name, 
                         machine.detail_id, machine.processing_end - machine.processing_start if machine.processing_end else 0)
                    )

        # Advance simulation
        system.DoStepDynamics(time_step)
        current_time += time_step

        # Update database periodically
        if current_time % 60 == 0:  # Log every minute
            conn.commit()

except Exception as e:
    print(f"Error in simulation: {e}")
finally:
    conn.commit()
    conn.close()
    print("Simulation completed. Data saved to database.")

# Final statistics report
print("\n=== Simulation Summary ===")
for machine_name, machine in machines.items():
    print(f"{machine_name}:")
    print(f"  Details processed: {machine.detail_count}")
    print(f"  Total uptime: {machine.total_uptime:.2f}s")
    print(f"  Total downtime: {machine.total_downtime:.2f}s")
    print(f"  Availability: {machine.get_availability():.2%}")
    print(f"  Energy consumed: {machine.energy_consumed:.2f} kWh")
    print(f"  Average processing time: {machine.process_time:.2f}s")
    print()
```