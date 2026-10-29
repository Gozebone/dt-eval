```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fea as fea
import numpy as np
import json
import time
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json
import threading

class ProductionLineSimulation:
    def __init__(self):
        # Initialize Chrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))
        
        # Simulation parameters
        self.sim_time = 0.0
        self.end_time = 432000.0  # 5 days in seconds
        self.time_step = 0.01
        
        # Equipment data
        self.equipment = {
            "source": {"inter_arrival_time": 300.0},
            "M1": {"processing_time": 199.86, "availability": 0.9877, "mttr": 1062.58, "power_working": 5.0, "power_idle": 0.5},
            "M2": {"processing_time": 220.09, "availability": 0.9863, "mttr": 1184.73, "power_working": 5.49, "power_idle": 0.55},
            "M3": {"processing_time": 240.01, "availability": 0.9978, "mttr": 314.75, "power_working": 5.99, "power_idle": 0.59},
            "M4": {"processing_time": 259.99, "availability": 0.9885, "mttr": 1246.71, "power_working": 6.99, "power_idle": 0.69},
            "M5": {"processing_time": 230.13, "availability": 0.9951, "mttr": 2129.84, "power_working": 6.49, "power_idle": 0.64},
            "M6": {"processing_time": 209.83, "availability": 0.9898, "mttr": 2200.89, "power_working": 6.0, "power_idle": 0.6},
            "sink": {},
            "B0": {"capacity": 10, "before": "source", "after": "M1"},
            "B1": {"capacity": 10, "before": "M1", "after": "M2"},
            "B2": {"capacity": 10, "before": "M2", "after": "M3"},
            "B3": {"capacity": 10, "before": "M3", "after": "M4"},
            "B4": {"capacity": 10, "before": "M4", "after": "M5"},
            "B5": {"capacity": 10, "before": "M5", "after": "M6"}
        }
        
        # Create components
        self.source = None
        self.machines = {}
        self.buffers = {}
        self.sink = None
        self.parts = []
        self.part_counter = 0
        
        # Data logging
        self.events_log = []
        self.samples_log = []
        self.data_lock = threading.Lock()
        
        # Initialize simulation components
        self.setup_simulation()
        
    def setup_simulation(self):
        # Create source
        self.source = chrono.ChBody()
        self.source.SetPos(chrono.ChVectorD(0, 0, 0))
        self.source.SetBodyFixed(True)
        self.system.Add(self.source)
        
        # Create stations
        station_positions = [
            chrono.ChVectorD(10, 0, 0),  # M1
            chrono.ChVectorD(20, 0, 0),  # M2
            chrono.ChVectorD(30, 0, 0),  # M3
            chrono.ChVectorD(40, 0, 0),  # M4
            chrono.ChVectorD(50, 0, 0),  # M5
            chrono.ChVectorD(60, 0, 0),  # M6
        ]
        
        for i, (machine_id, params) in enumerate(self.equipment.items()):
            if machine_id in ["source", "sink"]:
                continue
            if machine_id.startswith("M"):
                machine_body = chrono.ChBody()
                machine_body.SetPos(station_positions[i-1])
                machine_body.SetBodyFixed(True)
                self.system.Add(machine_body)
                self.machines[machine_id] = {
                    "body": machine_body,
                    "processing_time": params["processing_time"],
                    "availability": params["availability"],
                    "mttr": params["mttr"],
                    "power_working": params["power_working"],
                    "power_idle": params["power_idle"],
                    "state": "idle",  # idle, processing, failed
                    "last_state_change": 0.0,
                    "processing_start": 0.0,
                    "failure_end": 0.0
                }
        
        # Create buffers
        buffer_positions = [
            chrono.ChVectorD(5, 0, 0),   # B0
            chrono.ChVectorD(15, 0, 0),  # B1
            chrono.ChVectorD(25, 0, 0),  # B2
            chrono.ChVectorD(35, 0, 0),  # B3
            chrono.ChVectorD(45, 0, 0),  # B4
            chrono.ChVectorD(55, 0, 0),  # B5
        ]
        
        for i, (buffer_id, params) in enumerate(self.equipment.items()):
            if buffer_id.startswith("B"):
                buffer_body = chrono.ChBody()
                buffer_body.SetPos(buffer_positions[i-7])  # Adjust index
                buffer_body.SetBodyFixed(True)
                self.system.Add(buffer_body)
                self.buffers[buffer_id] = {
                    "body": buffer_body,
                    "capacity": params["capacity"],
                    "before": params["before"],
                    "after": params["after"],
                    "parts": []
                }
        
        # Create sink
        self.sink = chrono.ChBody()
        self.sink.SetPos(chrono.ChVectorD(70, 0, 0))
        self.sink.SetBodyFixed(True)
        self.system.Add(self.sink)
        
        # Create part bodies
        self.create_part(0.0)
        
    def create_part(self, creation_time):
        part = chrono.ChBody()
        part.SetPos(chrono.ChVectorD(-5, 0, 0))
        part.SetBodyFixed(False)
        
        # Add collision shape
        collision_shape = chrono.ChCollisionModel()
        collision_shape.AddSphere(0.5)
        part.SetCollide(True)
        part.SetCollisionModel(collision_shape)
        
        self.system.Add(part)
        self.parts.append({
            "body": part,
            "id": self.part_counter,
            "creation_time": creation_time,
            "current_station": "source",
            "position": -5.0,
            "state": "moving"  # moving, processing, finished
        })
        self.part_counter += 1
        
    def update_part_positions(self):
        # Move parts along the line
        for part_info in self.parts:
            if part_info["state"] == "moving":
                part_info["position"] += 0.1  # Speed
                part_info["body"].SetPos(chrono.ChVectorD(part_info["position"], 0, 0))
                
                # Check buffer boundaries
                for buffer_id, buffer_info in self.buffers.items():
                    if abs(part_info["position"] - buffer_info["body"].GetPos().x()) < 0.5:
                        if len(buffer_info["parts"]) < buffer_info["capacity"]:
                            buffer_info["parts"].append(part_info["id"])
                            part_info["current_station"] = buffer_id
                            part_info["state"] = "waiting"
                            break
                
                # Check if reached a machine
                for machine_id, machine_info in self.machines.items():
                    if abs(part_info["position"] - machine_info["body"].GetPos().x()) < 0.5:
                        if machine_info["state"] == "idle":
                            machine_info["state"] = "processing"
                            machine_info["processing_start"] = self.sim_time
                            part_info["current_station"] = machine_id
                            part_info["state"] = "processing"
                            # Log processing start
                            self.log_event(machine_id, "processing_start", 0.0, 0.0)
                            break
    
    def update_machine_states(self):
        # Update machine states based on availability and MTTR
        for machine_id, machine_info in self.machines.items():
            if machine_info["state"] == "processing":
                # Check if processing is complete
                processing_duration = self.sim_time - machine_info["processing_start"]
                if processing_duration >= machine_info["processing_time"]:
                    # Processing complete
                    machine_info["state"] = "idle"
                    machine_info["last_state_change"] = self.sim_time
                    
                    # Log processing end
                    self.log_event(machine_id, "processing_end", machine_info["processing_time"], 
                                 machine_info["processing_time"] * machine_info["power_working"] / 3600.0)
                    
                    # Move part to next buffer
                    for part_info in self.parts:
                        if part_info["current_station"] == machine_id and part_info["state"] == "processing":
                            part_info["state"] = "moving"
                            part_info["current_station"] = "B" + str(int(machine_id[1:])-1) if machine_id[1:] != "6" else "sink"
                            break
                            
            elif machine_info["state"] == "idle":
                # Check if machine needs to be repaired due to failure
                if self.sim_time - machine_info["last_state_change"] > machine_info["mttr"]:
                    machine_info["state"] = "idle"
            
            # Simulate machine failure based on availability
            if machine_info["state"] == "idle" and np.random.rand() > machine_info["availability"]:
                machine_info["state"] = "failed"
                machine_info["failure_end"] = self.sim_time + machine_info["mttr"]
                self.log_event(machine_id, "failure", 0.0, 0.0)
    
    def log_event(self, machine_id, reason_code, duration, energy):
        event_data = {
            "ts": datetime.now(),
            "machine_id": machine_id,
            "reason_code": reason_code,
            "duration_s": duration,
            "energy_kwh": energy
        }
        with self.data_lock:
            self.events_log.append(event_data)
    
    def log_sample(self, machine_id, tag, value):
        sample_data = {
            "ts": datetime.now(),
            "machine_id": machine_id,
            "tag": tag,
            "value": value
        }
        with self.data_lock:
            self.samples_log.append(sample_data)
    
    def log_machine_states(self):
        # Log current states of machines
        for machine_id, machine_info in self.machines.items():
            self.log_sample(machine_id, "processing_time_s", machine_info["processing_time"])
            self.log_sample(machine_id, "availability_pct", machine_info["availability"] * 100)
            self.log_sample(machine_id, "mttr_s", machine_info["mttr"])
            self.log_sample(machine_id, "power_working_kw", machine_info["power_working"])
            self.log_sample(machine_id, "power_idle_kw", machine_info["power_idle"])
    
    def run_simulation(self):
        # Start simulation
        print("Starting simulation...")
        start_time = time.time()
        
        # Create initial parts at regular intervals
        part_creation_count = 0
        next_part_time = 0.0
        
        # Main simulation loop
        while self.sim_time < self.end_time:
            # Create new parts at regular intervals
            if self.sim_time >= next_part_time:
                self.create_part(self.sim_time)
                part_creation_count += 1
                next_part_time += self.equipment["source"]["inter_arrival_time"]
            
            # Update simulation
            self.system.DoStepDynamics(self.time_step)
            self.sim_time += self.time_step
            
            # Update part positions
            self.update_part_positions()
            
            # Update machine states
            self.update_machine_states()
            
            # Log machine states periodically
            if int(self.sim_time) % 300 == 0:  # Every 5 minutes
                self.log_machine_states()
            
            # Print progress
            if int(self.sim_time) % 3600 == 0:  # Every hour
                elapsed = time.time() - start_time
                print(f"Simulation time: {self.sim_time:.0f}s ({self.sim_time/self.end_time*100:.1f}%) - Elapsed: {elapsed:.1f}s")
        
        # Final logging
        self.log_machine_states()
        print("Simulation completed.")
        print(f"Total parts created: {part_creation_count}")
        print(f"Total events logged: {len(self.events_log)}")
        print(f"Total samples logged: {len(self.samples_log)}")

def main():
    # Create simulation instance
    sim = ProductionLineSimulation()
    
    # Run simulation
    try:
        sim.run_simulation()
        
        # Example of how to log data to database (commented out for security)
        """
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            database="production_digital_twin",
           