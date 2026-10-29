```python
import pychrono as chrono
import pychrono.irrlicht as irr
import numpy as np
import time
import threading
import queue
from datetime import datetime
import json

# Simulation parameters
SIMULATION_TIME = 3600  # 1 hour of simulation
DT = 0.01  # Time step
GRAVITY = chrono.ChVectorD(0, -9.81, 0)

# Equipment data
equipment_data = {
    "M1": {
        "process_time_s": 150,
        "availability": 0.98,
        "mttr_s": 600,
        "work_power_kw": 4.0,
        "idle_power_kw": 0.4
    },
    "M2": {
        "process_time_s": 120,
        "availability": 0.97,
        "mttr_s": 900,
        "work_power_kw": 5.0,
        "idle_power_kw": 0.5
    },
    "M3": {
        "process_time_s": 180,
        "availability": 0.95,
        "mttr_s": 1200,
        "work_power_kw": 6.0,
        "idle_power_kw": 0.6
    },
    "M4": {
        "process_time_s": 120,
        "availability": 0.97,
        "mttr_s": 900,
        "work_power_kw": 5.0,
        "idle_power_kw": 0.5
    },
    "M5": {
        "process_time_s": 150,
        "availability": 0.98,
        "mttr_s": 600,
        "work_power_kw": 4.0,
        "idle_power_kw": 0.4
    }
}

# Buffer capacity
BUFFER_CAPACITY = 8

# Simulation data storage
class SimulationData:
    def __init__(self):
        self.machine_states = []
        self.buffer_levels = []
        self.energy_consumption = []
        self.production_metrics = {
            'wip': [],
            'throughput': [],
            'energy_per_part': []
        }
        self.time_points = []

# Sensor class
class MachineSensor:
    def __init__(self, machine_name, process_time, availability, mttr, work_power, idle_power):
        self.machine_name = machine_name
        self.process_time = process_time
        self.availability = availability
        self.mttr = mttr
        self.work_power = work_power
        self.idle_power = idle_power
        self.current_state = 'idle'
        self.process_start_time = 0
        self.total_energy = 0
        self.is_operational = True
        self.last_failure_time = 0
        self.total_operational_time = 0
        self.total_downtime = 0
        self.processed_parts = 0
        self.failure_count = 0

    def update_state(self, current_time, new_state):
        if new_state == 'working' and self.current_state == 'idle':
            self.process_start_time = current_time
        elif new_state == 'idle' and self.current_state == 'working':
            # Calculate processed parts
            process_duration = current_time - self.process_start_time
            if process_duration >= self.process_time:
                self.processed_parts += 1
            # Update energy consumption
            self.total_energy += self.work_power * (process_duration / 3600)  # kWh
        elif new_state == 'faulty' and self.current_state != 'faulty':
            self.failure_count += 1
            self.last_failure_time = current_time
            self.total_downtime += self.mttr
            self.is_operational = False
        elif new_state == 'idle' and self.current_state == 'faulty':
            self.is_operational = True
            self.total_operational_time += self.mttr
        self.current_state = new_state

    def get_power_consumption(self, current_time):
        if self.current_state == 'working':
            return self.work_power
        else:
            return self.idle_power

    def get_availability(self):
        if self.total_operational_time + self.total_downtime == 0:
            return 1.0
        return self.total_operational_time / (self.total_operational_time + self.total_downtime)

    def to_dict(self):
        return {
            'machine_name': self.machine_name,
            'state': self.current_state,
            'energy_consumption_kw': self.get_power_consumption(0),
            'availability': self.get_availability(),
            'processed_parts': self.processed_parts,
            'failure_count': self.failure_count
        }

# Buffer class
class Buffer:
    def __init__(self, name, capacity):
        self.name = name
        self.capacity = capacity
        self.items = []
        self.max_items = capacity

    def add_item(self):
        if len(self.items) < self.capacity:
            self.items.append(1)
            return True
        return False

    def remove_item(self):
        if self.items:
            self.items.pop()
            return True
        return False

    def get_level(self):
        return len(self.items)

    def to_dict(self):
        return {
            'buffer_name': self.name,
            'level': self.get_level(),
            'capacity': self.capacity
        }

# Main simulation class
class ProductionLineSimulation:
    def __init__(self):
        # Initialize the chrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravitationalAcceleration(GRAVITY)
        
        # Create simulation data store
        self.data = SimulationData()
        
        # Create equipment sensors
        self.machines = {}
        for name, params in equipment_data.items():
            self.machines[name] = MachineSensor(
                name,
                params['process_time_s'],
                params['availability'],
                params['mttr_s'],
                params['work_power_kw'],
                params['idle_power_kw']
            )
        
        # Create buffers
        self.buffers = []
        for i in range(5):  # B0 to B4
            self.buffers.append(Buffer(f"B{i}", BUFFER_CAPACITY))
        
        # Create part source
        self.part_counter = 0
        self.parts_processed = 0
        self.parts_in_system = 0
        self.last_part_arrival = 0
        self.part_arrival_interval = 100  # seconds between parts
        
        # Simulation state tracking
        self.current_time = 0
        self.running = True
        
        # Create a real-time data queue
        self.data_queue = queue.Queue()
        
        # Create a timer for periodic updates
        self.timer = threading.Timer(1.0, self.periodic_update)
        self.timer.start()

    def periodic_update(self):
        if not self.running:
            return
        # Update simulation data
        self.update_simulation_data()
        # Re-schedule the timer
        self.timer = threading.Timer(1.0, self.periodic_update)
        self.timer.start()

    def create_machine_body(self, name, position):
        # Create a simple machine body
        machine_body = chrono.ChBody()
        machine_body.SetPos(chrono.ChVectorD(*position))
        machine_body.SetMass(100)
        machine_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
        machine_body.SetBodyFixed(False)
        self.system.AddBody(machine_body)
        return machine_body

    def update_machine_states(self, current_time):
        # Update machine states based on current time
        for machine_name, machine in self.machines.items():
            # Simulate machine availability (random failures based on MTBF)
            if machine.is_operational:
                # Simulate machine working if it's time for a new process
                if machine.current_state == 'idle':
                    # Randomly decide if the machine should start processing
                    if np.random.random() < 0.01:  # 1% chance per second
                        machine.update_state(current_time, 'working')
                elif machine.current_state == 'working':
                    # Check if processing is complete
                    if current_time - machine.process_start_time >= machine.process_time:
                        machine.update_state(current_time, 'idle')
            else:
                # Check if machine is repaired
                if current_time - machine.last_failure_time >= machine.mttr:
                    machine.update_state(current_time, 'idle')

    def update_buffers(self, current_time):
        # Move parts between buffers based on processing state
        # This is a simplified model - in reality, you'd have more complex flow logic
        pass

    def update_simulation_data(self):
        # Store current data
        current_time = self.current_time
        timestamp = datetime.now().isoformat()
        
        # Update machine states
        machine_states = []
        for name, machine in self.machines.items():
            state = machine.to_dict()
            machine_states.append(state)
            # Store energy consumption
            self.data.energy_consumption.append({
                'timestamp': timestamp,
                'machine_name': name,
                'power_kw': machine.get_power_consumption(current_time),
                'energy_kwh': machine.total_energy
            })
        
        # Update buffer levels
        buffer_levels = []
        for buffer in self.buffers:
            level = buffer.to_dict()
            buffer_levels.append(level)
        
        # Update WIP
        wip = sum([b.get_level() for b in self.buffers])
        
        # Update throughput (parts processed per time unit)
        throughput = self.parts_processed
        
        # Update energy per part
        energy_per_part = 0
        if self.parts_processed > 0:
            total_energy = sum([m.total_energy for m in self.machines.values()])
            energy_per_part = total_energy / self.parts_processed
        
        # Store data
        self.data.machine_states.append({
            'timestamp': timestamp,
            'machines': machine_states
        })
        self.data.buffer_levels.append({
            'timestamp': timestamp,
            'buffers': buffer_levels
        })
        self.data.production_metrics['wip'].append({
            'timestamp': timestamp,
            'wip': wip
        })
        self.data.production_metrics['throughput'].append({
            'timestamp': timestamp,
            'throughput': throughput
        })
        self.data.production_metrics['energy_per_part'].append({
            'timestamp': timestamp,
            'energy_per_part': energy_per_part
        })
        self.data.time_points.append(timestamp)

    def run_simulation(self):
        self.current_time = 0
        print("Starting simulation...")
        
        # Initial update
        self.update_simulation_data()
        
        while self.current_time < SIMULATION_TIME and self.running:
            # Update simulation time
            self.current_time += DT
            
            # Update machine states
            self.update_machine_states(self.current_time)
            
            # Update buffers
            self.update_buffers(self.current_time)
            
            # Process part arrival
            if self.current_time - self.last_part_arrival > self.part_arrival_interval:
                # Add part to input buffer
                if self.buffers[0].add_item():
                    self.parts_in_system += 1
                    self.part_counter += 1
                    self.last_part_arrival = self.current_time
            
            # Process parts through machines
            # This is a simplified approach to simulate machine processing
            for i, machine in enumerate(self.machines.values()):
                # If this machine is working, check if part processing is complete
                if machine.current_state == 'working' and \
                   self.current_time - machine.process_start_time >= machine.process_time:
                    # Processing complete, move part to next buffer if possible
                    if i < len(self.buffers) - 1:
                        if self.buffers[i+1].add_item():
                            machine.update_state(self.current_time, 'idle')
                            self.parts_processed += 1
                    else:
                        # Part completed, remove from system
                        machine.update_state(self.current_time, 'idle')
                        self.parts_processed += 1
                        self.parts_in_system -= 1
            
            # Step the simulation
            self.system.DoStepDynamics(DT)
            
            # Add small delay to simulate real-time behavior
            time.sleep(DT * 0.01)
            
            # Print progress
            if int(self.current_time) % 60 == 0:
                print(f"Time: {int(self.current_time)}s")
                print(f"Parts processed: {self.parts_processed}")
                print(f"Active parts in system: {self.parts_in_system}")
        
        # Stop the periodic update
        self.running = False
        self.timer.cancel()
        
        # Final update
        self.update_simulation_data()
        
        print("Simulation completed.")
        self.print_summary()

    def print_summary(self):
        print("\n--- Simulation Summary ---")
        print(f"Total time simulated: {SIMULATION_TIME} seconds")
        print(f"Total parts processed: {self.parts_processed}")
        print(f"Average throughput: {self.parts_processed / SIMULATION_TIME * 3600:.2f} parts/hour")
        print(f"Total energy consumed: {sum([m.total_energy for m in self.machines.values()]):.2f} kWh")
        
        # Print machine availability
        for name, machine in self.machines.items():
            print(f"{name}: Availability = {machine.get_availability():.4f}, Failures = {machine.failure_count}")

# Run the simulation
if __name__ == "__main__":
    simulation = ProductionLineSimulation()
    try:
        simulation.run_simulation()
    except KeyboardInterrupt:
        print("Simulation interrupted by user")
        simulation.running = False
        simulation.timer.cancel()
    except Exception as e:
        print(f"An error occurred during simulation: {e}")
        simulation.running = False
        simulation.timer.cancel()
    
    # Save data to JSON
    try:
        with open('simulation_data.json', 'w') as f:
            json.dump({
                'machine_states': simulation.data.machine_states,
                'buffer_levels': simulation.data.buffer_levels,
               