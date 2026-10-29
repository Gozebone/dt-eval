import pychrono as chrono
import pychrono.irrlicht as chronoirr
import pychrono.fea as fea
import math
import numpy as np
import time
import json
import datetime
import sqlite3
import threading
from collections import deque

# Initialize the PyChrono system
chrono.SetChronoDataPath('path/to/chrono/data')
chrono.SetChronoDataPath('path/to/chrono/data')  # Ensure path is set

# Create the simulation system
sys = chrono.ChSystemNSC()
sys.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Set up the Irrlicht visualization
vis = chronoirr.ChVisualSystemIrrlicht()
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Production Line Digital Twin')
vis.Initialize()
vis.AddLogo()
vis.AddSkyBox()
vis.AddCamera(chrono.ChVectorD(0, 5, 10), chrono.ChVectorD(0, 0, 0))
vis.AddTypicalLights()

# Define material properties
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.4)
steel_mat.SetRestitution(0.1)

# Define machine parameters from the requirements
machines_data = [
    {
        'id': 'M1',
        'processing_time_s': 200,
        'availability': 0.97,
        'mttr_s': 900,
        'work_power_kw': 5.0,
        'idle_power_kw': 0.5
    },
    {
        'id': 'M2',
        'processing_time_s': 220,
        'availability': 0.97,
        'mttr_s': 1000,
        'work_power_kw': 5.5,
        'idle_power_kw': 0.55
    },
    {
        'id': 'M3',
        'processing_time_s': 240,
        'availability': 0.96,
        'mttr_s': 1200,
        'work_power_kw': 6.0,
        'idle_power_kw': 0.6
    },
    {
        'id': 'M4',
        'processing_time_s': 260,
        'availability': 0.96,
        'mttr_s': 1400,
        'work_power_kw': 7.0,
        'idle_power_kw': 0.7
    },
    {
        'id': 'M5',
        'processing_time_s': 230,
        'availability': 0.97,
        'mttr_s': 1100,
        'work_power_kw': 6.5,
        'idle_power_kw': 0.65
    },
    {
        'id': 'M6',
        'processing_time_s': 210,
        'availability': 0.97,
        'mttr_s': 1000,
        'work_power_kw': 6.0,
        'idle_power_kw': 0.6
    }
]

# Create machine bodies
machines = {}
for machine_data in machines_data:
    # Create a body for the machine
    machine_body = chrono.ChBodyEasyBox(2, 1, 2, 1000, True, True)
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
    machine_body.SetMaterialSurface(steel_mat)
    machine_body.SetBodyFixed(False)
    sys.Add(machine_body)

    # Store the machine in the dictionary
    machines[machine_data['id']] = {
        'body': machine_body,
        'data': machine_data,
        'is_working': False,
        'is_broken': False,
        'last_state_change': 0
    }

# Create buffers
buffers = {}
buffer_capacity = 10
for i in range(6):
    buffer_id = 'B' + str(i)
    buffer_body = chrono.ChBodyEasyBox(1, 0.5, 1, 1000, True, True)
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer_body.SetMaterialSurface(steel_mat)
    buffer_body.SetBodyFixed(True)
    sys.Add(buffer_body)
    buffers[buffer_id] = {
        'body': buffer_body,
        'capacity': buffer_capacity,
        'items': deque()
    }

# Create source object (item producer)
source_body = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 1000, True, True)
source_body.SetPos(chrono.ChVectorD(0, 0.5, 0))
source_body.SetMaterialSurface(steel_mat)
source_body.SetBodyFixed(True)
sys.Add(source_body)

