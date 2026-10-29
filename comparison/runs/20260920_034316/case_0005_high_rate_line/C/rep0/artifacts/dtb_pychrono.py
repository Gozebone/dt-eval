importchrono
importmath
importjson
importdatetime
importrandom
fromcollections importdefaultdict
importpandas as pd

# Initialize Chrono system
chrono =chrono.ChSystemNSC()
chrono.SetGravitationalAcceleration(chrono.ChVectorD(0, -9.81, 0))

# Define materials
material_steel =chrono.ChMaterialSurfaceNSC()
material_steel.SetFriction(0.4)
material_steel.SetRestitution(0.1)

material_refractory =chrono.ChMaterialSurfaceNSC()
material_refractory.SetFriction(0.3)
material_refractory.SetRestitution(0.05)

# Create base body for simulation environment
ground =chrono.ChBody()
ground.SetFixed(True)
ground.GetCollisionModel().ClearModel()
ground.GetCollisionModel().AddBox(material_steel, 10, 0.1, 10)
ground.SetPos(chrono.ChVectorD(0, -0.05, 0))
chrono.AddBody(ground)

# Define machine parameters from JSON
machines_data = {
    "M1": {
        "avg_time_per_part_s": 59.99,
        "availability_%": 99.99,
        "mttr_s": 46.14,
        "energy_idle_kw": 0.3,
        "energy_working_kw": 3.0
    },
    "M2": {
        "avg_time_per_part_s": 80.28,
        "availability_%": 100.0,
        "mttr_s": 1.0,
        "energy_idle_kw": 0.45,
        "energy_working_kw": 4.98
    },
    "M3": {
        "avg_time_per_part_s": 70.16,
        "availability_%": 99.88,
        "mttr_s": 272.07,
        "energy_idle_kw": 0.42,
        "energy_working_kw": 4.49
    },
    "M4": {
        "avg_time_per_part_s": 75.03,
        "availability_%": 100.0,
        "mttr_s": 1.0,
        "energy_idle_kw": 0.34,
        "energy_working_kw": 4.0
    }
}

buffers_data = {
    "B0": {
        "capacity": 25
    },
    "B1": {
        "capacity": 10
    },
    "B2": {
        "capacity": 10
    },
    "B3": {
        "capacity": 10
    }
}

# Define equipment as bodies
equipment_bodies = {}
for machine_id in ["source", "M1", "M2", "M3", "M4", "B0", "B1", "B2", "B3"]:
    body =chrono.ChBody()
    body.SetPos(chrono.ChVectorD(0, 0, 0))
    body.SetFixed(False)
    body.GetCollisionModel().ClearModel()
    body.GetCollisionModel().AddBox(material_steel, 1, 1, 1)
    body.SetMass(100)
    body.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
    chrono.AddBody(body)
    equipment_bodies[machine_id] = body

# Create source with part generation
classPartGenerator:
    def __init__(self, system, interval_s=45):
        self.system = system
        self.interval_s = interval_s
        self.last_generation_time = 0
        self.part_count = 0
    
    def update(self, current_time):
        if current_time - self.last_generation_time >= self.interval_s:
            self.generate_part()
            self.last_generation_time = current_time
    
    def generate_part(self):
        self.part_count += 1
        part =chrono.ChBody()
        part.SetPos(chrono.ChVectorD(0, 2, 0))
        part.SetFixed(False)
        part.GetCollisionModel().ClearModel()
        part.GetCollisionModel().AddBox(material_refractory, 0.5, 0.5, 0.5)
        part.SetMass(5)
        part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
        self.system.AddBody(part)

# Create source generator
source_generator =PartGenerator(chrono, 45)

