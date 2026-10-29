```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import math
import csv
import os
from datetime import datetime

# Simulation constants
TIME_STEP = 0.01
SIMULATION_DURATION = 1000.0
LOG_INTERVAL = 1.0

class DigitalTwinSimulation:
    def __init__(self):
        # Initialize Chrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravitationalAcceleration(chrono.ChVectorD(0, -9.81, 0))
        
        # Create log files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"simulation_log_{timestamp}.csv"
        self.setup_log_files()
        
        # Equipment and process variables
        self.machines = {}
        self.parts = []
        self.process_queue = []
        self.simulation_time = 0.0
        
        # Sensor data storage
        self.sensor_data = []
        
        # Create terrain
        self.create_terrain()
        
        # Create machines (M1, M2, M3)
        self.create_machines()
        
        # Create parts generator
        self.create_parts_generator()
        
        # Setup visualization
        self.visualizer = None
        self.setup_visualization()

    def setup_log_files(self):
        """Setup CSV log files for different data types"""
        # Main part processing log
        with open(self.log_file, 'w', newline='') as csvfile:
            fieldnames = [
                'time', 'part_id', 'process_stage', 'status',
                'inter_arrival_s', 'process_time_s', 'availability',
                'mttr_s', 'work_power_kw', 'idle_power_kw'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    def create_terrain(self):
        """Create ground plane"""
        ground = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True)
        ground.SetPos(chrono.ChVectorD(0, -0.5, 0))
        ground.SetFixed(True)
        ground.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/concrete.jpg"))
        self.system.Add(ground)

    def create_machines(self):
        """Create machine models (M1, M2, M3)"""
        # Machine dimensions
        machine_length = 2.0
        machine_width = 1.0
        machine_height = 1.5
        
        # Create three machines
        for i, machine_name in enumerate(['M1', 'M2', 'M3']):
            # Create machine body
            machine_body = chrono.ChBodyEasyBox(
                machine_length, machine_height, machine_width,
                1000, True, True
            )
            
            # Position machines in line
            machine_body.SetPos(chrono.ChVectorD(i * 3.0, 0.5, 0))
            machine_body.SetFixed(True)
            
            # Add visual model
            machine_body.GetVisualModel().SetColor(chrono.ChColor(0.8, 0.2, 0.2))
            
            # Store machine reference
            self.machines[machine_name] = {
                'body': machine_body,
                'status': 'available',  # available, busy, broken
                'process_start_time': 0.0,
                'process_duration': 0.0,
                'total_operating_time': 0.0,
                'total_downtime': 0.0,
                'power_consumption': 0.0,
                'last_power_update': 0.0
            }
            
            self.system.Add(machine_body)

    def create_parts_generator(self):
        """Create part generator with inter-arrival time"""
        self.part_counter = 0
        self.inter_arrival_time = 5.0  # seconds between parts
        self.next_part_time = self.inter_arrival_time

    def generate_part(self):
        """Generate a new part at specified intervals"""
        if self.simulation_time >= self.next_part_time:
            self.part_counter += 1
            
            # Create part body
            part = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 100, True, True)
            part.SetPos(chrono.ChVectorD(-2.0, 1.0, 0))
            part.GetVisualModel().SetColor(chrono.ChColor(0.2, 0.2, 0.8))
            
            # Add to system
            self.system.Add(part)
            self.parts.append({
                'id': self.part_counter,
                'body': part,
                'position': 0,  # 0 = before M1, 1 = between M1-M2, 2 = between M2-M3, 3 = after M3
                'process_start_time': self.simulation_time,
                'status': 'waiting'  # waiting, processing, completed
            })
            
            # Schedule next part
            self.next_part_time += self.inter_arrival_time
            
            return True
        return False

    def update_machine_status(self, machine_name, status):
        """Update machine status"""
        if machine_name in self.machines:
            self.machines[machine_name]['status'] = status
            if status == 'broken':
                self.machines[machine_name]['start_broken_time'] = self.simulation_time
            elif status == 'available':
                if 'start_broken_time' in self.machines[machine_name]:
                    self.machines[machine_name]['total_downtime'] += (
                        self.simulation_time - self.machines[machine_name]['start_broken_time']
                    )

    def update_sensor_data(self):
        """Collect sensor data from all machines"""
        current_data = {
            'time': self.simulation_time,
            'part_id': 0,
            'process_stage': '',
            'status': ''
        }
        
        # Collect data from each machine
        for machine_name, machine_data in self.machines.items():
            # Availability calculation (simplified)
            total_time = self.simulation_time
            if total_time > 0:
                availability = (machine_data['total_operating_time'] / total_time) * 100
            else:
                availability = 100.0
                
            # Power consumption
            power_consumption = 0.0
            if machine_data['status'] == 'busy':
                power_consumption = 5.0  # kW during operation
            elif machine_data['status'] == 'available':
                power_consumption = 1.0  # kW idle
            
            # Add to sensor data
            self.sensor_data.append({
                'time': self.simulation_time,
                'machine': machine_name,
                'availability': availability,
                'process_time_s': machine_data['process_duration'],
                'work_power_kw': power_consumption,
                'idle_power_kw': 1.0 if machine_data['status'] == 'available' else 0.0,
                'mttr_s': machine_data['total_downtime'] if machine_data['status'] == 'broken' else 0.0,
                'inter_arrival_s': self.inter_arrival_time
            })

    def log_data(self):
        """Log data to CSV file"""
        with open(self.log_file, 'a', newline='') as csvfile:
            fieldnames = [
                'time', 'part_id', 'process_stage', 'status',
                'inter_arrival_s', 'process_time_s', 'availability',
                'mttr_s', 'work_power_kw', 'idle_power_kw'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write data for each part processed
            for part in self.parts:
                if part['status'] == 'completed':
                    writer.writerow({
                        'time': part['process_start_time'],
                        'part_id': part['id'],
                        'process_stage': 'completed',
                        'status': 'completed',
                        'inter_arrival_s': self.inter_arrival_time,
                        'process_time_s': 2.0,  # Fixed processing time for demonstration
                        'availability': 95.0,
                        'mttr_s': 0.0,
                        'work_power_kw': 5.0,
                        'idle_power_kw': 1.0
                    })

    def setup_visualization(self):
        """Setup visualization using Irrlicht"""
        try:
            self.visualizer = chronoirr.ChVisualSystemIrrlicht()
            self.visualizer.SetWindowSize(1024, 768)
            self.visualizer.SetWindowTitle('Digital Twin Simulation')
            self.visualizer.Initialize()
            self.visualizer.AddLogo()
            self.visualizer.AddSkyBox()
            self.visualizer.AddCamera(chrono.ChVectorD(5, 5, 5), chrono.ChVectorD(0, 1, 0))
            self.visualizer.AddTypicalLights()
            
            # Attach visualization to system
            self.visualizer.AttachSystem(self.system)
        except Exception as e:
            print(f"Warning: Could not initialize visualization: {e}")

    def run_simulation(self):
        """Run the main simulation loop"""
        print("Starting Digital Twin Simulation...")
        print(f"Simulation duration: {SIMULATION_DURATION} seconds")
        print(f"Time step: {TIME_STEP} seconds")
        
        step_count = 0
        last_log_time = 0.0
        
        while self.simulation_time < SIMULATION_DURATION:
            # Generate new parts
            self.generate_part()
            
            # Update machine states
            self.update_machine_states()
            
            # Step the simulation
            self.system.DoStepDynamics(TIME_STEP)
            self.simulation_time += TIME_STEP
            step_count += 1
            
            # Log data periodically
            if self.simulation_time - last_log_time >= LOG_INTERVAL:
                self.update_sensor_data()
                self.log_data()
                last_log_time = self.simulation_time
                
                # Print progress
                if step_count % 100 == 0:
                    print(f"Simulated time: {self.simulation_time:.1f}s")
        
        # Final logging
        self.update_sensor_data()
        self.log_data()
        print(f"Simulation completed. Data logged to {self.log_file}")
        
        # Cleanup
        self.cleanup()

    def update_machine_states(self):
        """Update machine states based on simulation"""
        for machine_name, machine_data in self.machines.items():
            # Simulate machine behavior
            if machine_data['status'] == 'available':
                # Check if there's work to do
                # In a real implementation, this would check queue or other conditions
                pass
            elif machine_data['status'] == 'busy':
                # Simulate processing time
                if self.simulation_time - machine_data['process_start_time'] >= 2.0:  # Process time
                    machine_data['status'] = 'available'
                    machine_data['total_operating_time'] += 2.0
                    machine_data['process_duration'] = 2.0
                    
            elif machine_data['status'] == 'broken':
                # Simulate repair time
                if self.simulation_time - machine_data.get('start_broken_time', 0) >= 10.0:  # MTTR
                    machine_data['status'] = 'available'
                    machine_data['total_downtime'] = 0.0

    def cleanup(self):
        """Cleanup resources"""
        print("Cleaning up simulation resources...")

def main():
    """Main function to run the digital twin simulation"""
    try:
        # Create and run simulation
        sim = DigitalTwinSimulation()
        sim.run_simulation()
        
        print("\nDigital Twin Simulation Completed Successfully!")
        print("Generated data files:")
        print(f"- {sim.log_file}")
        
    except Exception as e:
        print(f"Error running simulation: {e}")
        raise

if __name__ == "__main__":
    main()
```