# Create the event log database
def create_database():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machines (
            id TEXT PRIMARY KEY,
            processing_time_s INTEGER,
            availability DOUBLE PRECISION,
            mttr_s INTEGER,
            work_power_kw DOUBLE PRECISION,
            idle_power_kw DOUBLE PRECISION
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buffers (
            id TEXT PRIMARY KEY,
            capacity INTEGER
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_ingest (
            ingested_at TIMESTAMP PRIMARY KEY,
            source TEXT,
            payload TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            ts TIMESTAMP,
            machine_id TEXT,
            reason_code TEXT,
            duration_s DOUBLE PRECISION,
            energy_kwh DOUBLE PRECISION,
            PRIMARY KEY (ts, machine_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            ts TIMESTAMP,
            machine_id TEXT,
            tag TEXT,
            value DOUBLE PRECISION,
            PRIMARY KEY (ts, machine_id, tag)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingest_watermark (
            source TEXT PRIMARY KEY,
            max_event_ts TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# Insert initial data into the database
def insert_initial_data():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()

    # Insert machines
    for machine_data in machines_data:
        cursor.execute('''
            INSERT OR REPLACE INTO machines (id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            machine_data['id'],
            machine_data['processing_time_s'],
            machine_data['availability'],
            machine_data['mttr_s'],
            machine_data['work_power_kw'],
            machine_data['idle_power_kw']
        ))

    # Insert buffers
    for i in range(6):
        buffer_id = 'B' + str(i)
        cursor.execute('''
            INSERT OR REPLACE INTO buffers (id, capacity)
            VALUES (?, ?)
        ''', (buffer_id, buffer_capacity))

    # Insert tag_map
    tag_counter = 1
    for machine_data in machines_data:
        machine_id = machine_data['id']
        for param_name, value in machine_data.items():
            if param_name in ['processing_time_s', 'availability', 'mttr_s', 'work_power_kw', 'idle_power_kw']:
                tag_id = f'T{tag_counter}'
                cursor.execute('''
                    INSERT OR REPLACE INTO tag_map (tag_id, machine_id, signal, unit, register, scale)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    tag_id,
                    machine_id,
                    param_name,
                    'unitless' if param_name in ['availability'] else 's' if param_name == 'processing_time_s' or param_name == 'mttr_s' else 'kW',
                    param_name,
                    1.0
                ))
                tag_counter += 1

    conn.commit()
    conn.close()

# Log sample data to the database
def log_sample_data(ts, machine_id, tag, value):
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO samples (ts, machine_id, tag, value)
        VALUES (?, ?, ?, ?)
    ''', (ts, machine_id, tag, value))
    conn.commit()
    conn.close()

# Log event data to the database
def log_event(ts, machine_id, reason_code, duration_s, energy_kwh):
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO events (ts, machine_id, reason_code, duration_s, energy_kwh)
        VALUES (?, ?, ?, ?, ?)
    ''', (ts, machine_id, reason_code, duration_s, energy_kwh))
    conn.commit()
    conn.close()

# Simulate a machine's processing
def process_item(machine_id, start_time):
    machine = machines[machine_id]
    processing_time = machine['data']['processing_time_s']
    work_power = machine['data']['work_power_kw']

    # Simulate processing
    sys.SetChTime(start_time)
    machine['is_working'] = True
    machine['last_state_change'] = start_time

    # Log the start of processing
    log_sample_data(start_time, machine_id, 'processing_time_s', processing_time)
    log_sample_data(start_time, machine_id, 'work_power_kw', work_power)

    # Wait for processing to complete
    while sys.GetChTime() < start_time + processing_time:
        # Step the simulation
        sys.DoStepDynamics(0.01)
        if vis.Run():
            vis.Render()

    # Log completion
    machine['is_working'] = False
    machine['last_state_change'] = sys.GetChTime()
    log_sample_data(sys.GetChTime(), machine_id, 'processing_time_s', processing_time)
    log_sample_data(sys.GetChTime(), machine_id, 'work_power_kw', work_power)

# Simulate machine availability and failures
def simulate_machine_reliability(machine_id, start_time):
    machine = machines[machine_id]
    availability = machine['data']['availability']
    mttr_s = machine['data']['mttr_s']
    
    # Simulate a failure with the given availability
    if np.random.random() > availability:
        # Machine is down
        machine['is_broken'] = True
        machine['last_state_change'] = start_time
        log_event(start_time, machine_id, 'FAILURE', mttr_s, 0)
        
        # Wait for repair
        while sys.GetChTime() < start_time + mttr_s:
            sys.DoStepDynamics(0.01)
            if vis.Run():
                vis.Render()
        
        # Machine is repaired
        machine['is_broken'] = False
        machine['last_state_change'] = sys.GetChTime()
        log_event(sys.GetChTime(), machine_id, 'REPAIR', mttr_s, 0)
    else:
        # Machine is working
        pass

# Main simulation loop
def run_simulation():
    create_database()
    insert_initial_data()
    
    # Start time for simulation
    start_time = 0
    current_time = start_time
    inter_arrival_time = 300  # seconds
    simulation_end = 432000  # 5 days of simulation
    
    # Create the source item producer
    item_count = 0
    
    # Main loop
    while current_time < simulation_end:
        # Create new items at the source
        if (current_time - start_time) % inter_arrival_time < 0.1:
            item_count += 1
            print(f"Producing item {item_count} at time {current_time}")
            # Simulate item moving through the production line
            # For this simplified simulation, we will just process items through all machines
        
        # Process items through machines
        for machine_id in machines.keys():
            machine = machines[machine_id]
            if machine['is_working'] == False and machine['is_broken'] == False:
                # Process item in this machine
                process_item(machine_id, current_time)
            
            # Simulate reliability
            simulate_machine_reliability(machine_id, current_time)
        
        # Step the simulation forward
        sys.DoStepDynamics(0.01)
        current_time = sys.GetChTime()
        
        if vis.Run():
            vis.Render()
        
        # Update log every second
        if int(current_time) % 1 == 0:
            print(f"Simulation time: {current_time:.2f}s")
            
            # Log power consumption
            total_power = 0
            for machine_id, machine in machines.items():
                if machine['is_working']:
                    power = machine['data']['work_power_kw']
                    log_sample_data(current_time, machine_id, 'work_power_kw', power)
                    total_power += power
                else:
                    power = machine['data']['idle_power_kw']
                    log_sample_data(current_time, machine_id, 'idle_power_kw', power)
                    total_power += power
            
            # Log energy consumption
            energy_consumed = total_power * 0.01 / 3600  # Convert to kWh
            log_sample_data(current_time, 'TOTAL', 'energy_kwh', energy_consumed)

    # Close visualization at the end
    vis.Run()
    vis.Shutdown()

# Run the simulation
if __name__ == "__main__":
    run_simulation()