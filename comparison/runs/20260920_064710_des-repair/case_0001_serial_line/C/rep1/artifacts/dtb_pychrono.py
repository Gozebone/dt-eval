import pychrono as chrono
import pychrono.irrlicht as irr
import numpy as np
import json
import time
from datetime import datetime, timezone
from collections import defaultdict
import sqlite3

class ProductionLineSimulation:
    def __init__(self):
        # Initialize the Chrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))
        
        # Simulation parameters
        self.time_step = 0.01
        self.end_time = 3600  # 1 hour simulation
        self.current_time = 0.0
        
        # Equipment data
        self.machines_data = {
            "M1": {
                "processing_time_s": 150,
                "availability_pct": 98,
                "mttr_s": 600,
                "power_working_kw": 4.0,
                "power_idle_kw": 0.4
            },
            "M2": {
                "processing_time_s": 120,
                "availability_pct": 97,
                "mttr_s": 900,
                "power_working_kw": 5.0,
                "power_idle_kw": 0.5
            },
            "M3": {
                "processing_time_s": 180,
                "availability_pct": 95,
                "mttr_s": 1200,
                "power_working_kw": 6.0,
                "power_idle_kw": 0.6
            },
            "M4": {
                "processing_time_s": 120,
                "availability_pct": 97,
                "mttr_s": 900,
                "power_working_kw": 5.0,
                "power_idle_kw": 0.5
            },
            "M5": {
                "processing_time_s": 150,
                "availability_pct": 98,
                "mttr_s": 600,
                "power_working_kw": 4.0,
                "power_idle_kw": 0.4
            }
        }
        
        self.buffers_data = {
            "B0": {"capacity": 20, "before": "source", "after": "M1"},
            "B1": {"capacity": 8, "before": "M1", "after": "M2"},
            "B2": {"capacity": 8, "before": "M2", "after": "M3"},
            "B3": {"capacity": 8, "before": "M3", "after": "M4"},
            "B4": {"capacity": 8, "before": "M4", "after": "M5"}
        }
        
        # Create SQLite database
        self.db_conn = sqlite3.connect(':memory:')
        self.create_tables()
        self.setup_database_data()
        
        # Data structures for simulation
        self.parts = []
        self.machine_states = {}
        self.buffer_states = {}
        self.sensors = {}
        self.event_log = []
        self.sample_log = []
        
        # Create equipment
        self.create_equipment()
        
    def create_tables(self):
        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tag_map (
                tag_id TEXT PRIMARY KEY,
                machine_id TEXT,
                signal TEXT,
                unit TEXT,
                register TEXT,
                scale REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id TEXT PRIMARY KEY,
                processing_time_s REAL,
                availability_pct REAL,
                mttr_s REAL,
                power_working_kw REAL,
                power_idle_kw REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buffers (
                id TEXT PRIMARY KEY,
                capacity INTEGER,
                before TEXT,
                after TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_ingest (
                ingested_at TEXT,
                source TEXT,
                payload TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                ts TEXT,
                machine_id TEXT,
                reason_code TEXT,
                duration_s REAL,
                energy_kwh REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS samples (
                ts TEXT,
                machine_id TEXT,
                tag TEXT,
                value REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingest_watermark (
                source TEXT PRIMARY KEY,
                max_event_ts TEXT
            )
        ''')
        
        self.db_conn.commit()
    
    def setup_database_data(self):
        cursor = self.db_conn.cursor()
        
        # Insert machines data
        for machine_id, data in self.machines_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO machines 
                (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (machine_id, data['processing_time_s'], data['availability_pct'], 
                  data['mttr_s'], data['power_working_kw'], data['power_idle_kw']))
        
        # Insert buffers data
        for buffer_id, data in self.buffers_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO buffers 
                (id, capacity, before, after)
                VALUES (?, ?, ?, ?)
            ''', (buffer_id, data['capacity'], data['before'], data['after']))
        
        self.db_conn.commit()
    
    def create_equipment(self):
        # Create source part generator
        self.source_generator = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 1000, True, True)
        self.source_generator.SetPos(chrono.ChVectorD(0, 0, 0))
        self.system.Add(self.source_generator)
        
        # Create stations (machines)
        machine_positions = {
            "M1": chrono.ChVectorD(5, 0, 0),
            "M2": chrono.ChVectorD(10, 0, 0),
            "M3": chrono.ChVectorD(15, 0, 0),
            "M4": chrono.ChVectorD(20, 0, 0),
            "M5": chrono.ChVectorD(25, 0, 0)
        }
        
        for machine_id, pos in machine_positions.items():
            machine = chrono.ChBodyEasyBox(1.0, 1.0, 1.0, 1000, True, True)
            machine.SetPos(pos)
            machine.SetBodyFixed(False)
            self.system.Add(machine)
            self.machine_states[machine_id] = {
                "status": "idle",
                "processing_time_left": 0,
                "power_kw": 0,
                "last_event_time": 0
            }
        
        # Create buffers
        buffer_positions = {
            "B0": chrono.ChVectorD(2.5, 0, 0),
            "B1": chrono.ChVectorD(7.5, 0, 0),
            "B2": chrono.ChVectorD(12.5, 0, 0),
            "B3": chrono.ChVectorD(17.5, 0, 0),
            "B4": chrono.ChVectorD(22.5, 0, 0)
        }
        
        for buffer_id, pos in buffer_positions.items():
            buffer = chrono.ChBodyEasyBox(0.8, 0.8, 0.8, 1000, True, True)
            buffer.SetPos(pos)
            buffer.SetBodyFixed(False)
            self.system.Add(buffer)
            self.buffer_states[buffer_id] = {"count": 0, "capacity": self.buffers_data[buffer_id]["capacity"]}
        
        # Create sink
        sink = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 1000, True, True)
        sink.SetPos(chrono.ChVectorD(30, 0, 0))
        self.system.Add(sink)
        
    def generate_part(self, time):
        part = {
            "id": f"part_{len(self.parts)}",
            "arrival_time": time,
            "status": "in_source"
        }
        self.parts.append(part)
        return part
    
    def simulate_step(self):
        self.current_time += self.time_step
        
        # Generate new parts periodically
        if int(self.current_time) % 130 == 0:
            self.generate_part(self.current_time)
        
        # Update machine states
        for machine_id in self.machine_states:
            machine_state = self.machine_states[machine_id]
            if machine_state["status"] == "processing":
                machine_state["processing_time_left"] -= self.time_step
                if machine_state["processing_time_left"] <= 0:
                    # Machine finished processing
                    machine_state["status"] = "idle"
                    machine_state["power_kw"] = self.machines_data[machine_id]["power_idle_kw"]
                    self.log_event(machine_id, "processing_complete", 0, 0)
        
        # Update buffer states
        for buffer_id, state in self.buffer_states.items():
            # Simulate buffer behavior
            pass
        
        # Log samples
        self.log_samples()
        
        return self.current_time < self.end_time
    
    def log_samples(self):
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Log machine power usage
        for machine_id, state in self.machine_states.items():
            power = state["power_kw"]
            self.sample_log.append({
                "ts": timestamp,
                "machine_id": machine_id,
                "tag": "power_kw",
                "value": power
            })
            
            # Insert into database
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, machine_id, "power_kw", power))
        
        # Log buffer counts
        for buffer_id, state in self.buffer_states.items():
            count = state["count"]
            self.sample_log.append({
                "ts": timestamp,
                "machine_id": buffer_id,
                "tag": "part_count",
                "value": count
            })
            
            # Insert into database
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, buffer_id, "part_count", count))
        
        self.db_conn.commit()
    
    def log_event(self, machine_id, reason_code, duration_s, energy_kwh):
        timestamp = datetime.now(timezone.utc).isoformat()
        self.event_log.append({
            "ts": timestamp,
            "machine_id": machine_id,
            "reason_code": reason_code,
            "duration_s": duration_s,
            "energy_kwh": energy_kwh
        })
        
        # Insert into database
        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT INTO events (ts, machine_id, reason_code, duration_s, energy_kwh)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, machine_id, reason_code, duration_s, energy_kwh))
        
        self.db_conn.commit()
    
    def run_simulation(self):
        # Initialize simulation
        self.current_time = 0.0
        
        # Main simulation loop
        while self.simulate_step():
            # Step the system
            self.system.DoStepDynamics(self.time_step)
        
        print(f"Simulation completed at time {self.current_time}")
        print(f"Total parts generated: {len(self.parts)}")
        print(f"Events logged: {len(self.event_log)}")
        print(f"Samples logged: {len(self.sample_log)}")
        
        return self.event_log, self.sample_log

def main():
    # Create and run the simulation
    simulation = ProductionLineSimulation()
    
    try:
        events, samples = simulation.run_simulation()
        print("Simulation executed successfully")
    except Exception as e:
        print(f"Error during simulation: {e}")
        return
    
    # Demonstrate database content
    print("\n--- Database Content ---")
    cursor = simulation.db_conn.cursor()
    
    cursor.execute("SELECT * FROM machines")
    print("\nMachines:")
    for row in cursor.fetchall():
        print(row)
    
    cursor.execute("SELECT * FROM buffers")
    print("\nBuffers:")
    for row in cursor.fetchall():
        print(row)
    
    cursor.execute("SELECT * FROM events LIMIT 5")
    print("\nEvents (first 5):")
    for row in cursor.fetchall():
        print(row)
    
    cursor.execute("SELECT * FROM samples LIMIT 5")
    print("\nSamples (first 5):")
    for row in cursor.fetchall():
        print(row)
    
    # Close database connection
    simulation.db_conn.close()

if __name__ == "__main__":
    main()