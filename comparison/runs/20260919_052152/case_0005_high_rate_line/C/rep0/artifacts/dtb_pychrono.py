import pychrono as chrono
import pychrono.fea as fea
import pychrono.irrlicht as irr
import numpy as np
import json
import time
import datetime
import sqlite3
from typing import Dict, List, Any

class DigitalTwinSimulation:
    def __init__(self):
        # Initialize PyChrono system
        self.system = chrono.ChSystemNSC()
        self.system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))
        
        # Create database connection
        self.conn = sqlite3.connect(':memory:')
        self.setup_database()
        
        # Simulation parameters
        self.time_step = 0.01
        self.sim_time = 0.0
        self.end_time = 3600.0  # 1 hour simulation
        
        # Equipment and stations
        self.equipment = {}
        self.stations = {}
        self.sensors = {}
        
        # Initialize simulation components
        self.setup_environment()
        self.setup_equipment()
        self.setup_sensors()
        
    def setup_database(self):
        cursor = self.conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE raw_ingest (
                ingested_at timestamptz NOT NULL,
                source text NOT NULL,
                payload jsonb NOT NULL,
                PRIMARY KEY (ingested_at, source)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE ingest_watermark (
                source text PRIMARY KEY,
                max_event_ts timestamptz
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE tag_map (
                tag_id text PRIMARY KEY,
                machine_id text,
                signal text,
                unit text,
                register text,
                scale double precision
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE machines (
                id text PRIMARY KEY,
                name text,
                type text
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE stations (
                id text PRIMARY KEY,
                machine_id text,
                processing_time_s double precision,
                availability_pct double precision,
                mttr_s double precision,
                power_working_kw double precision,
                power_idle_kw double precision
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE buffers (
                id text PRIMARY KEY,
                capacity int,
                before text,
                after text
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE events (
                ts timestamptz NOT NULL,
                machine_id text NOT NULL,
                reason_code text,
                duration_s double precision,
                energy_kwh double precision,
                PRIMARY KEY (ts, machine_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE samples (
                ts timestamptz NOT NULL,
                machine_id text NOT NULL,
                tag text NOT NULL,
                value double precision,
                PRIMARY KEY (ts, machine_id, tag)
            )
        ''')
        
        # Insert dimension data
        cursor.execute('''
            INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES
            ('length_sensor', 'laser_cutter', 'лазерный датчик для измерения длины', 'м', 'length', 1.0),
            ('temperature_sensor', 'tester', 'датчик температуры для тестера', '°C', 'temp', 1.0)
        ''')
        
        cursor.execute('''
            INSERT INTO machines (id, name, type) VALUES
            ('laser_cutter', 'лазерный резак', 'equipment'),
            ('ball_screw', 'шариковая скоба', 'equipment'),
            ('tester', 'тестер', 'equipment')
        ''')
        
        cursor.execute('''
            INSERT INTO stations (id, machine_id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES
            ('M1', 'laser_cutter', 30.0, 95.0, 1800.0, 5.0, 1.0)
        ''')
        
        cursor.execute('''
            INSERT INTO buffers (id, capacity, before, after) VALUES
            ('B0', 10, 'source', 'M1')
        ''')
        
        self.conn.commit()
        
    def setup_environment(self):
        # Create ground
        ground = chrono.ChBody()
        ground.SetBodyFixed(True)
        ground.SetPos(chrono.ChVectorD(0, -1, 0))
        self.system.Add(ground)
        
        # Create ground shape
        ground_shape = chrono.ChBoxShape()
        ground_shape.GetBoxGeometry().SetLengths(chrono.ChVectorD(20, 2, 20))
        ground.AddAsset(ground_shape)
        
        # Create material for ground
        ground_material = chrono.ChMaterialSurfaceNSC()
        ground_material.SetFriction(0.4)
        ground_material.SetRestitution(0.1)
        ground.AddAsset(ground_material)
        
    def setup_equipment(self):
        # Create laser cutter (station M1)
        cutter_body = chrono.ChBody()
        cutter_body.SetPos(chrono.ChVectorD(0, 0, 0))
        cutter_body.SetMass(100)
        cutter_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
        self.system.Add(cutter_body)
        
        # Add shape for cutter
        cutter_shape = chrono.ChBoxShape()
        cutter_shape.GetBoxGeometry().SetLengths(chrono.ChVectorD(1, 0.5, 1))
        cutter_body.AddAsset(cutter_shape)
        
        # Add material for cutter
        cutter_material = chrono.ChMaterialSurfaceNSC()
        cutter_material.SetFriction(0.5)
        cutter_material.SetRestitution(0.1)
        cutter_body.AddAsset(cutter_material)
        
        # Store equipment
        self.equipment['laser_cutter'] = cutter_body
        self.stations['M1'] = {
            'machine_id': 'laser_cutter',
            'processing_time_s': 30.0,
            'availability_pct': 95.0,
            'mttr_s': 1800.0,
            'power_working_kw': 5.0,
            'power_idle_kw': 1.0
        }
        
        # Create buffer B0
        buffer_body = chrono.ChBody()
        buffer_body.SetPos(chrono.ChVectorD(-2, 0, 0))
        buffer_body.SetMass(50)
        buffer_body.SetInertiaXX(chrono.ChVectorD(5, 5, 5))
        self.system.Add(buffer_body)
        
        # Add shape for buffer
        buffer_shape = chrono.ChBoxShape()
        buffer_shape.GetBoxGeometry().SetLengths(chrono.ChVectorD(0.5, 0.5, 0.5))
        buffer_body.AddAsset(buffer_shape)
        
        # Add material for buffer
        buffer_material = chrono.ChMaterialSurfaceNSC()
        buffer_material.SetFriction(0.3)
        buffer_material.SetRestitution(0.05)
        buffer_body.AddAsset(buffer_material)
        
        self.equipment['buffer_B0'] = buffer_body
        
    def setup_sensors(self):
        # Create sensors
        self.sensors['length_sensor'] = {
            'tag': 'length_sensor',
            'machine_id': 'laser_cutter',
            'value': 0.0
        }
        
        self.sensors['temperature_sensor'] = {
            'tag': 'temperature_sensor',
            'machine_id': 'tester',
            'value': 25.0
        }
        
    def get_station_stats(self, station_id: str) -> Dict[str, float]:
        """Get current station statistics"""
        return self.stations.get(station_id, {})
        
    def log_event(self, machine_id: str, reason_code: str, duration_s: float, energy_kwh: float):
        """Log event data to database"""
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        
        cursor.execute('''
            INSERT INTO events (ts, machine_id, reason_code, duration_s, energy_kwh)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, machine_id, reason_code, duration_s, energy_kwh))
        
        self.conn.commit()
        
    def log_sample(self, machine_id: str, tag: str, value: float):
        """Log sample data to database"""
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        
        cursor.execute('''
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, machine_id, tag, value))
        
        self.conn.commit()
        
    def log_ingest(self, source: str, payload: Dict[str, Any]):
        """Log raw ingest data"""
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        
        cursor.execute('''
            INSERT INTO raw_ingest (ingested_at, source, payload)
            VALUES (?, ?, ?)
        ''', (timestamp, source, json.dumps(payload)))
        
        self.conn.commit()
        
    def simulate(self):
        """Main simulation loop"""
        print("Starting simulation...")
        
        while self.sim_time < self.end_time:
            # Update simulation time
            self.system.DoStepDynamics(self.time_step)
            self.sim_time += self.time_step
            
            # Check for events every 10 seconds
            if int(self.sim_time) % 10 == 0:
                # Log sample data
                self.log_sample(
                    self.sensors['length_sensor']['machine_id'],
                    self.sensors['length_sensor']['tag'],
                    self.sensors['length_sensor']['value'] + np.random.normal(0, 0.01)
                )
                
                # Log events
                if np.random.random() < 0.01:  # 1% chance of event
                    self.log_event(
                        'laser_cutter',
                        'maintenance_needed',
                        10.0,
                        0.02
                    )
                    
            # Log raw ingest data
            self.log_ingest(
                'sensor_data',
                {
                    'type': 'sample',
                    'tag': 'length_sensor',
                    'value': self.sensors['length_sensor']['value'] + np.random.normal(0, 0.01),
                    'timestamp': self.sim_time
                }
            )
            
            # Simulate sensor readings
            self.sensors['length_sensor']['value'] = 1.5 + 0.1 * np.sin(self.sim_time / 10)
            self.sensors['temperature_sensor']['value'] = 25.0 + 2.0 * np.sin(self.sim_time / 5)
            
            if self.sim_time % 30 == 0:
                stats = self.get_station_stats('M1')
                print(f"Time: {self.sim_time:.1f}s")
                print(f"  Station M1: Processing time {stats.get('processing_time_s', 0):.1f}s")
                print(f"  Laser cutter length reading: {self.sensors['length_sensor']['value']:.3f}m")
                print(f"  Tester temperature: {self.sensors['temperature_sensor']['value']:.1f}°C")

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM samples")
        sample_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM raw_ingest")
        ingest_count = cursor.fetchone()[0]
        
        # Get recent events
        cursor.execute("SELECT * FROM events ORDER BY ts DESC LIMIT 5")
        recent_events = cursor.fetchall()
        
        # Get recent samples
        cursor.execute("SELECT * FROM samples ORDER BY ts DESC LIMIT 5")
        recent_samples = cursor.fetchall()
        
        return {
            'event_count': event_count,
            'sample_count': sample_count,
            'ingest_count': ingest_count,
            'recent_events': recent_events,
            'recent_samples': recent_samples
        }

# Run simulation
if __name__ == "__main__":
    try:
        sim = DigitalTwinSimulation()
        sim.simulate()
        
        # Print final stats
        stats = sim.get_database_stats()
        print("\n--- Final Simulation Stats ---")
        print(f"Events logged: {stats['event_count']}")
        print(f"Samples logged: {stats['sample_count']}")
        print(f"Raw ingest entries: {stats['ingest_count']}")
        
        # Print recent entries
        print("\nRecent events:")
        for event in stats['recent_events']:
            print(f"  {event}")
            
        print("\nRecent samples:")
        for sample in stats['recent_samples']:
            print(f"  {sample}")
            
    except Exception as e:
        print(f"Error occurred during simulation: {str(e)}")
        raise
    finally:
        # Cleanup
        print("Simulation completed successfully")