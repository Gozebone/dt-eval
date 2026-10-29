```python
import pychrono as chrono
import numpy as np
import json
import time
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json
import threading
import queue

# Database connection parameters
DB_CONFIG = {
    'dbname': 'digital_twin_db',
    'user': 'your_user',
    'password': 'your_password',
    'host': 'localhost',
    'port': '5432'
}

# Simulation constants
SIMULATION_TIME = 5 * 24 * 60 * 60  # 5 days in seconds
TIME_STEP = 0.01  # 10ms time step
LOG_INTERVAL = 1.0  # Log every second

# Equipment configuration
EQUIPMENT_CONFIG = {
    "M1": {"process_time_s": 100, "availability_pct": 92.58, "mttr_s": 3206.25,
           "power_working_kw": 4.0, "power_idle_kw": 0.4},
    "M2": {"process_time_s": 130, "availability_pct": 97.36, "mttr_s": 2859.26,
           "power_working_kw": 5.0, "power_idle_kw": 0.5},
    "M3": {"process_time_s": 90, "availability_pct": 94.69, "mttr_s": 2882.82,
           "power_working_kw": 4.5, "power_idle_kw": 0.45},
    "M4": {"process_time_s": 140, "availability_pct": 100.0, "mttr_s": 1099.8,
           "power_working_kw": 7.0, "power_idle_kw": 0.7},
    "M5": {"process_time_s": 110, "availability_pct": 98.23, "mttr_s": 1099.8,
           "power_working_kw": 5.5, "power_idle_kw": 0.55},
    "B0": {"capacity": 6},
    "B1": {"capacity": 3},
    "B2": {"capacity": 3},
    "B3": {"capacity": 3},
    "B4": {"capacity": 3}
}

# Sensor configuration
SENSOR_CONFIG = {
    "M1": ["process_time_s", "availability", "mttr_s", "work_power_kw", "idle_power_kw"],
    "M2": ["process_time_s", "availability", "mttr_s", "work_power_kw", "idle_power_kw"],
    "M3": ["process_time_s", "availability", "mttr_s", "work_power_kw", "idle_power_kw"],
    "M4": ["process_time_s", "availability", "mttr_s", "work_power_kw", "idle_power_kw"],
    "M5": ["process_time_s", "availability", "mttr_s", "work_power_kw", "idle_power_kw"],
    "B0": ["capacity"],
    "B1": ["capacity"],
    "B2": ["capacity"],
    "B3": ["capacity"],
    "B4": ["capacity"]
}

class DigitalTwinSimulation:
    def __init__(self):
        self.system = chrono.ChSystemNSC()
        self.system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))
        self.system.SetSolverType(chrono.ChSolver.Type_BARZILAIBORWEIN)
        self.system.SetMaxItersSolver(100)
        
        # Data structures for tracking simulation state
        self.equipment_states = {}
        self.sensor_data_queue = queue.Queue()
        self.db_connection = None
        self.setup_database_connection()
        self.initialize_equipment()
        self.setup_logging()
        
    def setup_database_connection(self):
        """Establish database connection"""
        try:
            self.db_connection = psycopg2.connect(**DB_CONFIG)
            cursor = self.db_connection.cursor()
            
            # Ensure tables exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_ingest (
                    ingested_at timestamptz NOT NULL DEFAULT NOW(),
                    source text NOT NULL,
                    payload jsonb NOT NULL
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ingest_watermark (
                    source text PRIMARY KEY,
                    max_event_ts timestamptz
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tag_map (
                    tag_id text PRIMARY KEY,
                    machine_id text,
                    signal text,
                    unit text,
                    register text,
                    scale double precision
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS machines (
                    id text PRIMARY KEY,
                    process_time_s double precision,
                    availability_pct double precision,
                    mttr_s double precision,
                    power_working_kw double precision,
                    power_idle_kw double precision
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS buffers (
                    id text PRIMARY KEY,
                    capacity int,
                    before text,
                    after text
                );
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stations (
                    id text PRIMARY KEY,
                    processing_time_s double precision,
                    availability_pct double precision,
                    mttr_s double precision,
                    power_working_kw double precision,
                    power_idle_kw double precision
                );
            """)
            
            cursor.execute("""
                CREATE OR REPLACE VIEW events AS
                SELECT T1.ingested_at, T1.source, T1.payload->>'machine_id' AS machine_id, 
                       T1.payload->>'reason_code' AS reason_code, T1.payload->>'duration_s' AS duration_s, 
                       T1.payload->>'energy_kwh' AS energy_kwh 
                FROM raw_ingest AS T1;
            """)
            
            cursor.execute("""
                CREATE OR REPLACE VIEW samples AS
                SELECT T1.ingested_at, T1.source, T1.payload->>'machine_id' AS machine_id, 
                       T2.tag_id, T1.payload->>'value' AS value 
                FROM raw_ingest AS T1 
                INNER JOIN tag_map AS T2 ON T1.payload->>'tag' = T2.tag_id;
            """)
            
            self.db_connection.commit()
            cursor.close()
            
        except Exception as e:
            print(f"Error setting up database connection: {e}")
    
    def initialize_equipment(self):
        """Initialize all equipment with their configurations"""
        # Create machines
        for machine_id, config in EQUIPMENT_CONFIG.items():
            if machine_id.startswith("M"):
                self.equipment_states[machine_id] = {
                    "status": "operational",
                    "last_status_change": 0.0,
                    "processing_start": 0.0,
                    "total_processing_time": 0.0,
                    "total_idle_time": 0.0,
                    "active_cycles": 0,
                    "total_energy_consumed": 0.0
                }
            elif machine_id.startswith("B"):
                self.equipment_states[machine_id] = {
                    "current_items": 0,
                    "capacity": config["capacity"]
                }
                
        # Insert static data into DB
        self.insert_static_data()
    
    def insert_static_data(self):
        """Insert static configuration data into database"""
        try:
            cursor = self.db_connection.cursor()
            
            # Insert into tag_map
            for machine_id, sensors in SENSOR_CONFIG.items():
                for sensor in sensors:
                    tag_id = f"{machine_id}: {sensor}"
                    cursor.execute(
                        "INSERT INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (tag_id) DO NOTHING;",
                        (tag_id, machine_id, sensor.split('_')[0], 
                         sensor.split('_')[-1] if sensor.split('_')[-1] in ['kw', 's', 'percent'] else 'unit',
                         sensor, 1)
                    )
            
            # Insert into machines table
            for machine_id, config in EQUIPMENT_CONFIG.items():
                if machine_id.startswith("M"):
                    cursor.execute(
                        "INSERT INTO machines (id, process_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) "
                        "VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (id) DO NOTHING;",
                        (machine_id, config["process_time_s"], config["availability_pct"],
                         config["mttr_s"], config["power_working_kw"], config["power_idle_kw"])
                    )
            
            # Insert into buffers table
            for machine_id, config in EQUIPMENT_CONFIG.items():
                if machine_id.startswith("B"):
                    cursor.execute(
                        "INSERT INTO buffers (id, capacity, before, after) "
                        "VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (id) DO NOTHING;",
                        (machine_id, config["capacity"], 
                         "source" if machine_id == "B0" else "M" + str(int(machine_id[1:]) - 1),
                         "M" + str(int(machine_id[1:]) + 1) if machine_id != "B4" else "destination")
                    )
            
            self.db_connection.commit()
            cursor.close()
        except Exception as e:
            print(f"Error inserting static data: {e}")
    
    def setup_logging(self):
        """Setup logging mechanism"""
        # Start logging thread
        self.logging_thread = threading.Thread(target=self.log_sensor_data, daemon=True)
        self.logging_thread.start()
    
    def log_sensor_data(self):
        """Log sensor data to database at regular intervals"""
        while True:
            try:
                current_time = datetime.now()
                while not self.sensor_data_queue.empty():
                    data = self.sensor_data_queue.get_nowait()
                    cursor = self.db_connection.cursor()
                    cursor.execute(
                        "INSERT INTO raw_ingest (source, payload) VALUES (%s, %s)",
                        ("digital_twin", Json(data))
                    )
                    self.db_connection.commit()
                    cursor.close()
                time.sleep(LOG_INTERVAL)
            except Exception as e:
                print(f"Error in logging thread: {e}")
                time.sleep(1)
    
    def simulate_step(self, current_time):
        """Simulate one time step"""
        # Update equipment states
        for machine_id, state in self.equipment_states.items():
            if machine_id.startswith("M"):
                # Simulate machine status changes
                if state["status"] == "operational":
                    # Calculate availability probability
                    availability = EQUIPMENT_CONFIG[machine_id]["availability_pct"] / 100.0
                    # Randomly determine if machine fails
                    if np.random.random() > availability:
                        state["status"] = "failed"
                        state["last_status_change"] = current_time
                        # Log failure event
                        self.log_event(machine_id, "failure", 
                                     EQUIPMENT_CONFIG[machine_id]["mttr_s"])
                elif state["status"] == "failed":
                    # Check if repair is complete
                    if current_time - state["last_status_change"] >= EQUIPMENT_CONFIG[machine_id]["mttr_s"]:
                        state["status"] = "operational"
                        state["last_status_change"] = current_time
                        # Log repair event
                        self.log_event(machine_id, "repair", 0)
            
            # Log sensor readings
            self.log_sensor_readings(machine_id, current_time)
    
    def log_event(self, machine_id, reason_code, duration_s):
        """Log machine events to database"""
        event_data = {
            "machine_id": machine_id,
            "reason_code": reason_code,
            "duration_s": duration_s
        }
        self.sensor_data_queue.put({
            "source": "event",
            "payload": event_data
        })
    
    def log_sensor_readings(self, machine_id, current_time):
        """Log sensor readings for a specific machine"""
        if machine_id.startswith("M"):
            # Get current state
            state = self.equipment_states[machine_id]
            
            # Log sensor data
            readings = {
                "machine_id": machine_id,
                "timestamp": current_time.isoformat()
            }
            
            # Process time (constant)
            readings["process_time_s"] = EQUIPMENT_CONFIG[machine_id]["process_time_s"]
            
            # Availability (based on operational status)
            readings["availability"] = 1.0 if state["status"] == "operational" else 0.0
            
            # MTTR (constant)
            readings["mttr_s"] = EQUIPMENT_CONFIG[machine_id]["mttr_s"]
            
            # Power consumption
            if state["status"] == "operational":
                readings["work_power_kw"] = EQUIPMENT_CONFIG[machine_id]["power_working_kw"]
                readings["idle_power_kw"] = 0.0
            else:
                readings["work_power_kw"] = 0.0
                readings["idle_power_kw"] = EQUIPMENT_CONFIG[machine_id]["power_idle_kw"]
            
            # Log the readings
            self.sensor_data_queue.put({
                "source": "sensor",
                "payload": readings
            })
            
        elif machine_id.startswith("B"):
            # Buffer capacity reading
            state = self.equipment_states[machine_id]
            readings = {
                "machine_id": machine_id,
                "timestamp": current_time.isoformat(),
                "capacity": state["capacity"]
            }
            self.sensor_data_queue.put({
                "source": "sensor",
                "payload": readings
            })
    
    def run_simulation(self):
        """Run the full simulation"""
        start_time = time.time()
        current_time = 0.0
        
        print("Starting digital twin simulation...")
        
        try:
            while current_time < SIMULATION_TIME:
                # Step simulation
                self.system.DoStepDynamics(TIME_STEP)
                
                # Update equipment states
                self.simulate_step(datetime.now())
                
                # Print progress
                if