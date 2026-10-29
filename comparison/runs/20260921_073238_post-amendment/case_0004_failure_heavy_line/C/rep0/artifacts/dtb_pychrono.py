import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import json
import time
import sqlite3
from datetime import datetime, timedelta
import threading
import queue

class ProductionLineSimulation:
    def __init__(self):
        # Initialize PyChrono
        self.system = chrono.ChSystemNSC()
        self.system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))
        
        # Simulation parameters
        self.simulation_time = 0.0
        self.end_time = 432000.0  # 5 days in seconds
        self.time_step = 0.01
        self.log_interval = 1.0
        
        # Data collection
        self.machine_data = {}
        self.buffer_data = {}
        self.event_log = []
        self.sample_log = []
        
        # Initialize database connection
        self.conn = sqlite3.connect(':memory:')
        self.setup_database()
        
        # Machine and buffer definitions
        self.machines = {
            'M1': {'processing_time': 100, 'availability': 0.9, 'mttr': 2400, 'power_working': 4.0, 'power_idle': 0.4},
            'M2': {'processing_time': 130, 'availability': 0.92, 'mttr': 3000, 'power_working': 5.0, 'power_idle': 0.5},
            'M3': {'processing_time': 90, 'availability': 0.88, 'mttr': 3600, 'power_working': 4.5, 'power_idle': 0.45},
            'M4': {'processing_time': 140, 'availability': 0.91, 'mttr': 4800, 'power_working': 7.0, 'power_idle': 0.7},
            'M5': {'processing_time': 110, 'availability': 0.93, 'mttr': 2400, 'power_working': 5.5, 'power_idle': 0.55}
        }
        
        self.buffers = {
            'B0': {'capacity': 6},
            'B1': {'capacity': 3},
            'B2': {'capacity': 3},
            'B3': {'capacity': 3},
            'B4': {'capacity': 3}
        }
        
        # Create simulation components
        self.create_environment()
        self.create_machines()
        self.create_buffers()
        self.create_production_line()
        
        # Logging
        self.last_log_time = 0.0
        
    def setup_database(self):
        cursor = self.conn.cursor()
        
        # Create tables
        cursor.execute('''CREATE TABLE machines (
            id TEXT PRIMARY KEY,
            processing_time_s DOUBLE PRECISION,
            availability DOUBLE PRECISION,
            mttr_s DOUBLE PRECISION
        )''')
        
        cursor.execute('''CREATE TABLE buffers (
            id TEXT PRIMARY KEY,
            capacity INTEGER
        )''')
        
        cursor.execute('''CREATE TABLE stations (
            id TEXT PRIMARY KEY,
            processing_time_s DOUBLE PRECISION,
            availability_pct DOUBLE PRECISION,
            mttr_s DOUBLE PRECISION,
            power_working_kw DOUBLE PRECISION,
            power_idle_kw DOUBLE PRECISION
        )''')
        
        cursor.execute('''CREATE TABLE tag_map (
            tag_id TEXT PRIMARY KEY,
            machine_id TEXT,
            signal TEXT,
            unit TEXT,
            register TEXT,
            scale DOUBLE PRECISION
        )''')
        
        cursor.execute('''CREATE TABLE raw_ingest (
            ingested_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL,
            payload JSONB NOT NULL
        )''')
        
        cursor.execute('''CREATE TABLE ingest_watermark (
            source TEXT PRIMARY KEY,
            max_event_ts TIMESTAMPTZ
        )''')
        
        cursor.execute('''CREATE TABLE events (
            ts TIMESTAMPTZ NOT NULL,
            machine_id TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            duration_s DOUBLE PRECISION,
            energy_kwh DOUBLE PRECISION
        )''')
        
        cursor.execute('''CREATE TABLE samples (
            ts TIMESTAMPTZ NOT NULL,
            machine_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            value DOUBLE PRECISION
        )''')
        
        # Create indexes
        cursor.execute('CREATE INDEX idx_events_machine_time ON events(machine_id, ts)')
        cursor.execute('CREATE INDEX idx_samples_machine_time ON samples(machine_id, ts)')
        cursor.execute('CREATE INDEX idx_raw_ingest_source ON raw_ingest(source)')
        cursor.execute('CREATE INDEX idx_ingest_watermark_source ON ingest_watermark(source)')
        
        # Insert dimension data
        for machine_id, params in self.machines.items():
            cursor.execute("INSERT INTO machines VALUES (?, ?, ?, ?)",
                          (machine_id, params['processing_time'], params['availability'], params['mttr']))
            
        for buffer_id, params in self.buffers.items():
            cursor.execute("INSERT INTO buffers VALUES (?, ?)",
                          (buffer_id, params['capacity']))
            
        # Insert station data with appropriate values
        for machine_id, params in self.machines.items():
            cursor.execute("INSERT INTO stations VALUES (?, ?, ?, ?, ?, ?)",
                          (machine_id, params['processing_time'], 
                           params['availability'] * 100, params['mttr'],
                           params['power_working'], params['power_idle']))
        
        # Insert tag map data
        tag_mappings = [
            ('M1_time', 'M1', 'processing_time_s', 's', 'time', 1),
            ('M1_avail', 'M1', 'availability', '%', 'availability', 1),
            ('M1_mttr', 'M1', 'mttr_s', 's', 'mttr', 1),
            ('M2_time', 'M2', 'processing_time_s', 's', 'time', 1),
            ('M2_avail', 'M2', 'availability', '%', 'availability', 1),
            ('M2_mttr', 'M2', 'mttr_s', 's', 'mttr', 1),
            ('M3_time', 'M3', 'processing_time_s', 's', 'time', 1),
            ('M3_avail', 'M3', 'availability', '%', 'availability', 1),
            ('M3_mttr', 'M3', 'mttr_s', 's', 'mttr', 1),
            ('M4_time', 'M4', 'processing_time_s', 's', 'time', 1),
            ('M4_avail', 'M4', 'availability', '%', 'availability', 1),
            ('M4_mttr', 'M4', 'mttr_s', 's', 'mttr', 1),
            ('M5_time', 'M5', 'processing_time_s', 's', 'time', 1),
            ('M5_avail', 'M5', 'availability', '%', 'availability', 1),
            ('M5_mttr', 'M5', 'mttr_s', 's', 'mttr', 1)
        ]
        
        for tag_id, machine_id, signal, unit, register, scale in tag_mappings:
            cursor.execute("INSERT INTO tag_map VALUES (?, ?, ?, ?, ?, ?)",
                          (tag_id, machine_id, signal, unit, register, scale))
        
        self.conn.commit()
        
    def create_environment(self):
        # Create ground
        ground = chrono.ChBody()
        ground.SetBodyFixed(True)
        ground.SetPos(chrono.ChVectorD(0, -1, 0))
        self.system.Add(ground)
        
        # Create ground shape
        ground_shape = chrono.ChTriangleMeshConnected()
        ground_shape.LoadWavefrontMesh(chrono.GetChronoDataFile("models/ground.obj"))
        ground_shape.SetScale(chrono.ChVectorD(100, 1, 100))
        ground_shape.SetPos(chrono.ChVectorD(0, 0, 0))
        ground.AddAsset(chrono.ChVisualAsset(ground_shape))
        
    def create_machines(self):
        # Create machine bodies
        for machine_id in self.machines.keys():
            machine_body = chrono.ChBody()
            machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
            machine_body.SetBodyFixed(True)
            self.system.Add(machine_body)
            self.machine_data[machine_id] = {
                'body': machine_body,
                'status': 'operational',
                'processing_start': 0.0,
                'processing_time': self.machines[machine_id]['processing_time'],
                'availability': self.machines[machine_id]['availability'],
                'mttr': self.machines[machine_id]['mttr'],
                'power_working': self.machines[machine_id]['power_working'],
                'power_idle': self.machines[machine_id]['power_idle'],
                'last_status_change': 0.0,
                'total_processing_time': 0.0,
                'total_downtime': 0.0,
                'last_processed': 0.0
            }
            
    def create_buffers(self):
        # Create buffer bodies
        for buffer_id in self.buffers.keys():
            buffer_body = chrono.ChBody()
            buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
            buffer_body.SetBodyFixed(True)
            self.system.Add(buffer_body)
            self.buffer_data[buffer_id] = {
                'body': buffer_body,
                'capacity': self.buffers[buffer_id]['capacity'],
                'current_items': 0,
                'last_updated': 0.0
            }
            
    def create_production_line(self):
        # Create links between machines and buffers
        pass  # In this simulation, we'll focus on core logic
        
    def simulate(self):
        print("Starting simulation...")
        start_time = time.time()
        
        while self.simulation_time < self.end_time:
            # Update simulation
            self.system.DoStepDynamics(self.time_step)
            self.simulation_time += self.time_step
            
            # Log data periodically
            if self.simulation_time - self.last_log_time >= self.log_interval:
                self.log_data()
                self.last_log_time = self.simulation_time
                
                # Simulate machine availability and failures
                self.simulate_machine_status()
                
                # Simulate buffer levels
                self.update_buffer_levels()
                
            # Check if simulation should end
            if self.simulation_time >= self.end_time:
                break
                
        # Final logging
        self.log_data()
        self.print_summary()
        
        end_time = time.time()
        print(f"Simulation completed in {end_time - start_time:.2f} seconds")
        
    def simulate_machine_status(self):
        for machine_id, data in self.machine_data.items():
            if data['status'] == 'operational':
                # Simulate possible failure
                if np.random.random() < (1 - data['availability']) * self.time_step:
                    data['status'] = 'failed'
                    data['last_status_change'] = self.simulation_time
                    self.log_event(machine_id, 'failure', data['mttr'], 0.0)
            elif data['status'] == 'failed':
                # Simulate repair
                if self.simulation_time - data['last_status_change'] >= data['mttr']:
                    data['status'] = 'operational'
                    data['last_status_change'] = self.simulation_time
                    self.log_event(machine_id, 'repair', 0.0, 0.0)
                    
    def update_buffer_levels(self):
        # This is a simplified simulation of buffer content changes
        for buffer_id, data in self.buffer_data.items():
            # Simulate items coming in/out of buffer
            if np.random.random() < 0.01:  # 1% chance per tick to change
                change = np.random.choice([-1, 1])  # Add or remove item
                new_items = max(0, min(data['capacity'], data['current_items'] + change))
                data['current_items'] = new_items
                data['last_updated'] = self.simulation_time
                
    def log_data(self):
        current_time = datetime.now()
        
        # Log machine samples
        for machine_id, data in self.machine_data.items():
            # Log processing time
            self.log_sample(machine_id, 'processing_time_s', data['processing_time'], current_time)
            
            # Log availability
            self.log_sample(machine_id, 'availability', data['availability'], current_time)
            
            # Log MTTR
            self.log_sample(machine_id, 'mttr_s', data['mttr'], current_time)
            
            # Log power usage
            power = data['power_working'] if data['status'] == 'operational' else data['power_idle']
            self.log_sample(machine_id, 'power_kw', power, current_time)
            
        # Log buffer samples
        for buffer_id, data in self.buffer_data.items():
            self.log_sample(buffer_id, 'capacity', data['capacity'], current_time)
            self.log_sample(buffer_id, 'current_items', data['current_items'], current_time)
            
    def log_sample(self, machine_id, tag, value, timestamp):
        self.sample_log.append({
            'ts': timestamp,
            'machine_id': machine_id,
            'tag': tag,
            'value': value
        })
        
        # Insert into database
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO samples VALUES (?, ?, ?, ?)",
                      (timestamp, machine_id, tag, value))
        self.conn.commit()
        
    def log_event(self, machine_id, reason_code, duration_s, energy_kwh):
        timestamp = datetime.now()
        self.event_log.append({
            'ts': timestamp,
            'machine_id': machine_id,
            'reason_code': reason_code,
            'duration_s': duration_s,
            'energy_kwh': energy_kwh
        })
        
        # Insert into database
        cursor = self.conn.cursor()
        cursor.execute("INSERT