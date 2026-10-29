```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fea as fea
import math
import json
import time
from datetime import datetime, timezone
import sqlite3

# Initialize PyChrono system
sys = chrono.ChSystemNSC()
sys.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

# Create terrain
terrain = chrono.ChBody()
terrain.SetBodyFixed(True)
terrain.SetPos(chrono.ChVectorD(0, -1, 0))
terrain.GetCollisionModel().ClearModel()
terrain.GetCollisionModel().AddBox(50, 1, 50)
terrain.SetMaterialSurface(steel_mat)
sys.Add(terrain)

# Create sources and buffers
class ProductionComponent:
    def __init__(self, component_id, component_type, **kwargs):
        self.id = component_id
        self.type = component_type
        self.params = kwargs
        self.body = None
        self.sensors = {}
        self.state = "idle"
        self.power = 0.0
        self.energy = 0.0
        self.start_time = 0.0
        self.log_data = []
        self.processing_start = 0.0
        self.processing_time = kwargs.get('processing_time_s', 60)
        self.availability = kwargs.get('availability_pct', 99.5) / 100
        self.mttr = kwargs.get('mttr_s', 300)
        self.power_working = kwargs.get('power_working_kw', 3.0)
        self.power_idle = kwargs.get('power_idle_kw', 0.3)
        self.capacity = kwargs.get('capacity', 25)
        self.inter_arrival = kwargs.get('inter_arrival_s', 45)
        
        # For M1-M4 machines, track processing state
        if component_type == "machine":
            self.working = False
            self.failure_time = 0.0
            self.next_failure_time = 0.0
            self.failure_count = 0
            
    def setup_body(self, sys, pos):
        """Create physical body for this component"""
        if self.type == "machine":
            # Create machine body
            self.body = chrono.ChBody()
            self.body.SetPos(pos)
            self.body.SetMass(100)
            self.body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
            self.body.GetCollisionModel().ClearModel()
            self.body.GetCollisionModel().AddBox(1, 1, 1)
            self.body.SetMaterialSurface(steel_mat)
            sys.Add(self.body)
            
        elif self.type == "buffer":
            # Create buffer body (simple box)
            self.body = chrono.ChBody()
            self.body.SetPos(pos)
            self.body.SetMass(10)
            self.body.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
            self.body.GetCollisionModel().ClearModel()
            self.body.GetCollisionModel().AddBox(1, 0.5, 1)
            self.body.SetMaterialSurface(steel_mat)
            sys.Add(self.body)
            
    def set_sensor(self, sensor_name, sensor_func):
        """Add sensor to component"""
        self.sensors[sensor_name] = sensor_func
        
    def get_sensor_value(self, sensor_name):
        """Get current sensor value"""
        if sensor_name in self.sensors:
            return self.sensors[sensor_name](self)
        return 0.0
        
    def check_failure(self, current_time):
        """Check if machine fails based on availability"""
        if self.type != "machine":
            return False
            
        if not self.working:
            return False
            
        # Check if it's time for failure
        if current_time >= self.next_failure_time:
            # Machine fails
            self.working = False
            self.failure_time = current_time
            self.failure_count += 1
            
            # Schedule next failure after MTTR
            self.next_failure_time = current_time + self.mttr
            return True
        return False
        
    def reset_failure(self, current_time):
        """Reset machine after failure"""
        if self.type != "machine":
            return
        if not self.working and current_time >= self.next_failure_time:
            self.working = True
            self.next_failure_time = current_time + (1.0 / self.availability) * 3600
            return True
        return False

# Create components
components = {}
# Create source
source = ProductionComponent("source", "source", inter_arrival_s=45)
components["source"] = source

# Create machines
machines = ["M1", "M2", "M3", "M4"]
machine_params = [
    {"id": "M1", "processing_time_s": 60, "availability_pct": 99.95, "mttr_s": 300, "power_working_kw": 3.0, "power_idle_kw": 0.3},
    {"id": "M2", "processing_time_s": 80, "availability_pct": 99.0, "mttr_s": 600, "power_working_kw": 5.0, "power_idle_kw": 0.5},
    {"id": "M3", "processing_time_s": 70, "availability_pct": 99.0, "mttr_s": 600, "power_working_kw": 4.5, "power_idle_kw": 0.45},
    {"id": "M4", "processing_time_s": 75, "availability_pct": 99.95, "mttr_s": 300, "power_working_kw": 4.0, "power_idle_kw": 0.4}
]

for i, m_params in enumerate(machine_params):
    machine = ProductionComponent(machines[i], "machine", **m_params)
    components[machines[i]] = machine

# Create buffers
buffers = ["B0", "B1", "B2", "B3"]
buffer_params = [
    {"id": "B0", "capacity": 25, "before": "source", "after": "M1"},
    {"id": "B1", "capacity": 10, "before": "M1", "after": "M2"},
    {"id": "B2", "capacity": 10, "before": "M2", "after": "M3"},
    {"id": "B3", "capacity": 10, "before": "M3", "after": "M4"}
]

for i, b_params in enumerate(buffer_params):
    buffer = ProductionComponent(buffers[i], "buffer", **b_params)
    components[buffers[i]] = buffer

# Setup positions for components
positions = {
    "source": chrono.ChVectorD(0, 0, 0),
    "M1": chrono.ChVectorD(3, 0, 0),
    "M2": chrono.ChVectorD(6, 0, 0),
    "M3": chrono.ChVectorD(9, 0, 0),
    "M4": chrono.ChVectorD(12, 0, 0),
    "B0": chrono.ChVectorD(1.5, 0, -1),
    "B1": chrono.ChVectorD(4.5, 0, -1),
    "B2": chrono.ChVectorD(7.5, 0, -1),
    "B3": chrono.ChVectorD(10.5, 0, -1)
}

# Initialize components in 3D space
for component_id, component in components.items():
    pos = positions.get(component_id, chrono.ChVectorD(0, 0, 0))
    component.setup_body(sys, pos)

# Setup sensors
for component_id, component in components.items():
    if component.type == "machine":
        # Process time sensor
        component.set_sensor("process_time_s", lambda x: x.processing_time)
        # Availability sensor
        component.set_sensor("availability", lambda x: x.availability)
        # MTTR sensor
        component.set_sensor("mttr_s", lambda x: x.mttr)
        # Working power sensor
        component.set_sensor("work_power_kw", lambda x: x.power_working)
        # Idle power sensor
        component.set_sensor("idle_power_kw", lambda x: x.power_idle)
        # Capacity sensor
        component.set_sensor("capacity", lambda x: x.capacity)
        # Inter-arrival sensor
        component.set_sensor("inter_arrival_s", lambda x: x.inter_arrival)
        
    elif component.type == "buffer":
        component.set_sensor("capacity", lambda x: x.capacity)
        component.set_sensor("before", lambda x: x.params.get("before", ""))
        component.set_sensor("after", lambda x: x.params.get("after", ""))

# Simulation parameters
total_simulation_time = 432000  # 5 days in seconds
dt = 0.1  # time step
current_time = 0.0
last_source_event = 0.0
items_produced = 0
items_processed = 0
total_energy = 0.0
time_step_count = 0

# Create a sample logger that mimics database logging
class SampleLogger:
    def __init__(self):
        self.samples = []
        self.events = []
        self.written_samples = []
        self.written_events = []
        
    def log_sample(self, ts, machine_id, tag, value):
        self.samples.append({
            "ts": ts,
            "machine_id": machine_id,
            "tag": tag,
            "value": value
        })
        
    def log_event(self, ts, machine_id, reason_code, duration_s, energy_kwh):
        self.events.append({
            "ts": ts,
            "machine_id": machine_id,
            "reason_code": reason_code,
            "duration_s": duration_s,
            "energy_kwh": energy_kwh
        })
        
    def flush_samples(self):
        # This would typically write to a database
        self.written_samples.extend(self.samples)
        self.samples.clear()
        
    def flush_events(self):
        # This would typically write to a database
        self.written_events.extend(self.events)
        self.events.clear()

logger = SampleLogger()

# Simulation loop
print("Starting simulation...")
start_time = time.time()

while current_time < total_simulation_time:
    # Step the system
    sys.DoStepDynamics(dt)
    time_step_count += 1
    current_time += dt
    
    if current_time - last_source_event >= 45:
        # Add new item to the production line
        last_source_event = current_time
        items_produced += 1
        
        # Create item at source position
        item = chrono.ChBody()
        item.SetPos(chrono.ChVectorD(0, 0.5, 0))
        item.SetMass(1)
        item.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
        item.GetCollisionModel().ClearModel()
        item.GetCollisionModel().AddBox(0.2, 0.2, 0.2)
        item.SetMaterialSurface(steel_mat)
        sys.Add(item)
        
        # Make item move towards M1
        item.SetBodyFixed(False)
        item.SetPos(chrono.ChVectorD(0, 0.5, 0))
    
    # Update each machine state
    for machine_id in machines:
        machine = components[machine_id]
        if machine.type == "machine":
            # Check for failures
            if machine.check_failure(current_time):
                # Log failure event
                logger.log_event(
                    current_time,
                    machine_id,
                    "FAILURE",
                    machine.mttr,
                    0.0
                )
                
            # Reset failure if needed
            machine.reset_failure(current_time)
            
            # Update power consumption
            if machine.working:
                machine.power = machine.power_working
                # Calculate energy consumption
                machine.energy += machine.power_working * dt / 3600.0
                total_energy += machine.power_working * dt / 3600.0
            else:
                machine.power = machine.power_idle
                total_energy += machine.power_idle * dt / 3600.0
                
            # Log sensor data
            if current_time % 10.0 < dt:  # Log every 10 seconds
                # Process time
                logger.log_sample(current_time, machine_id, "process_time_s", machine.processing_time)
                # Availability
                logger.log_sample(current_time, machine_id, "availability", machine.availability)
                # MTTR
                logger.log_sample(current_time, machine_id, "mttr_s", machine.mttr)
                # Work power
                logger.log_sample(current_time, machine_id, "work_power_kw", machine.power_working)
                # Idle power
                logger.log_sample(current_time, machine_id, "idle_power_kw", machine.power_idle)
                # Capacity
                logger.log_sample(current_time, machine_id, "capacity", machine.capacity)
                # Inter arrival
                logger.log_sample(current_time, machine_id, "inter_arrival_s", machine.inter_arrival)
    
    # Log buffer states
    for buffer_id in buffers:
        buffer = components[buffer_id]
        if buffer.type == "buffer":
            # Buffer capacity
            logger.log_sample(current_time, buffer_id, "capacity", buffer.capacity)
    
    # Periodically flush logs to simulate database writes
    if time_step_count % 10 == 0:
        logger.flush_samples()
        logger.flush_events()
    
    # Print progress
    if current_time % 1000 == 0:
