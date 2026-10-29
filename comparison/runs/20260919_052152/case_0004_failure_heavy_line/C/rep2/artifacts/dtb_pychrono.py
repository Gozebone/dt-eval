```python
import pychrono as chrono
import pychrono.irrlicht as irr
import numpy as np
import time
import json
from datetime import datetime, timezone
import sqlite3

# Initialize PyChrono system
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../data/")

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.4)
steel_mat.SetDampingF(0.2)
steel_mat.SetCompliance(0.0)
steel_mat.SetComplianceT(0.0)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetDampingF(0.1)
refractory_mat.SetCompliance(0.0)
refractory_mat.SetComplianceT(0.0)

# Create base floor
floor = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True)
floor.SetPos(chrono.ChVectorD(0, -0.5, 0))
floor.SetBodyFixed(True)
floor.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/concrete.jpg"))
system.Add(floor)

# Create furnace (M1)
furnace = chrono.ChBodyEasyBox(4, 2, 4, 3000, True, True)
furnace.SetPos(chrono.ChVectorD(0, 1, 0))
furnace.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/steel.jpg"))
system.Add(furnace)

# Create hot rolling mill (M2)
rolling_mill = chrono.ChBodyEasyBox(6, 2, 4, 2500, True, True)
rolling_mill.SetPos(chrono.ChVectorD(10, 1, 0))
rolling_mill.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/steel.jpg"))
system.Add(rolling_mill)

# Create cold rolling mill (M3)
cold_rolling = chrono.ChBodyEasyBox(6, 2, 4, 2500, True, True)
cold_rolling.SetPos(chrono.ChVectorD(20, 1, 0))
cold_rolling.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/steel.jpg"))
system.Add(cold_rolling)

# Create conveyor belts between machines
# Buffer B0
buffer_b0 = chrono.ChBodyEasyBox(5, 0.2, 1, 1000, True, True)
buffer_b0.SetPos(chrono.ChVectorD(5, 0.1, 0))
buffer_b0.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/concrete.jpg"))
system.Add(buffer_b0)

# Create sensors for temperature, pressure, humidity
class Sensor:
    def __init__(self, name, machine_id, system):
        self.name = name
        self.machine_id = machine_id
        self.system = system
        self.data = []
        self.last_update = time.time()
        
    def read(self):
        # In a real simulation this would read from the actual physical system
        # For this example we'll simulate readings
        timestamp = datetime.now(timezone.utc)
        
        if self.name == 'temperature':
            return np.random.normal(1200, 50)  # Temperature in degrees Celsius
        elif self.name == 'pressure':
            return np.random.normal(10, 2)  # Pressure in bar
        elif self.name == 'humidity':
            return np.random.normal(40, 10)  # Humidity in percentage
        
    def log(self):
        value = self.read()
        sample_data = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'machine_id': self.machine_id,
            'tag': self.name,
            'value': value
        }
        
        # Simulate database insert
        print(f"Sample logged: {sample_data}")
        self.data.append(sample_data)
        return sample_data

# Create sensors for each machine
sensors = []
sensors.append(Sensor('temperature', 'M1', system))
sensors.append(Sensor('pressure', 'M1', system))
sensors.append(Sensor('humidity', 'M1', system))
sensors.append(Sensor('temperature', 'M2', system))
sensors.append(Sensor('pressure', 'M2', system))
sensors.append(Sensor('humidity', 'M2', system))
sensors.append(Sensor('temperature', 'M3', system))
sensors.append(Sensor('humidity', 'M3', system))

# Create a simple event logger
class EventLogger:
    def __init__(self):
        self.events = []
        
    def log_event(self, machine_id, reason_code, duration_s, energy_kwh):
        event_data = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'machine_id': machine_id,
            'reason_code': reason_code,
            'duration_s': duration_s,
            'energy_kwh': energy_kwh
        }
        
        # Simulate database insert
        print(f"Event logged: {event_data}")
        self.events.append(event_data)
        return event_data

event_logger = EventLogger()

# Create a simple machine status tracker
class MachineStatus:
    def __init__(self, machine_id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw):
        self.machine_id = machine_id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.is_working = False
        self.working_time = 0
        self.last_start_time = 0
        self.current_energy_kwh = 0
        
    def update_status(self, time_step):
        if self.is_working:
            self.working_time += time_step
            # Simulate energy consumption
            self.current_energy_kwh += (self.power_working_kw * time_step) / 3600  # Convert to kWh
        else:
            # Simulate idle power consumption
            self.current_energy_kwh += (self.power_idle_kw * time_step) / 3600  # Convert to kWh

# Create machine status trackers
machines = [
    MachineStatus('M1', 600, 95, 300, 100, 20),
    MachineStatus('M2', 450, 90, 250, 80, 15),
    MachineStatus('M3', 300, 98, 150, 60, 10)
]

# Simulate simulation loop
def run_simulation():
    # Simulation parameters
    time_step = 0.01  # 10ms time step
    simulation_time = 0
    log_interval = 5 * 60  # Log every 5 minutes = 300 seconds
    last_log_time = 0
    
    print("Starting simulation...")
    
    try:
        while simulation_time < 3600:  # Run for 1 hour
            
            # Update machine statuses
            for machine in machines:
                machine.update_status(time_step)
            
            # Log sensor data every log_interval seconds
            if simulation_time - last_log_time >= log_interval:
                for sensor in sensors:
                    sensor.log()
                last_log_time = simulation_time
            
            # Simulate machine events
            if simulation_time % 1800 < time_step:  # Every 30 minutes
                for machine in machines:
                    # Simulate occasional events
                    if np.random.random() < 0.05:  # 5% chance of event
                        reason = np.random.choice(['maintenance', 'failure', 'quality_issue'])
                        duration = np.random.normal(300, 100)  # 5 minutes average
                        energy = np.random.normal(10, 2)  # 10 kWh average
                        event_logger.log_event(machine.machine_id, reason, duration, energy)
            
            # Step the simulation
            system.DoStepDynamics(time_step)
            simulation_time += time_step
            
            # Print status periodically
            if simulation_time % 300 < time_step:  # Every 5 minutes
                print(f"Simulation time: {simulation_time:.1f}s")
                
    except KeyboardInterrupt:
        print("Simulation interrupted by user.")
    except Exception as e:
        print(f"An error occurred during simulation: {e}")
    finally:
        print("Simulation completed.")

# Run the simulation
if __name__ == "__main__":
    run_simulation()
    
    # Final summary
    print("\n=== Simulation Summary ===")
    for i, machine in enumerate(machines):
        print(f"Machine {machine.machine_id}:")
        print(f"  Working time: {machine.working_time:.1f}s")
        print(f"  Energy consumed: {machine.current_energy_kwh:.2f} kWh")
        
    print("\n=== Sensor Data Records ===")
    for sensor in sensors:
        print(f"{sensor.name} readings: {len(sensor.data)} records")
        
    print("\n=== Events Recorded ===")
    for event in event_logger.events:
        print(f"Event at {event['ts']} on machine {event['machine_id']}: {event['reason_code']}")
```
