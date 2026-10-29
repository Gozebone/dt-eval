```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import math
import csv
import os
from datetime import datetime
import time

# Initialize PyChrono system
chrono.SetChronoDataPath(os.environ.get('CHRONO_DATA_DIR', '/usr/local/share/chrono/data/'))
chrono.SetChronoDataPath('/usr/local/share/chrono/data/')
chrono.SetLogToConsole(True)

# Simulation parameters
SIMULATION_DURATION = 432000  # 5 days in seconds
TIME_STEP = 0.01              # Time step in seconds
GRAVITY = chrono.ChVectorD(0, -9.81, 0)
OUTPUT_FREQUENCY = 10         # Output every 10 seconds

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(GRAVITY)
system.SetSolverType(chrono.ChSolver.Type_BARZILAI_BORWEIN)
system.SetMaxItersSolverSpeed(100)
system.SetMaxItersSolverStab(100)
system.SetTol(1e-9)
system.SetTolForce(1e-9)

# Create ground plane
ground = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True)
ground.SetPos(chrono.ChVectorD(0, -0.5, 0))
ground.SetFixed(True)
ground.GetVisualModel().SetFaceColor(chrono.ChColor(0.5, 0.5, 0.5))
system.Add(ground)

# Machine class to represent each production machine
class ProductionMachine:
    def __init__(self, id, processing_time, availability, mttr, work_power, idle_power):
        self.id = id
        self.processing_time = processing_time
        self.availability = availability
        self.mttr = mttr
        self.work_power = work_power
        self.idle_power = idle_power
        
        # Machine state tracking
        self.is_operational = True
        self.is_processing = False
        self.last_failure_time = 0
        self.next_failure_time = 0
        self.failure_duration = 0
        
        # Create physical representation
        self.body = chrono.ChBodyEasyBox(2, 1, 2, 1000, True, True)
        self.body.SetPos(chrono.ChVectorD(0, 0, 0))
        self.body.SetFixed(False)
        self.body.GetVisualModel().SetFaceColor(chrono.ChColor(0.8, 0.2, 0.2))
        system.Add(self.body)
        
        # Create a simple visual representation of the machine
        self.visual_body = chrono.ChBodyEasyBox(1.8, 0.8, 1.8, 1000, True, True)
        self.visual_body.SetPos(chrono.ChVectorD(0, 0.4, 0))
        self.visual_body.SetFixed(True)
        self.visual_body.GetVisualModel().SetFaceColor(chrono.ChColor(0.7, 0.1, 0.1))
        self.body.AddAsset(self.visual_body)
        
        # Create a simple conveyor belt visualization
        self.belt_visual = chrono.ChBodyEasyBox(3, 0.05, 0.2, 1000, True, True)
        self.belt_visual.SetPos(chrono.ChVectorD(0, 0.1, 0))
        self.belt_visual.SetFixed(True)
        self.belt_visual.GetVisualModel().SetFaceColor(chrono.ChColor(0.2, 0.2, 0.2))
        self.body.AddAsset(self.belt_visual)
        
        # Initialize failure state
        self._initialize_failure_state()
    
    def _initialize_failure_state(self):
        """Initialize machine failure state"""
        if np.random.rand() < (1 - self.availability):
            self.is_operational = False
            self.last_failure_time = 0
            self.next_failure_time = self.mttr * np.random.exponential(1.0)
        else:
            self.is_operational = True
            self.last_failure_time = 0
            self.next_failure_time = 0
    
    def update_failure_state(self, current_time):
        """Update machine failure state based on availability and MTTR"""
        if not self.is_operational:
            # Check if repair is completed
            if current_time - self.last_failure_time >= self.mttr:
                self.is_operational = True
                self.last_failure_time = 0
                self.next_failure_time = 0
        else:
            # Check for new failure
            if np.random.rand() < (1 - self.availability) / (self.processing_time + self.mttr):
                self.is_operational = False
                self.last_failure_time = current_time
                self.next_failure_time = self.mttr
    
    def get_power_consumption(self):
        """Get power consumption based on operational state"""
        if self.is_operational and self.is_processing:
            return self.work_power
        else:
            return self.idle_power

# Buffer class to represent storage areas
class Buffer:
    def __init__(self, id, capacity, before_machine=None, after_machine=None):
        self.id = id
        self.capacity = capacity
        self.items = []
        self.before_machine = before_machine
        self.after_machine = after_machine
        
        # Create physical representation
        self.body = chrono.ChBodyEasyBox(1.5, 0.5, 1.5, 1000, True, True)
        self.body.SetPos(chrono.ChVectorD(0, 0, 0))
        self.body.SetFixed(True)
        self.body.GetVisualModel().SetFaceColor(chrono.ChColor(0.2, 0.6, 0.8))
        system.Add(self.body)
        
        # Create a simple visual representation of the buffer
        self.visual_body = chrono.ChBodyEasyBox(1.4, 0.4, 1.4, 1000, True, True)
        self.visual_body.SetPos(chrono.ChVectorD(0, 0.25, 0))
        self.visual_body.SetFixed(True)
        self.visual_body.GetVisualModel().SetFaceColor(chrono.ChColor(0.1, 0.5, 0.7))
        self.body.AddAsset(self.visual_body)
    
    def add_item(self, item):
        """Add item to buffer if space available"""
        if len(self.items) < self.capacity:
            self.items.append(item)
            return True
        return False
    
    def remove_item(self):
        """Remove item from buffer"""
        if self.items:
            return self.items.pop(0)
        return None

# Source and Sink classes
class Source:
    def __init__(self, inter_arrival_time):
        self.inter_arrival_time = inter_arrival_time
        self.last_arrival_time = 0
        self.item_count = 0
        
        # Create source body
        self.body = chrono.ChBodyEasyBox(1, 1, 1, 1000, True, True)
        self.body.SetPos(chrono.ChVectorD(-5, 0.5, 0))
        self.body.SetFixed(True)
        self.body.GetVisualModel().SetFaceColor(chrono.ChColor(0.1, 0.8, 0.1))
        system.Add(self.body)
        
        # Create visual representation
        self.visual_body = chrono.ChBodyEasyBox(0.8, 0.8, 0.8, 1000, True, True)
        self.visual_body.SetPos(chrono.ChVectorD(0, 0.4, 0))
        self.visual_body.SetFixed(True)
        self.visual_body.GetVisualModel().SetFaceColor(chrono.ChColor(0.0, 0.7, 0.0))
        self.body.AddAsset(self.visual_body)
    
    def should_generate_item(self, current_time):
        """Check if it's time to generate a new item"""
        if current_time - self.last_arrival_time >= self.inter_arrival_time:
            self.last_arrival_time = current_time
            self.item_count += 1
            return True
        return False

class Sink:
    def __init__(self):
        # Create sink body
        self.body = chrono.ChBodyEasyBox(1, 1, 1, 1000, True, True)
        self.body.SetPos(chrono.ChVectorD(5, 0.5, 0))
        self.body.SetFixed(True)
        self.body.GetVisualModel().SetFaceColor(chrono.ChColor(0.8, 0.1, 0.1))
        system.Add(self.body)
        
        # Create visual representation
        self.visual_body = chrono.ChBodyEasyBox(0.8, 0.8, 0.8, 1000, True, True)
        self.visual_body.SetPos(chrono.ChVectorD(0, 0.4, 0))
        self.visual_body.SetFixed(True)
        self.visual_body.GetVisualModel().SetFaceColor(chrono.ChColor(0.7, 0.0, 0.0))
        self.body.AddAsset(self.visual_body)
    
    def receive_item(self, item):
        """Receive an item from the production line"""
        pass

# Create all production line components
machines = {}
buffers = {}
source = None
sink = None

# Create machines
for machine_data in [
    {"id": "M1", "processing_time": 100, "availability": 0.9, "mttr": 2400, "work_power": 4.0, "idle_power": 0.4},
    {"id": "M2", "processing_time": 130, "availability": 0.92, "mttr": 3000, "work_power": 5.0, "idle_power": 0.5},
    {"id": "M3", "processing_time": 90, "availability": 0.88, "mttr": 3600, "work_power": 4.5, "idle_power": 0.45},
    {"id": "M4", "processing_time": 140, "availability": 0.91, "mttr": 4800, "work_power": 7.0, "idle_power": 0.7},
    {"id": "M5", "processing_time": 110, "availability": 0.93, "mttr": 2400, "work_power": 5.5, "idle_power": 0.55}
]:
    machines[machine_data["id"]] = ProductionMachine(
        machine_data["id"],
        machine_data["processing_time"],
        machine_data["availability"],
        machine_data["mttr"],
        machine_data["work_power"],
        machine_data["idle_power"]
    )

# Create buffers
buffer_configs = [
    {"id": "B0", "capacity": 6, "before": "source", "after": "M1"},
    {"id": "B1", "capacity": 3, "before": "M1", "after": "M2"},
    {"id": "B2", "capacity": 3, "before": "M2", "after": "M3"},
    {"id": "B3", "capacity": 3, "before": "M3", "after": "M4"},
    {"id": "B4", "capacity": 3, "before": "M4", "after": "sink"}
]

for buf_config in buffer_configs:
    buffers[buf_config["id"]] = Buffer(buf_config["id"], buf_config["capacity"])

# Create source and sink
source = Source(inter_arrival_time=150)
sink = Sink()

# Create item to be processed
item = chrono.ChBodyEasyBox(0.2, 0.2, 0.2, 100, True, True)
item.SetPos(chrono.ChVectorD(-4.5, 0.1, 0))
item.SetFixed(False)
item.GetVisualModel().SetFaceColor(chrono.ChColor(0.9, 0.9, 0.1))
system.Add(item)

# Position machines and buffers in sequence
machine_positions = [-2, -1, 0, 1, 2]
for i, (machine_id, machine) in enumerate(machines.items()):
    machine.body.SetPos(chrono.ChVectorD(machine_positions[i], 0.5, 0))

# Position buffers
buffer_positions = [-3.5, -2.5, -1.5, -0.5, 0.5]
for i, (buffer_id, buffer) in enumerate(buffers.items()):
    buffer.body.SetPos(chrono.ChVectorD(buffer_positions[i], 0.25, 0))

# Create a simple conveyor system to move items between machines
conveyor_bodies = []
for i in range(len(machine_positions) - 1):
    start_pos = machine_positions[i]
    end_pos = machine_positions[i+1]
    # Create a simple conveyor belt representation
    belt = chrono.ChBodyEasyBox(0.1, 0.05, 1.5, 1000, True, True)
    belt.SetPos(chrono.ChVectorD((start_pos + end_pos)/2, 0.1, 0))
    belt.SetFixed(True)
    belt.GetVisualModel().SetFaceColor(chrono.ChColor(0.3, 0.3, 0.3))
    system.Add(belt)
    conveyor_bodies.append(belt)

# Sensor data collection
sensor_data = []

def log_sensor_data(current_time):
    """Log sensor data to match database schema"""
    row = {
        '