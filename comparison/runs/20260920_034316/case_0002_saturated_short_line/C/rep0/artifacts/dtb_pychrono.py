import os
import sys
import math
import time
import json
import random
from datetime import datetime, timedelta
import numpy as np

# PyChrono imports
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import pychrono.fsi as chronofsi

# Import database modules
import sqlite3

# Define constants
TIMESTEP = 0.01
SIMULATION_TIME = 432000  # 5 days in seconds
GRAVITY = chrono.ChVectorD(0, -9.81, 0)
DT = 0.01

class DatabaseManager:
    def __init__(self, db_path="simulation.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tag_map (
                tag_id TEXT PRIMARY KEY,
                machine_id TEXT,
                signal TEXT,
                unit TEXT,
                register TEXT,
                scale DOUBLE PRECISION
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id TEXT PRIMARY KEY,
                type TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stations (
                id TEXT PRIMARY KEY,
                processing_time_s INT,
                availability_pct DOUBLE PRECISION,
                mttr_s INT,
                power_working_kw DOUBLE PRECISION,
                power_idle_kw DOUBLE PRECISION
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buffers (
                id TEXT PRIMARY KEY,
                capacity INT,
                before TEXT,
                after TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_ingest (
                ingested_at TIMESTAMPTZ,
                source TEXT,
                payload JSONB
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                ts TIMESTAMPTZ,
                machine_id TEXT,
                reason_code TEXT,
                duration_s DOUBLE PRECISION,
                energy_kwh DOUBLE PRECISION
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS samples (
                ts TIMESTAMPTZ,
                machine_id TEXT,
                tag TEXT,
                value DOUBLE PRECISION
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingest_watermark (
                source TEXT PRIMARY KEY,
                max_event_ts TIMESTAMPTZ
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_machine_id_ts ON events (machine_id, ts)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_samples_machine_id_ts ON samples (machine_id, ts)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_ingest_source ON raw_ingest (source)')
        
        # Insert tag_map data
        tag_map_data = [
            ('M1_process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1),
            ('M1_availability', 'M1', 'availability', 'pct', 'availability', 1),
            ('M1_mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1),
            ('M1_work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1),
            ('M1_idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
            ('M2_process_time_s', 'M2', 'process_time_s', 's', 'process_time_s', 1),
            ('M2_availability', 'M2', 'availability', 'pct', 'availability', 1),
            ('M2_mttr_s', 'M2', 'mttr_s', 's', 'mttr_s', 1),
            ('M2_work_power_kw', 'M2', 'work_power_kw', 'kW', 'work_power_kw', 1),
            ('M2_idle_power_kw', 'M2', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
            ('M3_process_time_s', 'M3', 'process_time_s', 's', 'process_time_s', 1),
            ('M3_availability', 'M3', 'availability', 'pct', 'availability', 1),
            ('M3_mttr_s', 'M3', 'mttr_s', 's', 'mttr_s', 1),
            ('M3_work_power_kw', 'M3', 'work_power_kw', 'kW', 'work_power_kw', 1),
            ('M3_idle_power_kw', 'M3', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
            ('source_inter_arrival_s', 'source', 'inter_arrival_s', 's', 'inter_arrival_s', 1)
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)
        ''', tag_map_data)
        
        # Insert machines data
        machines_data = [
            ('source', 'source'),
            ('M1', 'station'),
            ('M2', 'station'),
            ('M3', 'station'),
            ('sink', 'sink')
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO machines VALUES (?, ?)
        ''', machines_data)
        
        # Insert stations data
        stations_data = [
            ('M1', 90, 0.99, 600, 3.0, 0.3),
            ('M2', 70, 0.98, 900, 4.5, 0.45),
            ('M3', 110, 0.99, 1200, 6.0, 0.6)
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO stations VALUES (?, ?, ?, ?, ?, ?)
        ''', stations_data)
        
        # Insert buffers data
        buffers_data = [
            ('B0', 15, 'source', 'M1'),
            ('B1', 5, 'M1', 'M2'),
            ('B2', 5, 'M2', 'M3')
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO buffers VALUES (?, ?, ?, ?)
        ''', buffers_data)
        
        conn.commit()
        conn.close()
        
    def log_sample(self, ts, machine_id, tag, value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO samples VALUES (?, ?, ?, ?)
        ''', (ts, machine_id, tag, value))
        conn.commit()
        conn.close()
        
    def log_event(self, ts, machine_id, reason_code, duration_s, energy_kwh):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events VALUES (?, ?, ?, ?, ?)
        ''', (ts, machine_id, reason_code, duration_s, energy_kwh))
        conn.commit()
        conn.close()

class Equipment:
    def __init__(self, id, equipment_type, params):
        self.id = id
        self.type = equipment_type
        self.params = params
        self.status = "idle"
        self.power = 0.0
        self.active_time = 0.0
        self.failure_time = 0.0
        self.is_operational = True
        self.failure_count = 0
        self.total_energy = 0.0
        self.start_time = time.time()
        
    def calculate_energy_consumption(self, dt):
        if self.is_operational:
            if self.status == "processing":
                energy_kwh = self.params.get("work_power_kw", 0) * dt / 3600.0
            else:
                energy_kwh = self.params.get("idle_power_kw", 0) * dt / 3600.0
        else:
            energy_kwh = 0.0
        self.total_energy += energy_kwh
        return energy_kwh
        
    def update_status(self, new_status):
        if self.status != new_status:
            self.status = new_status
            self.active_time = 0.0
            
    def update(self, dt):
        if self.is_operational:
            self.active_time += dt
            if self.status == "processing" and self.active_time >= self.params.get("process_time_s", 0):
                self.status = "idle"
                self.active_time = 0.0
        else:
            self.failure_time += dt

class Source:
    def __init__(self, params, db_manager):
        self.params = params
        self.db_manager = db_manager
        self.inter_arrival_time = params.get("inter_arrival_s", 60)
        self.last_arrival = 0.0
        self.item_count = 0
        self.start_time = time.time()
        
    def generate_item(self, current_time):
        if current_time - self.last_arrival >= self.inter_arrival_time:
            self.last_arrival = current_time
            self.item_count += 1
            return True
        return False
        
    def log_arrival(self, current_time):
        self.db_manager.log_sample(current_time, "source", "item_count", self.item_count)
        self.db_manager.log_sample(current_time, "source", "inter_arrival_s", self.inter_arrival_time)

class Buffer:
    def __init__(self, id, capacity, before, after):
        self.id = id
        self.capacity = capacity
        self.before = before
        self.after = after
        self.items = []
        self.start_time = time.time()
        
    def add_item(self, item):
        if len(self.items) < self.capacity:
            self.items.append(item)
            return True
        return False
        
    def remove_item(self):
        if self.items:
            return self.items.pop(0)
        return None

class Simulation:
    def __init__(self):
        # Initialize database
        self.db_manager = DatabaseManager()
        
        # Setup simulation parameters
        self.start_time = time.time()
        self.current_time = 0.0
        self.dt = DT
        
        # Create equipment
        self.source = Source({"inter_arrival_s": 60}, self.db_manager)
        self.machines = {}
        self.buffers = {}
        
        # Initialize machines
        machine_params = {
            "M1": {
                "process_time_s": 90,
                "availability": 0.99,
                "mttr_s": 600,
                "work_power_kw": 3.0,
                "idle_power_kw": 0.3
            },
            "M2": {
                "process_time_s": 70,
                "availability": 0.98,
                "mttr_s": 900,
                "work_power_kw": 4.5,
                "idle_power_kw": 0.45
            },
            "M3": {
                "process_time_s": 110,
                "availability": 0.99,
                "mttr_s": 1200,
                "work_power_kw": 6.0,
                "idle_power_kw": 0.6
            }
        }
        
        for machine_id, params in machine_params.items():
            self.machines[machine_id] = Equipment(machine_id, "station", params)
            
        # Initialize buffers
        self.buffers = {
            "B0": Buffer("B0", 15, "source", "M1"),
            "B1": Buffer("B1", 5, "M1", "M2"),
            "B2": Buffer("B2", 5, "M2", "M3")
        }
        
        # Create items tracking
        self.items = []
        self.processed_items = 0
        self.failed_items = 0
        
        # Simulation state tracking
        self.running = True
        
    def check_machine_failure(self, machine_id):
        machine = self.machines[machine_id]
        if machine.is_operational:
            # Simulate failure based on availability
            if random.random() > machine.params.get("availability", 0.99):
                machine.is_operational = False
                machine.failure_count += 1
                machine.failure_time = 0.0
                # Log failure event
                self.db_manager.log_event(
                    self.current_time,
                    machine_id,
                    "failure",
                    0,
                    0
                )
                return True
        elif machine.failure_time >= machine.params.get("mttr_s", 600):
            machine.is_operational = True
            machine.failure_time = 0.0
            # Log recovery event
            self.db_manager.log_event(
                self.current_time,
                machine_id,
                "recovery",
                machine.params.get("mttr_s", 600),
                0
            )
            return True
        return False
        
    def process_item(self, item_id, current_time):
        # Move item through the production line
        machine_order = ["M1", "M2", "M3"]
        buffer_order = ["B0", "B1", "B2"]
        
        for i, machine_id in enumerate(machine_order):
            if item_id not in [item['id'] for item in self.items]:
                break
                
            machine = self.machines[machine_id]
            buffer_id = buffer_order[i]
            
            # Check if machine is operational
            if not machine.is_operational:
                continue
                
            # Check if buffer has space
            buffer = self.buffers[buffer_id]
            if not buffer.add_item(item_id):
                continue
                
            # Start processing
            if machine.status != "processing":
                machine.update_status("processing")
                machine.active_time =