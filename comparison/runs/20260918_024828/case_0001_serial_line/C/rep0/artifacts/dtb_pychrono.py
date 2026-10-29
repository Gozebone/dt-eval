```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import time
import threading
import queue
import json
import csv
from datetime import datetime
from collections import defaultdict, deque

class ProductionLineDigitalTwin:
    def __init__(self):
        # Initialize PyChrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))
        
        # Simulation parameters
        self.time_step = 0.01
        self.sim_time = 0.0
        self.max_time = 1000.0
        
        # Equipment simulation objects
        self.machines = {}
        self.buffers = {}
        
        # Data collection
        self.production_log = []
        self.energy_log = []
        self.buffer_level_log = []
        self.event_log = []
        self.machine_status_log = []
        
        # Machine parameters
        self.machine_params = {
            "M1": {"avg_processing_time": 5.0, "mttr": 2.0, "power_active": 1000.0, "power_idle": 100.0},
            "M2": {"avg_processing_time": 4.0, "mttr": 1.5, "power_active": 1200.0, "power_idle": 120.0},
            "M3": {"avg_processing_time": 6.0, "mttr": 2.5, "power_active": 1100.0, "power_idle": 110.0},
            "M4": {"avg_processing_time": 5.5, "mttr": 1.8, "power_active": 1300.0, "power_idle": 130.0},
            "M5": {"avg_processing_time": 4.5, "mttr": 2.2, "power_active": 900.0, "power_idle": 90.0}
        }
        
        # Buffer parameters
        self.buffer_capacity = 10
        
        # Initialize simulation components
        self.init_simulation()
        
    def init_simulation(self):
        """Initialize all simulation components"""
        # Create ground
        ground = chrono.ChBody()
        ground.SetBodyFixed(True)
        ground.SetPos(chrono.ChVectorD(0, -1, 0))
        self.system.Add(ground)
        
        # Create machines and buffers
        self.create_machines()
        self.create_buffers()
        
        # Create conveyor belts
        self.create_conveyor_belts()
        
    def create_machines(self):
        """Create machine bodies with sensors"""
        positions = [chrono.ChVectorD(-10, 0, 0), chrono.ChVectorD(-5, 0, 0), 
                     chrono.ChVectorD(0, 0, 0), chrono.ChVectorD(5, 0, 0), 
                     chrono.ChVectorD(10, 0, 0)]
        
        for i, (machine_id, params) in enumerate(self.machine_params.items()):
            # Create machine body
            machine = chrono.ChBody()
            machine.SetPos(positions[i])
            machine.SetBodyFixed(True)
            machine.SetMass(1000)
            machine.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
            
            # Create visual shape
            machine_shape = chrono.ChVisualShapeBox(2.0, 1.0, 1.0)
            machine_shape.SetColor(chrono.ChColor(0.8, 0.2, 0.2))
            machine.AddVisualShape(machine_shape, chrono.ChFrameD())
            
            self.system.Add(machine)
            self.machines[machine_id] = {
                "body": machine,
                "params": params,
                "status": "idle",
                "processing_start_time": 0.0,
                "process_time": 0.0,
                "energy_consumption": 0.0,
                "last_failure_time": 0.0,
                "failure_duration": 0.0
            }
    
    def create_buffers(self):
        """Create buffer zones for material flow"""
        positions = [chrono.ChVectorD(-7.5, 0, 0), chrono.ChVectorD(-2.5, 0, 0), 
                     chrono.ChVectorD(2.5, 0, 0), chrono.ChVectorD(7.5, 0, 0)]
        
        for i in range(4):
            buffer_id = f"B{i}"
            buffer_body = chrono.ChBody()
            buffer_body.SetPos(positions[i])
            buffer_body.SetBodyFixed(True)
            buffer_body.SetMass(500)
            buffer_body.SetInertiaXX(chrono.ChVectorD(50, 50, 50))
            
            # Create visual shape
            buffer_shape = chrono.ChVisualShapeBox(1.0, 0.5, 1.0)
            buffer_shape.SetColor(chrono.ChColor(0.2, 0.5, 0.8))
            buffer_body.AddVisualShape(buffer_shape, chrono.ChFrameD())
            
            self.system.Add(buffer_body)
            self.buffers[buffer_id] = {
                "body": buffer_body,
                "items": deque(),
                "capacity": self.buffer_capacity
            }
    
    def create_conveyor_belts(self):
        """Create conveyor belts to connect machines and buffers"""
        # This would use PyChrono constraints to model conveyor belts
        # For simplicity, we simulate conveyor movement through time-based logic
        pass
    
    def generate_part(self):
        """Generate new parts at input buffer"""
        part_id = f"part_{len(self.production_log) + 1}"
        part_data = {
            "id": part_id,
            "process_start_time": self.sim_time,
            "current_station": "B0",
            "status": "in_buffer",
            "buffer_level": 1
        }
        self.production_log.append(part_data)
        self.event_log.append({
            "timestamp": self.sim_time,
            "event_type": "part_generated",
            "part_id": part_id,
            "station": "B0"
        })
        return part_id
    
    def process_part(self, part_id, machine_id):
        """Process a part at a specific machine"""
        # Update part status
        for part in self.production_log:
            if part["id"] == part_id:
                part["current_station"] = machine_id
                part["status"] = "processing"
                part["processing_start_time"] = self.sim_time
                break
        
        # Update machine status
        machine = self.machines[machine_id]
        machine["status"] = "processing"
        machine["processing_start_time"] = self.sim_time
        machine["process_time"] = machine["params"]["avg_processing_time"]
        
        # Log event
        self.event_log.append({
            "timestamp": self.sim_time,
            "event_type": "part_processed",
            "part_id": part_id,
            "station": machine_id
        })
    
    def complete_processing(self, part_id, machine_id):
        """Complete processing and move part to next buffer"""
        # Update part status
        for part in self.production_log:
            if part["id"] == part_id:
                part["status"] = "completed" if machine_id == "M5" else "in_buffer"
                part["processing_end_time"] = self.sim_time
                part["total_process_time"] = self.sim_time - part["processing_start_time"]
                break
        
        # Update machine status
        machine = self.machines[machine_id]
        machine["status"] = "idle"
        
        # Log event
        self.event_log.append({
            "timestamp": self.sim_time,
            "event_type": "processing_complete",
            "part_id": part_id,
            "station": machine_id
        })
    
    def update_machine_status(self):
        """Update machine status based on processing state"""
        for machine_id, machine_data in self.machines.items():
            if machine_data["status"] == "processing":
                elapsed_time = self.sim_time - machine_data["processing_start_time"]
                if elapsed_time > machine_data["process_time"]:
                    # Processing complete
                    # In a full implementation, we would find the part being processed
                    self.complete_processing("temp_part", machine_id)
    
    def collect_energy_data(self):
        """Collect energy consumption data"""
        total_energy = 0.0
        for machine_id, machine_data in self.machines.items():
            if machine_data["status"] == "processing":
                power = machine_data["params"]["power_active"]
            else:
                power = machine_data["params"]["power_idle"]
            total_energy += power * self.time_step
            machine_data["energy_consumption"] += power * self.time_step
        
        self.energy_log.append({
            "timestamp": self.sim_time,
            "total_energy_kwh": total_energy / 3600000.0,  # Convert to kWh
            "machine_energy": {mid: data["energy_consumption"] / 3600000.0 
                              for mid, data in self.machines.items()}
        })
    
    def collect_buffer_data(self):
        """Collect buffer level data"""
        buffer_levels = {}
        for buffer_id, buffer_data in self.buffers.items():
            buffer_levels[buffer_id] = len(buffer_data["items"])
        
        self.buffer_level_log.append({
            "timestamp": self.sim_time,
            "buffer_levels": buffer_levels
        })
    
    def collect_machine_status(self):
        """Collect detailed machine status"""
        machine_status = {}
        for machine_id, machine_data in self.machines.items():
            machine_status[machine_id] = {
                "status": machine_data["status"],
                "energy_consumption": machine_data["energy_consumption"],
                "processing_time": machine_data["process_time"]
            }
        
        self.machine_status_log.append({
            "timestamp": self.sim_time,
            "machine_status": machine_status
        })
    
    def run_simulation(self):
        """Run the complete simulation"""
        print("Starting simulation...")
        
        # Generate initial parts
        for i in range(5):
            self.generate_part()
        
        # Main simulation loop
        while self.sim_time < self.max_time:
            # Update machine status
            self.update_machine_status()
            
            # Collect data at regular intervals
            if int(self.sim_time) % 5 == 0:  # Every 5 time units
                self.collect_energy_data()
                self.collect_buffer_data()
                self.collect_machine_status()
            
            # Advance simulation
            self.system.DoStepDynamics(self.time_step)
            self.sim_time += self.time_step
            
            # Generate new parts periodically
            if int(self.sim_time) % 10 == 0:
                self.generate_part()
            
            # Display progress
            if int(self.sim_time) % 100 == 0:
                print(f"Simulation time: {self.sim_time:.2f}")
        
        print("Simulation completed.")
        self.save_logs()
    
    def save_logs(self):
        """Save all collected data to CSV files"""
        # Save production log
        with open('production_log.csv', 'w', newline='') as csvfile:
            fieldnames = ['id', 'process_start_time', 'current_station', 'status', 'buffer_level']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.production_log:
                writer.writerow(row)
        
        # Save energy log
        with open('energy_log.csv', 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'total_energy_kwh']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.energy_log:
                writer.writerow(row)
        
        # Save buffer level log
        with open('buffer_log.csv', 'w', newline='') as csvfile:
            fieldnames = ['timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.buffer_level_log:
                writer.writerow(row)
        
        # Save event log
        with open('event_log.csv', 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'event_type', 'part_id', 'station']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.event_log:
                writer.writerow(row)
        
        # Save machine status log
        with open('machine_status_log.csv', 'w', newline='') as csvfile:
            fieldnames = ['timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.machine_status_log:
                writer.writerow(row)

# Main execution
if __name__ == "__main__":
    # Create and run simulation
    digital_twin = ProductionLineDigitalTwin()
    digital_twin.run_simulation()
```