```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import pychrono.fea as fea
import numpy as np
import time
import json
from datetime import datetime, timedelta
import sqlite3
import threading
import queue

# Database setup
def setup_database():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machines (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT
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
        CREATE TABLE IF NOT EXISTS stations (
            id TEXT PRIMARY KEY,
            processing_time_s DOUBLE PRECISION,
            availability_pct DOUBLE PRECISION,
            mttr_s DOUBLE PRECISION,
            power_working_kw DOUBLE PRECISION,
            power_idle_kw DOUBLE PRECISION
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_ingest (
            ingested_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL,
            payload JSONB NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingest_watermark (
            source TEXT PRIMARY KEY,
            max_event_ts TIMESTAMPTZ
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            ts TIMESTAMPTZ NOT NULL,
            machine_id TEXT NOT NULL,
            reason_code TEXT,
            duration_s DOUBLE PRECISION,
            energy_kwh DOUBLE PRECISION
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            ts TIMESTAMPTZ NOT NULL,
            machine_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            value DOUBLE PRECISION
        )
    ''')
    
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
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_machine_id_ts ON events (machine_id, ts)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_samples_machine_id_ts ON samples (machine_id, ts)')
    
    # Insert initial data
    machines_data = [
        ('M1', 'M1', 'process'), ('M2', 'M2', 'process'), ('M3', 'M3', 'process'), ('M4', 'M4', 'process'),
        ('B0', 'B0', 'buffer'), ('B1', 'B1', 'buffer'), ('B2', 'B2', 'buffer'), ('B3', 'B3', 'buffer')
    ]
    
    buffers_data = [
        ('B0', 25, 'source', 'M1'), ('B1', 10, 'M1', 'M2'), ('B2', 10, 'M2', 'M3'), ('B3', 10, 'M3', 'M4')
    ]
    
    stations_data = [
        ('M1', 60, 99.99, 300, 3.0, 0.3),
        ('M2', 80, 100.0, 600, 5.0, 0.5),
        ('M3', 70, 99.88, 600, 4.5, 0.45),
        ('M4', 75, 99.995, 300, 4.0, 0.4)
    ]
    
    tag_map_data = [
        ('T1', 'M1', 'temperature', '°C', 'T1', 1.0),
        ('T2', 'M2', 'temperature', '°C', 'T2', 1.0),
        ('T3', 'M3', 'temperature', '°C', 'T3', 1.0),
        ('T4', 'M4', 'temperature', '°C', 'T4', 1.0),
        ('P1', 'M1', 'pressure', 'bar', 'P1', 1.0),
        ('P2', 'M2', 'pressure', 'bar', 'P2', 1.0),
        ('P3', 'M3', 'pressure', 'bar', 'P3', 1.0),
        ('P4', 'M4', 'pressure', 'bar', 'P4', 1.0)
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO machines VALUES (?, ?, ?)', machines_data)
    cursor.executemany('INSERT OR REPLACE INTO buffers VALUES (?, ?, ?, ?)', buffers_data)
    cursor.executemany('INSERT OR REPLACE INTO stations VALUES (?, ?, ?, ?, ?, ?)', stations_data)
    cursor.executemany('INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)', tag_map_data)
    
    conn.commit()
    conn.close()

# Sensor data logging
class SensorLogger:
    def __init__(self):
        self.db_queue = queue.Queue()
        self.db_thread = threading.Thread(target=self._db_worker)
        self.db_thread.start()
        
    def _db_worker(self):
        conn = sqlite3.connect('digital_twin.db')
        cursor = conn.cursor()
        while True:
            try:
                data = self.db_queue.get(timeout=1)
                if data is None:
                    break
                cursor.execute(data['query'], data['params'])
                conn.commit()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"DB logging error: {e}")
        conn.close()
    
    def log_event(self, machine_id, reason_code, duration_s, energy_kwh):
        ts = datetime.now()
        query = "INSERT INTO events VALUES (?, ?, ?, ?, ?)"
        params = (ts, machine_id, reason_code, duration_s, energy_kwh)
        self.db_queue.put({'query': query, 'params': params})
    
    def log_sample(self, machine_id, tag, value):
        ts = datetime.now()
        query = "INSERT INTO samples VALUES (?, ?, ?, ?)"
        params = (ts, machine_id, tag, value)
        self.db_queue.put({'query': query, 'params': params})

# Process station class
class ProcessStation:
    def __init__(self, id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw):
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.is_operational = True
        self.current_processing_time = 0
        self.logger = SensorLogger()
        
    def update(self, dt):
        if not self.is_operational:
            self.current_processing_time += dt
            if self.current_processing_time >= self.mttr_s:
                self.is_operational = True
                self.current_processing_time = 0
                # Log event when repaired
                self.logger.log_event(self.id, "REPAIR", self.mttr_s, 0)
        else:
            self.current_processing_time += dt
            if self.current_processing_time >= self.processing_time_s:
                self.current_processing_time = 0
                # Simulate random failure based on availability
                if np.random.rand() > self.availability_pct / 100:
                    self.is_operational = False
                    self.current_processing_time = 0
                    # Log event when failed
                    self.logger.log_event(self.id, "FAILURE", self.processing_time_s, 0)
    
    def get_power_consumption(self):
        if self.is_operational:
            return self.power_working_kw
        else:
            return self.power_idle_kw

# Buffer class
class Buffer:
    def __init__(self, id, capacity, before, after):
        self.id = id
        self.capacity = capacity
        self.before = before
        self.after = after
        self.items = []
        
    def add_item(self, item):
        if len(self.items) < self.capacity:
            self.items.append(item)
            return True
        return False
        
    def remove_item(self):
        if self.items:
            return self.items.pop(0)
        return None

# Main simulation class
class ProductionLineSimulation:
    def __init__(self, time_step=0.01):
        self.system = chrono.ChSystemNSC()
        self.system.SetGravity(chrono.ChVectorD(0, -9.81, 0))
        
        # Setup materials
        self.mat = chrono.ChMaterialSurfaceNSC()
        self.mat.SetFriction(0.5)
        self.mat.SetRestitution(0.0)
        
        # Initialize components
        self.stations = {}
        self.buffers = {}
        self.source_timer = 0
        self.source_interval = 45  # seconds
        
        # Setup database
        setup_database()
        
        # Initialize logger
        self.logger = SensorLogger()
        
        # Create source object
        self.source = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 1000, True, True)
        self.source.SetPos(chrono.ChVectorD(-5, 0, 0))
        self.system.AddBody(self.source)
        
        # Setup stations
        stations_config = [
            {'id': 'M1', 'processing_time_s': 60, 'availability_pct': 99.99, 'mttr_s': 300, 'power_working_kw': 3.0, 'power_idle_kw': 0.3},
            {'id': 'M2', 'processing_time_s': 80, 'availability_pct': 100.0, 'mttr_s': 600, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
            {'id': 'M3', 'processing_time_s': 70, 'availability_pct': 99.88, 'mttr_s': 600, 'power_working_kw': 4.5, 'power_idle_kw': 0.45},
            {'id': 'M4', 'processing_time_s': 75, 'availability_pct': 99.995, 'mttr_s': 300, 'power_working_kw': 4.0, 'power_idle_kw': 0.4}
        ]
        
        for config in stations_config:
            self.stations[config['id']] = ProcessStation(**config)
            
        # Setup buffers
        buffers_config = [
            {'id': 'B0', 'capacity': 25, 'before': 'source', 'after': 'M1'},
            {'id': 'B1', 'capacity': 10, 'before': 'M1', 'after': 'M2'},
            {'id': 'B2', 'capacity': 10, 'before': 'M2', 'after': 'M3'},
            {'id': 'B3', 'capacity': 10, 'before': 'M3', 'after': 'M4'}
        ]
        
        for config in buffers_config:
            self.buffers[config['id']] = Buffer(**config)
            
        # Setup sensors
        for station_id in ['M1', 'M2', 'M3', 'M4']:
            tag_data = [
                {'tag': 'T1', 'machine_id': 'M1', 'signal': 'temperature', 'unit': '°C', 'register': 'T1', 'scale': 1.0},
                {'tag': 'T2', 'machine_id': 'M2', 'signal': 'temperature', 'unit': '°C', 'register': 'T2', 'scale': 1.0},
                {'tag': 'T3', 'machine_id': 'M3', 'signal': 'temperature', 'unit': '°C', 'register': 'T3', 'scale': 1.0},
                {'tag': 'T4', 'machine_id': 'M4', 'signal': 'temperature', 'unit': '°C', 'register': 'T4', 'scale': 1.0},
                {'tag': 'P1', 'machine_id': 'M1', 'signal': 'pressure', 'unit': 'bar', 'register': 'P1', 'scale': 1.0},
                {'tag': 'P2', 'machine_id': 'M2', 'signal': 'pressure', 'unit': 'bar', 'register': 'P2', 'scale': 1.0},
                {'tag': 'P3', 'machine_id': 'M3', 'signal': 'pressure', 'unit': 'bar', 'register': 'P3', 'scale': 1.0},
                {'tag': 'P4', 'machine_id': 'M4', 'signal': 'pressure', 'unit': 'bar', 'register': 'P4', 'scale': 1.0}
            ]
            
            for tag in tag_data:
                if tag['machine_id'] == station_id:
                    # Store tag mapping for future use
                    pass  # In a real implementation, this would be stored in the database

    def add_part_to_buffer(self, buffer_id, part):
        return self.buffers[buffer_id].add_item(part)
        
    def remove_part_from_buffer(self, buffer_id):
        return self.buffers[buffer_id].remove_item()
        
    def simulate(self, simulation_time):
        start_time = time.time()
        current_time = 0
        
        # Start simulation
        while current_time < simulation_time:
           