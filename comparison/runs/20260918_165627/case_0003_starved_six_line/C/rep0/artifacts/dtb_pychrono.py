```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import math
import time
import csv
from datetime import datetime

# Simulation constants
SIMULATION_TIME = 3600  # 1 hour of simulation
TIME_STEP = 0.01        # Time step in seconds
GRAVITY = chrono.ChVectorD(0, -9.81, 0)

# Database logging setup
LOG_FILE = 'digital_twin_simulation_log.csv'
with open(LOG_FILE, 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'machine_id', 'status', 'process_time_s', 'power_kw', 'availability', 'mttr_s']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

class Machine:
    def __init__(self, machine_id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw):
        self.machine_id = machine_id
        self.process_time_s = process_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        self.is_running = False
        self.is_broken = False
        self.running_time = 0
        self.broken_time = 0
        self.start_process_time = 0
        self.total_power = 0
        self.last_log_time = 0

    def update_status(self, current_time):
        if self.is_broken:
            self.broken_time += TIME_STEP
            if self.broken_time >= self.mttr_s:
                self.is_broken = False
                self.broken_time = 0
                return "repaired"
        else:
            if np.random.rand() < (1 - self.availability) * TIME_STEP:
                self.is_broken = True
                self.broken_time = 0
                return "failed"
        return None

    def start_process(self, current_time):
        if not self.is_broken and not self.is_running:
            self.is_running = True
            self.start_process_time = current_time
            return True
        return False

    def finish_process(self, current_time):
        if self.is_running:
            self.is_running = False
            self.running_time += current_time - self.start_process_time
            return True
        return False

    def get_current_power(self):
        if self.is_running:
            return self.work_power_kw
        else:
            return self.idle_power_kw

    def log_data(self, current_time):
        if current_time - self.last_log_time >= 1:  # Log every second
            power_kw = self.get_current_power()
            status = "running" if self.is_running else ("broken" if self.is_broken else "idle")
            with open(LOG_FILE, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['timestamp', 'machine_id', 'status', 'process_time_s', 'power_kw', 'availability', 'mttr_s'])
                writer.writerow({
                    'timestamp': current_time,
                    'machine_id': self.machine_id,
                    'status': status,
                    'process_time_s': self.process_time_s,
                    'power_kw': power_kw,
                    'availability': self.availability,
                    'mttr_s': self.mttr_s
                })
            self.last_log_time = current_time

def create_machine_body(system, pos, machine_id):
    # Create a rigid body for the machine
    body = chrono.ChBody()
    body.SetPos(chrono.ChVectorD(pos[0], pos[1], pos[2]))
    body.SetMass(1000)
    body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    
    # Add a visualization shape
    visual_shape = chrono.ChVisualShapeBox(1, 1, 1)
    visual_shape.SetColor(chrono.ChColor(0.8, 0.2, 0.2))
    body.AddVisualShape(visual_shape)
    
    # Add collision shape
    collision_shape = chrono.ChCollisionModel()
    collision_shape.AddBox(1, 1, 1)
    body.SetCollide(True)
    body.SetCollisionModel(collision_shape)
    
    system.Add(body)
    return body

def main():
    # Initialize the Chrono system
    chrono.SetChronoDataPath('path/to/chrono/data')  # Update this path
    
    # Create the simulation system
    system = chrono.ChSystemNSC()
    system.Set_G_acc(GRAVITY)
    
    # Create the Irrlicht visualization (optional)
    vis = chronoirr.ChVisualSystemIrrlicht()
    vis.SetWindowSize(1024, 768)
    vis.SetWindowTitle("Digital Twin Simulation")
    vis.Initialize()
    vis.AddLogo()
    vis.AddSkyBox()
    vis.AddCamera(chrono.ChVectorD(5, 5, 5), chrono.ChVectorD(0, 0, 0))
    vis.AddTypicalLights()
    
    # Create ground
    ground = chrono.ChBody()
    ground.SetFixed(True)
    ground.SetPos(chrono.ChVectorD(0, -1, 0))
    ground_shape = chrono.ChVisualShapeBox(20, 1, 20)
    ground_shape.SetColor(chrono.ChColor(0.5, 0.5, 0.5))
    ground.AddVisualShape(ground_shape)
    system.Add(ground)
    
    # Create machines
    machines = {}
    machine_positions = [
        [0, 0, 0],
        [3, 0, 0],
        [6, 0, 0],
        [9, 0, 0],
        [12, 0, 0],
        [15, 0, 0]
    ]
    
    for i, machine_id in enumerate(["M1", "M2", "M3", "M4", "M5", "M6"]):
        machine_config = {
            "process_time_s": 200 + i*20,
            "availability": 0.97 - i*0.005,
            "mttr_s": 900 + i*100,
            "work_power_kw": 5.0 + i*0.5,
            "idle_power_kw": 0.5 + i*0.05
        }
        
        machines[machine_id] = Machine(
            machine_id=machine_id,
            process_time_s=machine_config["process_time_s"],
            availability=machine_config["availability"],
            mttr_s=machine_config["mttr_s"],
            work_power_kw=machine_config["work_power_kw"],
            idle_power_kw=machine_config["idle_power_kw"]
        )
        
        # Create physical representation
        create_machine_body(system, machine_positions[i], machine_id)
    
    # Simulation loop
    current_time = 0
    while current_time < SIMULATION_TIME:
        # Update machine statuses
        for machine_id, machine in machines.items():
            status_change = machine.update_status(current_time)
            if status_change == "failed":
                print(f"{machine_id} has failed at {current_time}s")
            elif status_change == "repaired":
                print(f"{machine_id} has been repaired at {current_time}s")
            
            # Simulate processing
            if machine.is_running and (current_time - machine.start_process_time) >= machine.process_time_s:
                machine.finish_process(current_time)
                print(f"{machine_id} completed process at {current_time}s")
                
                # Start new process with probability
                if np.random.rand() < 0.8:  # 80% chance to start next process
                    machine.start_process(current_time)
                    print(f"{machine_id} started new process at {current_time}s")
            
            # Start process randomly
            if not machine.is_running and not machine.is_broken:
                if np.random.rand() < 0.01:  # 1% chance per time step to start
                    machine.start_process(current_time)
                    print(f"{machine_id} started process at {current_time}s")
            
            # Log data
            machine.log_data(current_time)
        
        # Step the system
        system.DoStepDynamics(TIME_STEP)
        
        # Update visualization
        if vis.Run():
            vis.BeginScene()
            vis.Render()
            vis.EndScene()
        
        # Increment time
        current_time += TIME_STEP
        
        # Print progress
        if int(current_time) % 60 == 0:
            print(f"Simulated time: {current_time:.1f}s")
    
    # Final summary
    print("\n=== Simulation Summary ===")
    for machine_id, machine in machines.items():
        print(f"{machine_id}: Running time = {machine.running_time:.1f}s, "
              f"Total power = {machine.total_power:.1f}kWh")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred during simulation: {e}")
    finally:
        print("Simulation finished.")
```