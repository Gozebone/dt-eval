import os
import numpy as np
import pandas as pd
from datetime import datetime
import time

import pychrono as chrono
import pychrono.fea as fea
import pychrono.vehicle as vehicle
import pychrono.irrlicht as irr

class EquipmentSimulation:
    def __init__(self):
        # Initialize Chrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravity(chrono.ChVectorD(0, -9.81, 0))
        
        # Create materials
        self.material_steel = chrono.ChMaterialSurfaceNSC()
        self.material_steel.SetFriction(0.4)
        self.material_steel.SetRestitution(0.1)
        
        self.material_refractory = chrono.ChMaterialSurfaceNSC()
        self.material_refractory.SetFriction(0.3)
        self.material_refractory.SetRestitution(0.05)
        
        # Simulation parameters
        self.time_step = 0.001
        self.sim_time = 0.0
        self.total_parts = 0
        self.parts_processed = 0
        
        # Data storage
        self.process_data = []
        self.energy_data = []
        self.availability_data = []
        
        # Equipment list
        self.equipment = {}
        self.sensors = {}
        
        # Create simulation environment
        self.create_environment()
        
    def create_environment(self):
        # Create ground
        ground = chrono.ChBody()
        ground.SetBodyFixed(True)
        ground.SetPos(chrono.ChVectorD(0, -1, 0))
        ground.GetCollisionModel().ClearModel()
        ground.GetCollisionModel().AddBox(self.material_steel, 20, 1, 20)
        ground.GetCollisionModel().BuildModel()
        ground.SetCollide(True)
        self.system.Add(ground)
        
        # Create equipment
        self.create_equipment()
        
    def create_equipment(self):
        # Create M1 to M6 equipment
        positions = [
            chrono.ChVectorD(-8, 0, 0),  # M1
            chrono.ChVectorD(-6, 0, 0),  # M2
            chrono.ChVectorD(-4, 0, 0),  # M3
            chrono.ChVectorD(-2, 0, 0),  # M4
            chrono.ChVectorD(0, 0, 0),   # M5
            chrono.ChVectorD(2, 0, 0)    # M6
        ]
        
        for i, pos in enumerate(positions):
            equipment_name = f"M{i+1}"
            self.create_machine(equipment_name, pos)
            
    def create_machine(self, name, pos):
        # Create machine body
        machine = chrono.ChBody()
        machine.SetPos(pos)
        machine.SetMass(1000)
        machine.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
        machine.GetCollisionModel().ClearModel()
        machine.GetCollisionModel().AddBox(self.material_steel, 2, 1, 1)
        machine.GetCollisionModel().BuildModel()
        machine.SetCollide(True)
        machine.SetBodyFixed(False)
        
        # Add material properties
        machine.SetMaterialSurface(self.material_steel)
        
        # Add to system
        self.system.Add(machine)
        
        # Store reference
        self.equipment[name] = {
            'body': machine,
            'active': True,
            'process_time': 2.0 + np.random.uniform(-0.2, 0.2),  # Random process time
            'work_power': 50.0 + np.random.uniform(-5, 5),       # Random power
            'idle_power': 5.0 + np.random.uniform(-1, 1),        # Random idle power
            'last_start_time': 0.0,
            'total_active_time': 0.0,
            'total_idle_time': 0.0,
            'total_work_energy': 0.0,
            'total_idle_energy': 0.0
        }
        
        # Create sensors for this machine
        self.create_sensors(name)
        
    def create_sensors(self, machine_name):
        # Create sensors dictionary for each machine
        self.sensors[machine_name] = {
            'process_time_s': 0.0,
            'availability': 1.0,
            'MTTR': 0.0,
            'work_power_kw': self.equipment[machine_name]['work_power'],
            'idle_power_kw': self.equipment[machine_name]['idle_power'],
            'last_processed': 0.0
        }
        
    def start_process(self, machine_name):
        """Start processing a part on a machine"""
        if machine_name in self.equipment:
            self.equipment[machine_name]['active'] = True
            self.equipment[machine_name]['last_start_time'] = self.sim_time
            self.equipment[machine_name]['total_active_time'] += self.sim_time - self.equipment[machine_name]['last_start_time']
            
    def stop_process(self, machine_name):
        """Stop processing a part on a machine"""
        if machine_name in self.equipment:
            self.equipment[machine_name]['active'] = False
            self.equipment[machine_name]['total_idle_time'] += self.sim_time - self.equipment[machine_name]['last_start_time']
            self.parts_processed += 1
            
    def calculate_availability(self, machine_name):
        """Calculate availability of a machine"""
        if machine_name in self.equipment:
            total_time = self.sim_time
            if total_time > 0:
                active_time = self.equipment[machine_name]['total_active_time']
                return active_time / total_time
        return 1.0
        
    def calculate_energy_consumption(self, machine_name):
        """Calculate energy consumption for a machine"""
        if machine_name in self.equipment:
            # Calculate work energy
            work_energy = self.equipment[machine_name]['total_active_time'] * self.equipment[machine_name]['work_power']
            idle_energy = self.equipment[machine_name]['total_idle_time'] * self.equipment[machine_name]['idle_power']
            
            self.equipment[machine_name]['total_work_energy'] = work_energy
            self.equipment[machine_name]['total_idle_energy'] = idle_energy
            
            return work_energy + idle_energy
        return 0.0
        
    def log_process_data(self):
        """Log data for each machine"""
        for machine_name in self.equipment:
            # Update availability
            availability = self.calculate_availability(machine_name)
            
            # Calculate energy consumption
            total_energy = self.calculate_energy_consumption(machine_name)
            
            # Log process data
            process_record = {
                'timestamp': datetime.now(),
                'machine_name': machine_name,
                'process_time_s': self.equipment[machine_name]['process_time'],
                'availability': availability,
                'MTTR': 0.0,  # Not implemented but can be extended
                'work_power_kw': self.equipment[machine_name]['work_power'],
                'idle_power_kw': self.equipment[machine_name]['idle_power'],
                'energy_consumption_kwh': total_energy,
                'parts_processed': self.parts_processed
            }
            
            self.process_data.append(process_record)
            
    def log_energy_data(self):
        """Log energy consumption data"""
        energy_record = {
            'timestamp': datetime.now(),
            'sim_time': self.sim_time,
            'total_work_power_kw': sum([self.equipment[m]['work_power'] for m in self.equipment]),
            'total_idle_power_kw': sum([self.equipment[m]['idle_power'] for m in self.equipment]),
            'total_energy_kwh': sum([self.equipment[m]['total_work_energy'] + self.equipment[m]['total_idle_energy'] 
                                   for m in self.equipment])
        }
        self.energy_data.append(energy_record)
        
    def update_sensors(self):
        """Update all sensor values"""
        for machine_name in self.equipment:
            # Update sensors for this machine
            self.sensors[machine_name] = {
                'process_time_s': self.equipment[machine_name]['process_time'],
                'availability': self.calculate_availability(machine_name),
                'MTTR': 0.0,
                'work_power_kw': self.equipment[machine_name]['work_power'],
                'idle_power_kw': self.equipment[machine_name]['idle_power'],
                'last_processed': self.equipment[machine_name]['last_start_time']
            }
            
    def simulate(self, duration=60.0):
        """Run simulation for given duration"""
        print("Starting simulation...")
        
        # Simulation loop
        while self.sim_time < duration:
            # Step the simulation
            self.system.DoStepDynamics(self.time_step)
            self.sim_time += self.time_step
            
            # Log data every 0.5 seconds
            if int(self.sim_time * 2) % 1 == 0:  # Every 0.5 seconds
                self.update_sensors()
                self.log_energy_data()
                
            # Random part generation (simulating part flow)
            if np.random.rand() < 0.05:  # 5% chance per time step to create part
                self.total_parts += 1
                # Assign part to first machine
                self.start_process("M1")
                
                # Simulate processing through line
                for machine_num in range(1, 6):
                    machine_name = f"M{machine_num}"
                    # Simulate processing time
                    process_time = self.equipment[machine_name]['process_time']
                    time.sleep(process_time / 100)  # Simulate processing time
                    self.stop_process(machine_name)
                    
                    # Move to next machine
                    if machine_num < 6:
                        next_machine = f"M{machine_num + 1}"
                        self.start_process(next_machine)
                        
            # Log process data occasionally
            if self.sim_time % 2.0 < self.time_step:
                self.log_process_data()
                
        print("Simulation completed.")
        
    def save_data(self, output_dir="output"):
        """Save all data to CSV files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Save process data
        if self.process_data:
            df_process = pd.DataFrame(self.process_data)
            df_process.to_csv(os.path.join(output_dir, "process_data.csv"), index=False)
            
        # Save energy data
        if self.energy_data:
            df_energy = pd.DataFrame(self.energy_data)
            df_energy.to_csv(os.path.join(output_dir, "energy_data.csv"), index=False)
            
        print(f"Data saved to {output_dir}")
        
    def get_summary_metrics(self):
        """Calculate and return summary metrics"""
        if not self.process_data:
            return {}
            
        df = pd.DataFrame(self.process_data)
        
        # Calculate summary metrics
        summary = {
            'total_parts_processed': self.parts_processed,
            'average_process_time': df['process_time_s'].mean(),
            'average_availability': df['availability'].mean(),
            'total_energy_consumption': df['energy_consumption_kwh'].sum(),
            'average_work_power': df['work_power_kw'].mean(),
            'average_idle_power': df['idle_power_kw'].mean()
        }
        
        return summary

def main():
    # Create simulation instance
    simulation = EquipmentSimulation()
    
    # Run simulation for 60 seconds
    simulation.simulate(duration=60.0)
    
    # Save data
    simulation.save_data()
    
    # Print summary
    summary = simulation.get_summary_metrics()
    print("\nSummary Metrics:")
    for key, value in summary.items():
        print(f"{key}: {value:.2f}")
        
    # Clean up
    del simulation

if __name__ == "__main__":
    main()