# Create sensors for each machine
classMachineSensor:
    def __init__(self, machine_id, machine_data, start_time):
        self.machine_id = machine_id
        self.machine_data = machine_data
        self.start_time = start_time
        self.status = "IDLE"
        self.last_status_change = start_time
        self.processing_start_time = None
        self.processed_parts = 0
        self.energy_consumed = 0
        self.maintenance_events = []
        self.failure_times = []
        self.success_times = []
    
    def update(self, current_time, is_working):
        if not is_working:
            if self.status != "FAILURE":
                self.status = "FAILURE"
                self.last_status_change = current_time
                self.failure_times.append(current_time)
                self.log_event(current_time, "FAILURE", 0, 0)
        else:
            if self.status == "FAILURE":
                self.status = "IDLE"
                self.last_status_change = current_time
                # Simulate MTTR
                mttr = self.machine_data["mttr_s"]
                # Log maintenance event
                self.log_event(current_time, "MAINTENANCE", mttr, 0)
                self.maintenance_events.append(current_time)
            elif self.status == "IDLE" and self.processing_start_time is None:
                self.status = "PROCESSING"
                self.processing_start_time = current_time
            elif self.status == "PROCESSING":
                processing_time = current_time - self.processing_start_time
                expected_time = self.machine_data["avg_time_per_part_s"]
                if processing_time >= expected_time:
                    self.status = "IDLE"
                    self.processing_start_time = None
                    self.processed_parts += 1
                    self.success_times.append(current_time)
                    # Calculate energy consumed
                    energy_per_part = self.machine_data["energy_working_kw"] * expected_time / 3600
                    self.energy_consumed += energy_per_part
                    self.log_event(current_time, "SUCCESS", expected_time, energy_per_part)
    
    def log_event(self, ts, reason_code, duration_s, energy_kwh):
        print(f"Event: Machine={self.machine_id}, Time={ts}, Reason={reason_code}, Duration={duration_s}, Energy={energy_kwh}")

# Create sensors for machines
machine_sensors = {}
for machine_id, data in machines_data.items():
    machine_sensors[machine_id] = MachineSensor(machine_id, data, 0)

# Create buffer sensors
classBufferSensor:
    def __init__(self, buffer_id, capacity):
        self.buffer_id = buffer_id
        self.capacity = capacity
        self.current_parts = 0
        self.part_inflow = 0
        self.part_outflow = 0
    
    def update(self, current_time):
        pass

buffer_sensors = {}
for buffer_id, data in buffers_data.items():
    buffer_sensors[buffer_id] = BufferSensor(buffer_id, data["capacity"])

# Create sampling system
classSampleLogger:
    def __init__(self):
        self.samples = []
    
    def log_sample(self, ts, machine_id, tag, value):
        self.samples.append({
            "ts": ts,
            "machine_id": machine_id,
            "tag": tag,
            "value": value
        })
    
    def get_samples(self):
        return self.samples

sample_logger = SampleLogger()

# Simulation parameters
simulation_duration = 432000  # 5 days in seconds
time_step = 0.01
current_time = 0

# Initialize variables for logging
events = []
samples = []

# Main simulation loop
while current_time < simulation_duration:
    # Step the system
    chrono.DoStepDynamics(time_step)
    
    # Update source generator
    source_generator.update(current_time)
    
    # Update machine sensors
    for machine_id, sensor in machine_sensors.items():
        # Simulate availability (check if machine should be working)
        availability = machines_data[machine_id]["availability_%"] / 100.0
        is_working = random.random() < availability
        sensor.update(current_time, is_working)
        
        # Log samples
        sample_logger.log_sample(current_time, machine_id, "avg_time_per_part", machines_data[machine_id]["avg_time_per_part_s"])
        sample_logger.log_sample(current_time, machine_id, "availability", machines_data[machine_id]["availability_%"])
        sample_logger.log_sample(current_time, machine_id, "mttr", machines_data[machine_id]["mttr_s"])
        sample_logger.log_sample(current_time, machine_id, "energy_idle", machines_data[machine_id]["energy_idle_kw"])
        sample_logger.log_sample(current_time, machine_id, "energy_working", machines_data[machine_id]["energy_working_kw"])
    
    # Update buffer sensors
    for buffer_id, sensor in buffer_sensors.items():
        sensor.update(current_time)
    
    # Increment time
    current_time += time_step

# Log final results
for machine_id, sensor in machine_sensors.items():
    print(f"Machine {machine_id}: Processed {sensor.processed_parts} parts, Energy consumed {sensor.energy_consumed} kWh")
    print(f"  - Failures: {len(sensor.failure_times)}")
    print(f"  - Maintenance events: {len(sensor.maintenance_events)}")

# Output results to CSV for database ingestion
df_events = pd.DataFrame(events)
df_samples = pd.DataFrame(samples)

# Save to CSV files for database import
df_events.to_csv("events.csv", index=False)
df_samples.to_csv("samples.csv", index=False)

print("Simulation completed. Data saved to events.csv and samples.csv")